# Responses App Recommendations

## Snapshot Assessment
- **Overall health:** 🟠 Yellow — robust session tracking but critical logic lives in models with minimal tests and unclear ownership of agenda parsing.
- **Top risks:** Agenda markdown drift leading to stale sessions, unrestricted character selection leading to inconsistent analytics, and storage of sensitive transcripts without retention policies.
- **Immediate wins:** Centralize agenda versioning with courses, enforce consistent character options, and add tests for session creation/logging flows.

## Architecture & Design
- **Boundaries:** Define whether agenda parsing stays here or moves to courses; encapsulate parsing in a dedicated service with clear interfaces.
- **Domain model:** Normalize conversation storage (e.g., separate transcript table or integrate with chat app) and enforce constraints on status transitions.
- **State management:** Replace ad hoc JSON snapshots with explicit version references; provide automated migration tools when agendas change.

## Code Quality & Testing
- **Testing strategy:** Build factories for sessions/responses, cover `CourseSessionViewSet` actions, and add regression tests for agenda hash detection.
- **Modularity:** Extract unlocking logic into a domain service to reduce coupling with courses; decouple conversation summarization from models.
- **Error handling:** Improve validation when agenda parsing fails and surface actionable errors rather than silent fallbacks.

## API & Integration Surface
- **Contracts:** Document API payloads for logging responses and retrieving sessions; version endpoints if schema evolves.
- **Security:** Apply stricter permissions (organization scoping, rate limits) and define retention/anonymization policies for stored transcripts.
- **Performance:** Prefetch responses when serializing sessions to avoid repeated queries; consider pagination for long transcripts.

## Operations & Tooling
- **Monitoring:** Track session completion rates, agenda mismatch counts, and response logging errors.
- **Automation:** Provide management commands to reconcile sessions when agendas change and to purge stale transcripts per policy.
- **Documentation:** Publish guidance on agenda authoring, schema evolution, and how responses feed course unlocks.

## Suggested Roadmap
1. **Now (0-2 weeks):** Align with courses on agenda versioning, add API documentation/tests, and enforce character choices.
2. **Next (1-2 months):** Introduce migration tools for agenda changes, refactor conversation storage, and add observability.
3. **Later (Quarter+):** Integrate with activities' submission model and explore analytics exports for learning outcomes.

## Dependencies & Follow-Ups
- **Cross-team coordination:** Coordinate with courses and chat teams on agenda ownership and transcript retention.
- **Blocking issues:** Need policy decisions on transcript storage and anonymization before implementing retention jobs.
- **Definition of done:** Sessions stay in sync with agendas, unlocking logic is tested, and data retention/security policies are enforced.
