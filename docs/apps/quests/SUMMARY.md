# Quests App Summary

## Purpose & Scope
- **Primary mission:** Coordinate user goal-tracking quests, milestones, and newer enrollment-based quest templates that integrate learning activities.
- **Core consumers:** Frontend dashboards for personal/shared quests, activities app for quest-driven activity selection, and background demo-seeding commands.
- **Key entry points:** Legacy `QuestViewSet`/`MilestoneViewSet` in `views.py`, V2 template/enrollment ViewSets in `views_v2.py`, helper routers in `views/`, `dashboard_views.py`, and services bridging activities (`v2_bridge.py`).

## Domain Model
- **Primary models:**
  - Legacy `Quest` and `Milestone` representing per-user editable goal boards (`models.py`).
  - V2 `QuestTemplate`, `MilestoneTemplate`, `QuestEnrollment`, and `MilestoneProgress` supporting shared templates and structured progress tracking (`models.py`).
- **Supporting data:** Default quest definitions under `default_quests.py`/`default_quests_v2.py`, demo assets in `demo/`, and services for onboarding/bridging activities.
- **External relationships:** Quests reference `User` and optionally `Activity` structures via JSON. Enrollments can trigger activity sessions via `activities` integration (`v2_bridge.py`).

## Application Structure
- **API layer:** Multiple DRF routers — legacy `urls.py` for Quest/Milestone endpoints, nested routers in `serializers/` packages, and V2 routers for templates/enrollments.
- **Business logic:**
  - `services/` orchestrate quest creation, dashboard aggregation, and integration with activities.
  - `v2_bridge.py` maps quest progress to activity sessions.
  - Management commands seed defaults and migrate between versions.
- **Background/operations:** Demo loaders in `management/`; no continuous jobs but heavy reliance on command-run data seeding.
- **Configuration:** Many feature toggles implied via comments; V2 adoption is opt-in with fallback to legacy flows.

## Data & Control Flow
- **Inbound:** Authenticated API requests create/update quests, milestones, enrollments, and trigger status changes via custom actions.
- **Processing:** Legacy flow mutates `Quest`/`Milestone` directly; V2 flow enrolls users into templates, copies milestone templates into progress rows, and syncs with activities as needed.
- **Outbound:** Responses deliver quest lists, milestone dashboards, and upcoming/progress data. Bridge services may call activities APIs to launch sessions.

## Integration Points
- **Inter-app dependencies:** Coordinates with `apps.activities` for activity sessions, `apps.users` for ownership, and possibly `apps.responses` for completion unlocking.
- **External services:** None directly, though quest templates may reference external content via JSON.
- **Shared libraries:** Uses DRF viewsets, nested routers, and serializer patterns consistent with other apps.

## Operational Notes
- **Statefulness:** Maintains overlapping legacy and V2 data models; migrations/commands manage conversions but risk duplication.
- **Security & privacy:** Permission checks rely on ownership; template sharing/rescoping lacks explicit organization filtering.
- **Observability:** Limited logging; progress/completion metrics not surfaced beyond API responses.

## Known Variants & Roadmaps
- **Alternate flows:** Coexistence of legacy personal quests and V2 enrollment-based templates with bridging utilities.
- **Planned migrations:** Comments and presence of V2 modules indicate an ongoing migration to template/enrollment architecture.
- **Open questions:** Migration timeline, duplication handling between versions, and how quest progress ties into activities/courses.
