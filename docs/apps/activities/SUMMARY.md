# Activities App Summary

## Purpose & Scope
- **Primary mission:** Manage authored learning activities, their page/block structure, and user execution lifecycle from session to submission.
- **Core consumers:** Internal quest orchestration (apps.quests), course/response analytics, and frontend clients hitting REST endpoints for authoring and playthrough.
- **Key entry points:** DRF routers exposed in `urls.py` for authoring/results and `session_urls.py` for live sessions, alongside management commands for demo data and data migration.

## Domain Model
- **Primary models:**
  - `Activity`, `ActivityVersion`, `Page`, and `Block` provide a versioned hierarchy of authored content (`models.py`).
  - `QuestDefinition`, `QuestInstance`, and `Attempt` legacy quest/attempt tracking (`models.py`).
  - `ActivitySession`, `ActivitySubmission`, and `SubmissionResponse` implement the newer session/submission split (`models.py`).
- **Supporting data:**
  - `MediaAsset` and `QuestionPackage` hold reusable assets and metadata (`models.py`).
  - `PageProgress` and `Response` capture granular attempt data (`models.py`).
  - Session-specific persistence lives in `session_models.py` (e.g., `ActivitySession`, `ActivityCompletion`, `SessionAttempt`).
- **External relationships:** Activities link to `organizations.Organization` for ownership and to the custom `User` model for quest/session tracking (`models.py`).

## Application Structure
- **API layer:**
  - Authoring/results ViewSets in `views.py` registered via `urls.py` for CRUD and analytics (`urls.py`).
  - Session-oriented endpoints (start/continue, navigation, analytics) in `session_views.py` routed by `session_urls.py`.
- **Business logic:**
  - `services.py` handles authoring-side orchestration (publishing, demo data).
  - `session_services.py` centralizes the new session lifecycle and completion workflow.
  - `session_services.py` and `services.py` rely heavily on query helpers embedded in models.
- **Background/operations:**
  - Management commands to create demo content, migrate old attempts, and clean expired sessions (`management/commands`).
- **Configuration:**
  - Relies on quest/activity feature toggles implied by comments (e.g., new session flow) and cleanup intervals baked into services.

## Data & Control Flow
- **Inbound:** Requests enter via DRF ViewSets for CRUD or via dedicated session actions (`urls.py`, `session_urls.py`). Validation is mostly serializer-driven, with business rules in services.
- **Processing:** Authoring operations go through serializer/model logic; session operations orchestrate `ActivitySessionService` to manage continue/restart decisions and persist progress (`session_services.py`).
- **Outbound:** Responses return DRF serializer payloads, while background commands create/mutate data for other apps (quests, courses). Session completion writes `ActivitySubmission` records consumed by reporting endpoints (`views.py`).

## Integration Points
- **Inter-app dependencies:**
  - Quests rely on `Activity` metadata when assembling enrollments (`quests` services).
  - Responses/courses read submission data for analytics and unlocking logic.
  - Organizations enforce tenant scoping for authored content.
- **External services:** No direct third-party calls; assumes storage/backends for media via keys in `MediaAsset`.
- **Shared libraries:** Uses Django REST Framework and Django ORM patterns shared across apps.

## Operational Notes
- **Statefulness:** Tracks both legacy `Attempt`/`Response` records and newer `ActivitySession`/`ActivitySubmission` data, leading to overlapping state machines.
- **Security & privacy:** Access control largely delegated to DRF defaults; organization ownership and user foreign keys enforce scope but lack explicit permission classes.
- **Observability:** Logging hooks exist in services, but no structured metrics or analytics instrumentation beyond manual fields.

## Known Variants & Roadmaps
- **Alternate flows:** Coexistence of legacy attempt model and new session/submission architecture; `session_urls.py` describes a parallel API surface still stabilizing.
- **Planned migrations:** `management/commands/migrate_completed_attempts.py` hints at migrating historical attempts into the new submission tables.
- **Open questions:** How/when the legacy quest attempt stack will be deprecated, and whether organizations/quests fully adopt the new APIs.
