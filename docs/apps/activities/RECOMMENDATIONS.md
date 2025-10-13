# Activities App Recommendations

## Snapshot Assessment
- **Overall health:** 🔴 Red — overlapping legacy and new session architectures, limited test coverage, and sparse permission checks create high maintenance risk.
- **Top risks:** Data divergence between `Attempt`/`Response` and `ActivitySession`/`ActivitySubmission`, unclear API surface across `urls.py` vs. `session_urls.py`, and ad hoc management commands operating on production data.
- **Immediate wins:** Document authoritative API (session vs. legacy), add permission classes to ViewSets, and instrument cleanup jobs for observability.

## Architecture & Design
- **Boundaries:** Decide whether quest orchestration lives here or in `apps.quests`; migrate quest-related models (`QuestDefinition`, `QuestInstance`) to quests to reduce duplication.
- **Domain model:** Consolidate on the session/submission schema by backfilling submissions from attempts and freezing legacy writers; introduce explicit status enums instead of string literals.
- **State management:** Centralize TTL/cleanup policy in settings and expose metrics for expired sessions rather than embedding constants in services.

## Code Quality & Testing
- **Testing strategy:** Add factories for `Activity`, `ActivitySession`, and `ActivitySubmission`; cover `ActivitySessionService` continue/restart paths and management commands.
- **Modularity:** Extract serializer validation logic out of views into dedicated validators to simplify `views.py`; break large services into focused collaborators.
- **Error handling:** Ensure session navigation gracefully handles missing page content with typed exceptions mapped to 4xx responses.

## API & Integration Surface
- **Contracts:** Publish OpenAPI/DRF schema for both authoring and session endpoints; version the session API if the legacy endpoints must remain temporarily.
- **Security:** Apply organization-based permission classes and user ownership checks in ViewSets; add throttling for session start/continue actions to prevent abuse.
- **Performance:** Prefetch related pages/blocks in serializer queries to avoid N+1 patterns when hydrating activity detail responses.

## Operations & Tooling
- **Monitoring:** Emit structured logs for session lifecycle events and cleanup jobs; add metrics for active sessions, completion times, and expirations.
- **Automation:** Schedule `cleanup_expired_sessions` via Celery/cron with alerting on failures; gate `create_comprehensive_demo` behind environment checks.
- **Documentation:** Provide runbooks for migrating legacy attempts and for interpreting the new submission tables.

## Suggested Roadmap
1. **Now (0-2 weeks):** Lock down permissions, publish authoritative API docs, and add smoke tests for session lifecycle.
2. **Next (1-2 months):** Complete migration off legacy attempt models, refactor services into smaller units, and implement metrics/alerts for session cleanup.
3. **Later (Quarter+):** Explore content versioning workflows (draft/publish with approvals) and richer analytics exports built on the consolidated submission schema.

## Dependencies & Follow-Ups
- **Cross-team coordination:** Align with quests team on ownership of quest instance data and with frontend on endpoint deprecation timelines.
- **Blocking issues:** Requires historical attempt data audit before deletion and potential data warehouse consumers review.
- **Definition of done:** All consumers use session/submission APIs, automated cleanup is observable, and tests cover core session flows.
