# Responses App Summary

## Purpose & Scope
- **Primary mission:** Capture AI-assisted course assessment sessions, persist question-level responses, and generate conversational transcripts tied to course agendas.
- **Core consumers:** Frontend assessment experience, courses app for progress unlocking, and analytics/reporting features requiring detailed response data.
- **Key entry points:** `CourseSessionViewSet` in `views.py` with custom actions (create/continue sessions, log responses, finalize sessions), supporting serializers, and utilities for parsing agenda markdown (`utils.py`).

## Domain Model
- **Primary models:** `CourseSession` tracks per-user course attempts with agenda snapshots and progress metrics; `QuestionResponse` stores question-level outcomes; `ConversationTurn` captures AI conversation history (`models.py`).
- **Supporting data:** Helpers for hashing agendas, tracking schema drift, and unlocking child courses via `Course` relationships (`models.py`).
- **External relationships:** Strong dependency on `apps.courses.Course` for agenda content and unlocking; updates `UserCourseProgress` on completion.

## Application Structure
- **API layer:** DRF `CourseSessionViewSet` with numerous custom actions for session lifecycle and conversation management (`views.py`); URL routing exposes nested operations (`urls.py`).
- **Business logic:** Heavy model methods handle agenda parsing, progress updates, and unlocking; view helpers orchestrate serialization/responses.
- **Background/operations:** No scheduled jobs; relies on on-demand updates and agenda hash comparisons to detect outdated sessions.
- **Configuration:** Hardcodes characters (e.g., `minu`) and progression logic within models/views.

## Data & Control Flow
- **Inbound:** Authenticated clients create or resume sessions, send question responses, and request conversation summaries.
- **Processing:** Agenda markdown is parsed into structured JSON at session creation; responses update progress metrics and may trigger course unlocks.
- **Outbound:** Responses provide serialized session state, completion percentages, conversation transcripts, and agenda snapshots for UI rendering.

## Integration Points
- **Inter-app dependencies:** Directly manipulates `apps.courses.UserCourseProgress`; interacts with chat/LLM services indirectly via stored conversation data.
- **External services:** None directly; assumes upstream chat/LLM pipeline already executed.
- **Shared libraries:** Utilizes DRF, Django ORM, and internal utilities for markdown parsing.

## Operational Notes
- **Statefulness:** Maintains session state with agenda snapshots; tracks schema drift but requires manual intervention when agendas change.
- **Security & privacy:** Stores raw AI responses and agenda data; lacks explicit PII handling though content may contain user input.
- **Observability:** Minimal logging/metrics; relies on status fields to infer progress.

## Known Variants & Roadmaps
- **Alternate flows:** Supports character variants via `character_used` and conversation logging; potential expansion to multiple assessment types.
- **Planned migrations:** Agenda hash fields suggest planned schema evolution handling but no automated migration workflows.
- **Open questions:** Ownership of agenda parsing, retention of conversation transcripts, and alignment with activities' session/submission model.
