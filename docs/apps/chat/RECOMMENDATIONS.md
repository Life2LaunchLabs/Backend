# Chat App Recommendations

## Snapshot Assessment
- **Overall health:** 🟠 Yellow — core abstractions are in place, but gaps in auth, observability, and provider management threaten reliability.
- **Top risks:** Missing access controls on REST/WebSocket endpoints, lack of automated TTL cleanup for `ChatSession`, and hardcoded provider defaults without environment segregation.
- **Immediate wins:** Enforce DRF permissions, add WebSocket authentication middleware, and schedule a job to deactivate expired sessions.

## Architecture & Design
- **Boundaries:** Separate provider configuration from runtime session state; consider a dedicated module for preset definitions that can be versioned.
- **Domain model:** Normalize model/provider parameters to avoid arbitrary JSON blobs and ease validation; persist provider response metadata in a structured form.
- **State management:** Move TTL durations and session policies into settings, exposing a cron/management command for cleanup and metrics.

## Code Quality & Testing
- **Testing strategy:** Add tests for `ChatSessionService` create/update flows, conversation streaming, and analytics aggregations using mocked LLM clients.
- **Modularity:** Extract provider-specific logic from `conversation_service.py` into adapters; tighten typing around processors to avoid silent failures.
- **Error handling:** Introduce structured exceptions for provider failures and map them to meaningful HTTP/WebSocket error payloads.

## API & Integration Surface
- **Contracts:** Document REST endpoints and message formats for WebSocket clients; version presets so clients can detect breaking changes.
- **Security:** Require authenticated WebSocket connections (token/cookie), validate ownership on every session/message call, and scrub sensitive parameters before persisting.
- **Performance:** Implement pagination for session history, index `ChatMessage` queries appropriately (already partially covered) and batch analytics queries.

## Operations & Tooling
- **Monitoring:** Emit metrics for active sessions, message latency, and provider error rates; integrate with logging/alerting for provider outages.
- **Automation:** Provide management commands for rehydrating presets and rotating provider credentials; run TTL cleanup as scheduled job.
- **Documentation:** Maintain runbooks for onboarding new providers and troubleshooting streaming failures.

## Suggested Roadmap
1. **Now (0-2 weeks):** Add authentication/authorization to all endpoints, implement TTL cleanup, and create contract docs for REST/WebSocket APIs.
2. **Next (1-2 months):** Refactor provider adapters with test coverage and add observability hooks (metrics/logging dashboards).
3. **Later (Quarter+):** Build UI/admin tooling for preset management and experiment with conversation summarization/storage policies.

## Dependencies & Follow-Ups
- **Cross-team coordination:** Align with security/compliance on storage of LLM prompts/responses and with frontend on auth changes.
- **Blocking issues:** Need environment secrets for providers and decision on persistence retention for privacy compliance.
- **Definition of done:** Auth enforced, sessions auto-expire without manual intervention, and provider integrations are observable and tested.
