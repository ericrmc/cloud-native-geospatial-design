# Cloud-Native Geospatial Reference Architecture

*Compiled May 2026 — see [Timeline and currency](00_INDEX.md#timeline-and-currency) on the document index for the dating context.*

Some time ago I was asked what could be done to reduce cost pressure, ease the maintenance burden carried by spatial teams, address the data silos that grow up across project-specific platforms, improve access security, and make spatial data delivery faster and more reliable.

This corpus is my answer.

The work is a cloud-native spatial platform reference architecture. In simpler terms, it is a complete design for a modern platform that can store, manage, secure, serve, and edit spatial data in a more consistent way across an organisation.

It addresses the original asks together because, in practice, they are closely connected. Cost, maintenance, security, performance, and data fragmentation are not separate problems. They are different symptoms of the same underlying platform challenge.

The artefact is a nineteen-chapter design corpus. It is written to stand on its own. The prototype that informed it is not being handed over as a production system. It was valuable as a way to test ideas, but it was not production-reviewed and should not be treated as a deployable asset. What is offered is the design, the reasoning behind it, the options that were tested and rejected, and the lessons learned along the way.

## How the work was developed

I did not approach this as a traditional requirements-gathering exercise. I did not run a large workshop process, circulate surveys, or try to reconcile every existing request into a single backlog.

Instead, I spent time in conversation with senior stakeholders, developed a view about the kind of spatial platform that was likely to be needed over the longer term, and then built enough of that view to test whether it was realistic.

That approach was deliberate. There have been many opportunities for incremental improvement. What has not been on the table is a clear, worked-through position on what a simpler, lower-overhead, more secure, and more durable spatial platform could be.

This work is offered as that position. It is not a demand that anyone immediately change direction. It is a stake in the ground that future investment, procurement, and architecture decisions can be measured against.

## What the corpus contains

The corpus describes a platform that uses cloud storage as the primary foundation for spatial data, rather than relying on heavy database infrastructure for every read request. That choice is central to the cost and maintenance story.

It also describes a single access-control layer across the platform, so that data can be reached securely and consistently rather than being split across many project-specific arrangements.

The design supports standard spatial interfaces, so that future systems, tools, and vendors can connect to it without anyone being locked into one narrow delivery pattern. It includes a model for reviewed editing, change history, data repair, and publication workflows. It also includes a worked example of a web mapping client to show how the platform could be used in practice.

Importantly, the corpus records the decisions behind the design. It documents earlier options that were tried and moved away from, including heavier database-led patterns, alternative serving components, public-facing infrastructure choices, and platform options that did not fit the work's needs. These are not abstract preferences. They are lessons from the work.

It also includes a comparison of peer platforms and tools, so that future teams can see what was considered, what was rejected, and why. Some future possibilities are sketched as well, including better search, assisted data discovery, and more natural ways for users to ask questions of spatial data. Those ideas are clearly marked as future directions, not delivered components.

## What it is not

This is not a complete solution ready to implement without further work. It cannot replace any existing platform on day one. It would need proper engagement with business users, technical teams, project owners, security, operations, and delivery partners before any adoption decision.

Some parts of the design are strong and well tested through the prototype. Other parts are designed but not yet tested in a production setting. Some sections are deliberately directional.

The corpus is clear about those boundaries. That honesty is important. Anyone using the work should be able to see where the firm ground ends and where further validation would be needed.

## The economic case

The cost case is one of the main reasons this work exists.

Adopting the design at scale would require investment. A full transition needs capital funding to cover production hardening, migration planning and tooling, support for existing project teams, technical assurance, and the safety nets needed for a responsible transition.

The longer-term operating position is very different. The systems this design is intended to simplify or replace currently carry significant ongoing costs in hosting, licensing, support, and operational complexity. The proposed architecture is designed to reduce those recurring costs substantially by using simpler cloud-native components that scale with demand rather than requiring heavy infrastructure to run continuously.

The investment case is therefore not only technical. It is financial and operational. The upfront cost is real, but the potential reduction in long-term cost and complexity is the strongest reason to take the work seriously.

## Three ways to use the work

There are three realistic ways an organisation could use this architecture.

The first is to adopt it as a strategic platform direction. That would mean committing to a proper transition, funding the work, selecting candidate systems or datasets, and moving deliberately toward the target design. This option requires the most commitment, but it also offers the greatest long-term benefit.

The second is to adopt parts of it selectively. Individual capabilities, such as the access-control model, the data-serving pattern, the editing workflow, or the catalogue approach, could be applied to specific projects where the fit is strongest. This is likely to be the most practical near-term path. The design is intentionally modular, so that useful parts can be adopted without requiring the whole platform to be built at once.

The third is to use it as a reference point. Even if no direct adoption follows, the design decisions, lessons learned, and platform comparisons can help shape future procurement, investment, and technical choices. It provides a defensible view of what good could look like in this domain, and a useful counterpoint when assessing vendor proposals or incremental uplift options.

## Closing

I worked hard on this, and I worked differently. I took responsibility for forming a view, testing it, documenting it, and leaving behind something that others could use.

The work has mattered to me. I hope the technical architecture is useful — whether it becomes a platform direction, a source of reusable components, or simply a reference point for better decisions in the future.

---

**Read next:** [Document index and reading paths](00_INDEX.md) — chapter-by-chapter navigation, audience-keyed reading suggestions, the document catalogue, and notes on currency and dating.
