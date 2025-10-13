# Quests App Recommendations

## Snapshot Assessment
- **Overall health:** 🔴 Red — simultaneous legacy and V2 stacks create confusing ownership, high risk of data drift, and heavy maintenance overhead.
- **Top risks:** Users can exist in both legacy and V2 quest systems, bridges depend on manual commands, and integration with activities lacks transactional guarantees.
- **Immediate wins:** Freeze legacy quest creation, document V2 as the authoritative path, and add analytics to monitor cross-system divergence.

## Architecture & Design
- **Boundaries:** Split legacy and V2 code into separate modules/packages with explicit deprecation timeline; isolate shared utilities to avoid circular imports.
- **Domain model:** Design migrations to convert legacy quests/milestones into templates/enrollments, including data cleanup and mapping of custom fields.
- **State management:** Introduce status flags/feature switches controlling which quest system is exposed to clients; centralize quest-activity orchestration in a dedicated service.

## Code Quality & Testing
- **Testing strategy:** Establish fixtures covering both legacy and V2 flows; add integration tests for enrollment lifecycle and activity bridging.
- **Modularity:** Reduce duplication between `views.py` and `views_v2.py` by extracting shared serializer logic; ensure services encapsulate business rules instead of views.
- **Error handling:** Implement consistent error responses when prerequisites aren't met; handle race conditions in milestone progression (e.g., multiple clients updating simultaneously).

## API & Integration Surface
- **Contracts:** Publish roadmap for API consumers describing migration to V2 endpoints; version APIs to avoid breaking clients during transition.
- **Security:** Enforce organization scoping and sharing permissions for templates/enrollments; audit access to shared quests.
- **Performance:** Optimize queries with prefetch/select_related (partially done) and consider background jobs for heavy onboarding tasks.

## Operations & Tooling
- **Monitoring:** Track adoption metrics (legacy vs. V2 usage), quest completion rates, and bridge errors; alert on command failures when seeding quests.
- **Automation:** Provide idempotent management commands for migrating and seeding V2 data; schedule sync jobs where real-time integration is not feasible.
- **Documentation:** Maintain runbooks for deprecating legacy quests, including data migration steps and communication plan.

## Suggested Roadmap
1. **Now (0-2 weeks):** Publish migration plan, gate legacy creation, and add observability to bridge services.
2. **Next (1-2 months):** Execute migration of existing quests to V2, update frontend clients, and deprecate legacy endpoints.
3. **Later (Quarter+):** Enhance template authoring tooling and deep integration with activities/courses once a single system remains.

## Dependencies & Follow-Ups
- **Cross-team coordination:** Coordinate with frontend, activities, and product stakeholders on migration timeline and feature parity.
- **Blocking issues:** Need data mapping for legacy custom fields and assurance from analytics/reporting consumers.
- **Definition of done:** Legacy endpoints disabled, all quests represented as templates/enrollments, and integration tests cover quest-to-activity lifecycle.
