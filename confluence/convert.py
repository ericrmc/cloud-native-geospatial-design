#!/usr/bin/env python3
"""
Convert the design-corpus Markdown to Confluence Cloud storage format.

Reads:   ../content/*.md
Writes:  ./pages/*.xml  (one Confluence storage-format file per Markdown file)
         ./manifest.json (filename -> title mapping for push.py)

Handles the Markdown features used in this corpus:
  - ATX headings (the H1 of each file becomes the page title; the body
    starts at H2)
  - Paragraphs, bold, italic, inline code, links
  - Bulleted and numbered lists
  - Fenced code blocks (language tag preserved as Confluence code macro)
  - Mermaid fenced blocks -> rendered to PNG via mermaid-cli (mmdc), emitted
    as <ac:image><ri:attachment.../></ac:image> references. This avoids any
    dependency on a Confluence Cloud mermaid app being installed in the
    destination space — diagrams ship as page attachments.
  - Pipe tables
  - Standard blockquotes -> <blockquote>
  - "In plain terms" / "Prior iteration" italicised blockquotes -> info panel
  - Horizontal rules
  - Cross-document Markdown links (file.md) -> Confluence page links by title

The output is XHTML-ish Confluence storage format suitable for posting to
`POST /wiki/rest/api/content` with representation="storage".

Run with no arguments. Re-run any time the Markdown changes.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape as _xml_escape

HERE = Path(__file__).resolve().parent
CONTENT_DIR = HERE.parent / "content"
PRIVATE_DIR = HERE.parent / "private"
PAGES_DIR = HERE / "pages"
DIAGRAMS_DIR = HERE / "diagrams"
MANIFEST_PATH = HERE / "manifest.json"

# Pixel width for rendered PNG diagrams. mmdc auto-scales height.
DIAGRAM_WIDTH = 1600
DIAGRAM_BACKGROUND = "white"

# Per-file source overrides for Confluence generation.
#
# Confluence is an internal-only surface (the corpus's Confluence space), so
# some pages should be sourced from `private/` instead of `content/`. The
# public Quartz site reads only `content/`, so this override is the mechanism
# that lets one repository feed both audiences without sanitising on the way
# out.
#
# Keys are content filenames (relative to content/). Values are paths to the
# preferred source file. If the override file does not exist, the original
# content/ source is used.
SOURCE_OVERRIDES = {
    "index.md": PRIVATE_DIR / "intro-letter.md",
}

ATTR_QUOTE = {'"': "&quot;"}


# ---------------------------------------------------------------------------
# Mermaid rendering — relies on the mermaid-cli (mmdc) binary being in PATH
# ---------------------------------------------------------------------------

def check_mmdc() -> None:
    """Verify mermaid-cli (mmdc) is available; exit with a clear message if not."""
    if shutil.which("mmdc") is None:
        print(
            "ERROR: mermaid-cli (mmdc) not found in PATH.\n"
            "  Install: npm install -g @mermaid-js/mermaid-cli\n"
            "  Then re-run convert.py.",
            file=sys.stderr,
        )
        sys.exit(1)


def render_diagram(mmd_path: Path, png_path: Path) -> None:
    """Render one .mmd source file to a .png via mmdc."""
    result = subprocess.run(
        [
            "mmdc",
            "-i", str(mmd_path),
            "-o", str(png_path),
            "-w", str(DIAGRAM_WIDTH),
            "-b", DIAGRAM_BACKGROUND,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"mmdc failed on {mmd_path.name}: {result.stderr.strip() or result.stdout.strip()}"
        )


def reset_diagrams_dir() -> None:
    """Clear stale diagram sources and images. Regenerated fresh each run."""
    DIAGRAMS_DIR.mkdir(exist_ok=True)
    for f in DIAGRAMS_DIR.iterdir():
        if f.is_file():
            f.unlink()


def x(text: str) -> str:
    """Escape for XML text content."""
    return _xml_escape(text)


def xq(text: str) -> str:
    """Escape for XML attribute values (also escapes double quotes)."""
    return _xml_escape(text, ATTR_QUOTE)


def cdata(text: str) -> str:
    """Safely embed text inside <![CDATA[...]]>."""
    return text.replace("]]>", "]]]]><![CDATA[>")


# ---------------------------------------------------------------------------
# Title extraction and filename mapping
# ---------------------------------------------------------------------------

def extract_title(md_text: str) -> str:
    for line in md_text.splitlines():
        m = re.match(r"^#\s+(.+?)\s*$", line)
        if m:
            return m.group(1).strip()
    return "Untitled"


def build_title_map() -> dict[str, str]:
    """Map source filename (e.g. '03_AUTHORISATION.md') -> page title."""
    titles: dict[str, str] = {}
    for f in sorted(CONTENT_DIR.glob("*.md")):
        md = f.read_text(encoding="utf-8")
        titles[f.name] = extract_title(md)
    return titles


def output_filename(source_name: str) -> str:
    """03_AUTHORISATION.md -> 03_authorisation.xml; index.md stays index.xml."""
    stem = Path(source_name).stem.lower()
    return f"{stem}.xml"


# ---------------------------------------------------------------------------
# Inline rendering: bold, italic, inline code, links
# ---------------------------------------------------------------------------

_INLINE_CODE_RE = re.compile(r"`([^`]+?)`")
_BOLD_RE = re.compile(r"\*\*([^*\n]+?)\*\*")
# Italic *...* — must not match ** (handled by ordering: bold first) and
# must not match standalone * in things like list bullets at line start.
_ITALIC_RE = re.compile(r"(?<![*\w])\*([^*\n][^*\n]*?)\*(?![\w*])")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

# Placeholder marker used while building inline output. The escape function
# is applied last, so any markup we want preserved is "stashed" first and
# substituted back after escaping the remaining plain text.
_PH_OPEN = "\x00PH"
_PH_CLOSE = "\x00"


def _render_inline(text: str, title_map: dict[str, str]) -> str:
    stash: list[str] = []

    def push(html: str) -> str:
        stash.append(html)
        return f"{_PH_OPEN}{len(stash) - 1}{_PH_CLOSE}"

    # 1. Inline code first — no further processing inside.
    def code_repl(m: re.Match) -> str:
        return push(f"<code>{x(m.group(1))}</code>")

    text = _INLINE_CODE_RE.sub(code_repl, text)

    # 2. Links — internal .md links become Confluence page links.
    def link_repl(m: re.Match) -> str:
        link_text, link_url = m.group(1), m.group(2)
        if "#" in link_url:
            # Drop anchors; Confluence storage anchors work differently and
            # the corpus only uses anchors for in-document scrolling.
            link_url = link_url.split("#", 1)[0]
        if link_url.endswith(".md"):
            target = title_map.get(link_url)
            if target is None:
                # Unknown reference — leave as plain text.
                return push(x(link_text))
            return push(
                f'<ac:link><ri:page ri:content-title="{xq(target)}"/>'
                f'<ac:plain-text-link-body><![CDATA[{cdata(link_text)}]]>'
                f"</ac:plain-text-link-body></ac:link>"
            )
        # External link or anchor
        if link_url.startswith(("http://", "https://", "mailto:")):
            return push(f'<a href="{xq(link_url)}">{x(link_text)}</a>')
        # Relative non-md link — render as plain text with the URL appended
        return push(x(link_text))

    text = _LINK_RE.sub(link_repl, text)

    # 3. Bold
    text = _BOLD_RE.sub(lambda m: push(f"<strong>{x(m.group(1))}</strong>"), text)

    # 4. Italic
    text = _ITALIC_RE.sub(lambda m: push(f"<em>{x(m.group(1))}</em>"), text)

    # 5. Escape remaining plain text.
    text = x(text)

    # 6. Restore stashed markup. Loop until stable because stashed content
    #    can itself contain placeholder markers (e.g. bold wrapping inline
    #    code) that need to be resolved.
    def restore(m: re.Match) -> str:
        return stash[int(m.group(1))]

    pattern = re.compile(rf"{re.escape(_PH_OPEN)}(\d+){re.escape(_PH_CLOSE)}")
    while True:
        new_text = pattern.sub(restore, text)
        if new_text == text:
            break
        text = new_text
    return text


# ---------------------------------------------------------------------------
# Block-level parser
# ---------------------------------------------------------------------------

class Converter:
    def __init__(self, title_map: dict[str, str], diagram_stem: str = "") -> None:
        self.title_map = title_map
        # Stem used to name extracted mermaid diagrams for this page, e.g.
        # diagram_stem="02_architecture" -> "02_architecture-mermaid-1.png".
        self.diagram_stem = diagram_stem
        # Each entry is (filename, mermaid_source). Populated as the
        # converter encounters fenced mermaid blocks.
        self.diagrams: list[tuple[str, str]] = []
        self.out: list[str] = []
        self.lines: list[str] = []
        self.i = 0

    def convert(self, md_text: str) -> str:
        # Strip the leading H1 (becomes the page title) and proceed.
        self.lines = md_text.splitlines()
        self.i = 0
        self.out = []
        self._skip_first_h1()

        while self.i < len(self.lines):
            line = self.lines[self.i]
            stripped = line.strip()

            if stripped == "":
                self.i += 1
                continue
            if line.startswith("```"):
                self._parse_fence()
                continue
            if line.startswith(">"):
                self._parse_blockquote()
                continue
            if re.match(r"^#{1,6}\s+", line):
                self._parse_heading()
                continue
            if stripped in {"---", "***", "___"}:
                self.out.append("<hr/>")
                self.i += 1
                continue
            if self._is_table_header_here():
                self._parse_table()
                continue
            if re.match(r"^[-*+]\s+", line):
                self._parse_list(ordered=False)
                continue
            if re.match(r"^\d+\.\s+", line):
                self._parse_list(ordered=True)
                continue
            self._parse_paragraph()

        return "\n".join(self.out)

    # ----- helpers ---------------------------------------------------------

    def _skip_first_h1(self) -> None:
        for idx, line in enumerate(self.lines):
            if re.match(r"^#\s+", line):
                self.i = idx + 1
                return
        self.i = 0

    def _peek(self, offset: int = 0) -> str | None:
        j = self.i + offset
        if 0 <= j < len(self.lines):
            return self.lines[j]
        return None

    # ----- block parsers ---------------------------------------------------

    def _parse_heading(self) -> None:
        line = self.lines[self.i]
        m = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if not m:
            self._parse_paragraph()
            return
        level = len(m.group(1))
        # Headings in body content shift down: corpus uses H1 as page title;
        # the next-most-prominent level (H2 in markdown) maps to h1 of the
        # Confluence body? Confluence's body normally starts at h1 too, but
        # the page title is rendered separately. We map markdown H2 -> h1,
        # H3 -> h2, etc., so structure stays comfortable on the rendered page.
        level = max(1, level - 1)
        text = self._render_inline(m.group(2))
        self.out.append(f"<h{level}>{text}</h{level}>")
        self.i += 1

    def _parse_paragraph(self) -> None:
        buf: list[str] = []
        while self.i < len(self.lines):
            line = self.lines[self.i]
            stripped = line.strip()
            if (
                stripped == ""
                or line.startswith("```")
                or line.startswith(">")
                or re.match(r"^#{1,6}\s+", line)
                or stripped in {"---", "***", "___"}
                or re.match(r"^[-*+]\s+", line)
                or re.match(r"^\d+\.\s+", line)
                or self._is_table_header_at(self.i)
            ):
                break
            buf.append(line.rstrip())
            self.i += 1
        if buf:
            text = " ".join(b.strip() for b in buf)
            self.out.append(f"<p>{self._render_inline(text)}</p>")

    def _parse_fence(self) -> None:
        opener = self.lines[self.i]
        lang_match = re.match(r"^```([\w+-]*)\s*$", opener)
        lang = lang_match.group(1) if lang_match else ""
        self.i += 1
        body_lines: list[str] = []
        while self.i < len(self.lines):
            line = self.lines[self.i]
            if line.startswith("```"):
                self.i += 1
                break
            body_lines.append(line)
            self.i += 1
        body = "\n".join(body_lines)

        if lang.lower() == "mermaid":
            # Record the source and emit an attachment-image reference.
            # The actual .mmd file is written and rendered by main(); push.py
            # uploads the .png as a Confluence attachment so the
            # ri:attachment reference here resolves at render time.
            idx = len(self.diagrams) + 1
            filename = f"{self.diagram_stem}-mermaid-{idx}.png"
            self.diagrams.append((filename, body))
            self.out.append(
                f'<p><ac:image ac:align="center" ac:layout="center">'
                f'<ri:attachment ri:filename="{xq(filename)}"/>'
                f"</ac:image></p>"
            )
        else:
            params = ""
            if lang:
                params = (
                    f'<ac:parameter ac:name="language">{x(lang)}</ac:parameter>'
                )
            self.out.append(
                f'<ac:structured-macro ac:name="code">{params}'
                f"<ac:plain-text-body><![CDATA[{cdata(body)}]]></ac:plain-text-body>"
                f"</ac:structured-macro>"
            )

    def _parse_blockquote(self) -> None:
        # Collect consecutive lines that start with '>' (or are blank
        # continuations within the quote).
        lines: list[str] = []
        while self.i < len(self.lines):
            line = self.lines[self.i]
            if line.startswith(">"):
                lines.append(line[1:].lstrip())
                self.i += 1
            else:
                break
        text = " ".join(l for l in lines if l.strip())

        # Detect "callout" style annotations and render them as Confluence
        # info panels. The corpus uses two specific openers in blockquotes:
        #   *In plain terms:* ...
        #   *Prior iteration.* ...    (rare in blockquote form)
        callout_match = re.match(
            r"^\*(In plain terms|Prior iteration|Why this matters|Note)[:.]\*\s*(.*)$",
            text,
            re.IGNORECASE,
        )
        if callout_match:
            label = callout_match.group(1)
            body = callout_match.group(2)
            inline = self._render_inline(body)
            self.out.append(
                f'<ac:structured-macro ac:name="info">'
                f"<ac:rich-text-body>"
                f"<p><strong>{x(label)}.</strong> {inline}</p>"
                f"</ac:rich-text-body></ac:structured-macro>"
            )
        else:
            inline = self._render_inline(text)
            self.out.append(f"<blockquote><p>{inline}</p></blockquote>")

    def _is_table_header_at(self, idx: int) -> bool:
        if idx + 1 >= len(self.lines):
            return False
        header, sep = self.lines[idx], self.lines[idx + 1]
        if "|" not in header or "|" not in sep:
            return False
        # Separator row: cells made of dashes (with optional colons for align)
        sep_cells = [c.strip() for c in sep.strip().strip("|").split("|")]
        if not sep_cells or not all(re.fullmatch(r":?-+:?", c) for c in sep_cells):
            return False
        return True

    def _is_table_header_here(self) -> bool:
        return self._is_table_header_at(self.i)

    def _parse_table(self) -> None:
        header_line = self.lines[self.i]
        self.i += 2  # skip header + separator
        headers = self._split_row(header_line)
        rows: list[list[str]] = []
        while self.i < len(self.lines):
            line = self.lines[self.i]
            if not line.strip() or "|" not in line:
                break
            rows.append(self._split_row(line))
            self.i += 1
        # Emit table
        parts = ["<table><tbody>"]
        parts.append(
            "<tr>" + "".join(f"<th>{self._render_inline(h)}</th>" for h in headers) + "</tr>"
        )
        for row in rows:
            # Pad if a row has fewer cells than headers
            while len(row) < len(headers):
                row.append("")
            parts.append(
                "<tr>"
                + "".join(f"<td>{self._render_inline(c)}</td>" for c in row[: len(headers)])
                + "</tr>"
            )
        parts.append("</tbody></table>")
        self.out.append("".join(parts))

    def _split_row(self, line: str) -> list[str]:
        # Strip leading/trailing pipe, then split.
        s = line.strip()
        if s.startswith("|"):
            s = s[1:]
        if s.endswith("|"):
            s = s[:-1]
        return [c.strip() for c in s.split("|")]

    def _parse_list(self, ordered: bool) -> None:
        items: list[str] = []
        marker_re = re.compile(r"^(\s*)(?:[-*+]|\d+\.)\s+(.+)$")
        while self.i < len(self.lines):
            line = self.lines[self.i]
            if not line.strip():
                # Allow blank lines between items
                if self.i + 1 < len(self.lines) and marker_re.match(
                    self.lines[self.i + 1]
                ):
                    self.i += 1
                    continue
                break
            m = marker_re.match(line)
            if not m:
                # Continuation of previous item
                if items:
                    items[-1] += " " + line.strip()
                    self.i += 1
                    continue
                break
            text = m.group(2)
            items.append(text)
            self.i += 1
        tag = "ol" if ordered else "ul"
        body = "".join(f"<li>{self._render_inline(item)}</li>" for item in items)
        self.out.append(f"<{tag}>{body}</{tag}>")

    # ----- inline pass-through --------------------------------------------

    def _render_inline(self, text: str) -> str:
        return _render_inline(text, self.title_map)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def main() -> int:
    if not CONTENT_DIR.exists():
        print(f"Content directory not found: {CONTENT_DIR}", file=sys.stderr)
        return 1

    check_mmdc()

    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    reset_diagrams_dir()

    titles = build_title_map()
    manifest: dict[str, dict] = {}
    total_diagrams = 0

    for md_path in sorted(CONTENT_DIR.glob("*.md")):
        # Honour any Confluence-specific source override.
        override = SOURCE_OVERRIDES.get(md_path.name)
        if override and override.exists():
            source_path = override
            source_label = f"private/{override.name}"
        else:
            source_path = md_path
            source_label = md_path.name

        md = source_path.read_text(encoding="utf-8")
        title = extract_title(md)
        out_name = output_filename(md_path.name)
        diagram_stem = Path(out_name).stem  # e.g. "index" or "02_architecture"

        conv = Converter(titles, diagram_stem)
        body = conv.convert(md)

        out_path = PAGES_DIR / out_name
        out_path.write_text(body + "\n", encoding="utf-8")

        # Render any extracted mermaid diagrams for this page.
        attachments: list[str] = []
        for filename, mermaid_src in conv.diagrams:
            mmd_path = DIAGRAMS_DIR / (filename[:-4] + ".mmd")
            png_path = DIAGRAMS_DIR / filename
            mmd_path.write_text(mermaid_src + "\n", encoding="utf-8")
            try:
                render_diagram(mmd_path, png_path)
            except RuntimeError as err:
                print(f"  ERROR rendering {filename}: {err}", file=sys.stderr)
                return 1
            attachments.append(filename)
            total_diagrams += 1

        manifest[out_name] = {
            "source": source_label,
            "title": title,
            "attachments": attachments,
        }
        suffix = f"  + {len(attachments)} diagram(s)" if attachments else ""
        print(f"  {source_label:36s} -> pages/{out_name:32s}{suffix}")

    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"\nWrote {len(manifest)} pages, rendered {total_diagrams} diagrams "
        f"to diagrams/, manifest at {MANIFEST_PATH.name}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
