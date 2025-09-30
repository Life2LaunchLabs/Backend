# Courses App Recommendations

## Snapshot Assessment
- **Overall health:** 🟠 Yellow — model is simple but critical logic is duplicated across serializers and responses integration, with little validation or auditing.
- **Top risks:** Agenda markdown is unversioned despite driving assessments, progress defaults are hardcoded, and no guardrails prevent cross-tenant access.
- **Immediate wins:** Introduce organization scoping, centralize agenda parsing/version hashes, and add tests for `skill_tree` and `update_progress` actions.

## Architecture & Design
- **Boundaries:** Clarify whether agenda ownership belongs here or in responses; expose a dedicated agenda service rather than having responses parse raw markdown.
- **Domain model:** Track agenda versions and metadata on `Course` to prevent silent schema drifts; consider a separate table for skill tree positioning vs. course content.
- **State management:** Move default status rules (root unlocked, parent gating) into declarative configuration, and expose signals/events when progress changes.

## Code Quality & Testing
- **Testing strategy:** Create factories for `Course` hierarchies and `UserCourseProgress`; cover serializer helpers and view actions with DRF tests.
- **Modularity:** Extract progress default logic into a reusable utility to avoid duplication between serializer and views; avoid querying inside serializer getters repeatedly.
- **Error handling:** Validate agenda presence before creating sessions in responses; return meaningful errors when progress updates violate gating rules.

## API & Integration Surface
- **Contracts:** Document the `skill_tree` response shape for frontend clients; plan versioning if agenda schema or positioning changes.
- **Security:** Enforce organization/role-based permissions on course access and updates; restrict who can mutate progress outside automated flows.
- **Performance:** Prefetch child relationships and progress in one query (already partially done); consider caching the skill tree for anonymous reads.

## Operations & Tooling
- **Monitoring:** Log/audit progress changes and expose metrics for course completion funnels.
- **Automation:** Provide management commands for seeding/updating course catalogs and validating agenda markdown.
- **Documentation:** Maintain authoring guidelines for agenda format and positioning rules.

## Suggested Roadmap
1. **Now (0-2 weeks):** Add permission checks, write unit tests, and document agenda/skill-tree contracts.
2. **Next (1-2 months):** Introduce agenda versioning with migration support and centralize gating rules.
3. **Later (Quarter+):** Integrate analytics dashboards and automation for large-scale catalog updates.

## Dependencies & Follow-Ups
- **Cross-team coordination:** Align with responses team on agenda ownership and with organizations team on tenancy requirements.
- **Blocking issues:** Need clarity on multi-tenant requirements before designing permission scheme.
- **Definition of done:** Agenda changes are versioned/audited, progress updates respect organization boundaries, and automated tests protect gating logic.
