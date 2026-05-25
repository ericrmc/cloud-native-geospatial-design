# Cloud-Native Geospatial Reference Architecture

This is a reference architecture for a cloud-native spatial platform: a complete design for storing, managing, securing, serving, and editing spatial data consistently across an organisation.

It was developed in response to a recurring set of questions about cost pressure, maintenance burden on spatial teams, data silos across project-specific platforms, access security, and the speed and reliability of spatial data delivery. Those concerns are treated together here because, in practice, they are connected — different symptoms of the same underlying platform challenge.

The artefact is a twenty-chapter set of design documents, written to stand on its own. A prototype informed the design but is not being handed over as a production system; it was a way to test ideas, not a deployable asset. What is offered is the design, the reasoning behind it, the options that were tested and rejected, and the lessons learned along the way.

## How the work was developed

The approach was to spend time in conversation with senior stakeholders, form a view about the kind of spatial platform likely to be needed over the longer term, and then build enough of that view to test whether it was realistic.

Incremental improvement to existing systems has always been on the table. A clear, worked-through position on what a simpler, lower-overhead, more secure, and more durable spatial platform could look like has not. This work is offered as that position — a reference point against which future investment, procurement, and architecture decisions can be measured, rather than a call for immediate change in direction.

## What the documentation contains

The design uses cloud storage as the primary foundation for spatial data, rather than relying on heavy database infrastructure for every read request. That choice is central to the cost and maintenance story.

A single access-control layer sits across the platform, so data is reached securely and consistently rather than through many project-specific arrangements.

Standard spatial interfaces are supported throughout, so future systems, tools, and vendors can connect without anyone being locked into one delivery pattern. The design includes a model for reviewed editing, change history, data repair, and publication workflows, and a worked example of a web mapping client to show how the platform could be used in practice.

The documentation also records the decisions behind the design — including earlier options that were tried and moved away from: heavier database-led patterns, alternative serving components, public-facing infrastructure choices, and platforms that did not fit. These are lessons from the work, not abstract preferences.

A comparison of peer platforms and tools is included, so future teams can see what was considered and why. Some future possibilities are sketched as well — better search, assisted data discovery, and more natural ways for users to ask questions of spatial data — clearly marked as future directions rather than delivered components.

## What it is not

This is not a complete solution ready to implement without further work, and it cannot replace any existing platform on day one. Proper engagement with business users, technical teams, project owners, security, operations, and delivery partners would be needed before any adoption decision.

Some parts of the design are strong and well tested through the prototype. Others are designed but not yet tested in a production setting, and some sections are deliberately directional. The documentation is explicit about which is which, so anyone using the work can see where the firm ground ends and where further validation would be needed.

## The economic case

The cost case is one of the main reasons this work exists.

Adopting the design at scale would require investment. A full transition needs capital funding to cover production hardening, migration planning and tooling, support for existing project teams, technical assurance, and the safety nets needed for a responsible transition.

The longer-term operating position is meaningfully different. The systems this design is intended to simplify or replace carry significant ongoing costs in hosting, licensing, support, and operational complexity. The proposed architecture reduces those recurring costs by using cloud-native components that scale with demand rather than requiring heavy infrastructure to run continuously.

The investment case is therefore financial and operational as well as technical. The upfront cost is real; the reduction in long-term cost and complexity is the strongest reason to take the work seriously.

## Three ways to use the work

There are three realistic ways an organisation could use this architecture.

The first is to adopt it as a strategic platform direction — committing to a transition, funding the work, selecting candidate systems or datasets, and moving deliberately toward the target design. This option requires the most commitment and offers the greatest long-term benefit.

The second is to adopt parts of it selectively. Individual capabilities — the access-control model, the data-serving pattern, the editing workflow, the catalogue approach — can be applied to specific projects where the fit is strongest. The design is intentionally modular, so useful parts can land without requiring the whole platform to be built at once. This is likely to be the most practical near-term path.

The third is to use it as a reference point. Even without direct adoption, the design decisions, lessons learned, and platform comparisons can shape future procurement, investment, and technical choices — a defensible view of what good could look like in this domain, and a useful counterpoint when assessing vendor proposals or incremental uplift options.

## Closing

The intent of this work is to leave behind something others can use: a worked view, tested against a prototype, documented in enough depth to inform real decisions. Whether it becomes a platform direction, a source of reusable components, or a reference point for assessing future options, the value is in being concrete enough to argue with.

---

**Read next:** [Document index and reading paths](00_INDEX.md) — chapter-by-chapter navigation, audience-keyed reading suggestions, the document catalogue, and a note on currency.
