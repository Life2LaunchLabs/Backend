# Courses App Summary

## Purpose & Scope
- **Primary mission:** Model course hierarchy/skill tree data and track user progress states to unlock learning paths.
- **Core consumers:** Frontend constellation/skill-tree visualizations, responses app for agenda parsing, and admin tooling for course maintenance.
- **Key entry points:** Read-only DRF `CourseViewSet` with custom actions, user progress endpoints in `views.py`, and serializers exposing course graph metadata (`serializers.py`).

## Domain Model
- **Primary models:** `Course` defines hierarchical course nodes with positional metadata, and `UserCourseProgress` records per-user status transitions (`models.py`).
- **Supporting data:** Course agenda markdown stored on `Course.agenda` feeds agenda parsing in `apps.responses`.
- **External relationships:** Progress updates unlock related content in `apps.responses` via shared foreign keys; course completion affects child course availability.

## Application Structure
- **API layer:** `CourseViewSet` (read-only) with `skill_tree` aggregation and `update_progress` mutation actions, requiring authentication (`views.py`).
- **Business logic:** Serializer helpers compute child IDs and derive user status from progress records (`serializers.py`); model methods provide helper lookups.
- **Background/operations:** No scheduled jobs; progression automation occurs synchronously inside model helpers.
- **Configuration:** Depends on implicit rules (root courses unlocked by default) encoded in serializer/view logic rather than settings.

## Data & Control Flow
- **Inbound:** Authenticated API requests fetch the course tree or update a specific course's progress state.
- **Processing:** Views assemble the full course list, enrich with user progress, and compute defaults when no records exist; updates adjust `UserCourseProgress` and timestamps.
- **Outbound:** Responses deliver serialized course graphs with per-user status; progress updates return serialized progress records.

## Integration Points
- **Inter-app dependencies:** `apps.responses` reads course agenda content and updates `UserCourseProgress` upon session completion; `apps.quests` may reference course structure for activity unlocks.
- **External services:** None directly; data is stored in PostgreSQL.
- **Shared libraries:** Utilizes DRF serializers and viewsets common across the project.

## Operational Notes
- **Statefulness:** Progress state is persisted per user; no caching layer. Agenda markdown can drift from parsed snapshots maintained elsewhere.
- **Security & privacy:** Requires authentication but lacks fine-grained authorization (e.g., organization scoping).
- **Observability:** No analytics or logging beyond default DRF logging; progress changes are not audited.

## Known Variants & Roadmaps
- **Alternate flows:** Manual progress updates through API vs. automatic updates triggered by responses app; agenda parsing implies future automated unlock logic.
- **Planned migrations:** None explicit; potential restructuring hinted by dependence on agenda parsing for question counts.
- **Open questions:** Governance of course agenda format, versioning, and how multi-tenant organizations should isolate course catalogs.
