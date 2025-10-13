# Chat App Summary

## Purpose & Scope
- **Primary mission:** Provide multi-provider LLM chat experiences with configurable presets, analytics, and WebSocket streaming.
- **Core consumers:** Frontend chat clients over REST and WebSockets, analytics dashboards, and background processors for conversation control.
- **Key entry points:** REST endpoints in `views.py`, session management services in `services.py`, conversation orchestration via `conversation_service.py`, and Channels consumers in `websocket_consumers.py` mapped through `websocket_urls.py`.

## Domain Model
- **Primary models:** `ChatSession` stores per-user chat sessions with TTL and dynamic configuration, while `ChatMessage` persists individual conversation turns (`models.py`).
- **Supporting data:** Analytics helpers in `analytics.py` compute session statistics; presets and provider specs live in `presets.py` and `providers.py`.
- **External relationships:** Sessions tie to the custom `User` model; configuration references external LLM providers defined in `llm_clients.py`.

## Application Structure
- **API layer:** `views.py` exposes DRF endpoints for creating/updating sessions and retrieving transcripts; routers are registered in `urls.py`.
- **Business logic:**
  - `services.py` coordinates session lifecycle, validation through `SessionConfigValidator`, and persistence.
  - `conversation_service.py` manages turn handling, safety filters, and provider dispatch.
  - `control_service.py` and `processors.py` plug into conversation orchestration for tool outputs and context enrichment.
- **Background/operations:** No Celery tasks; relies on TTL expiration and management via services. WebSockets provide live streaming through Channels consumers.
- **Configuration:** Provider and context defaults defined in code (`providers.py`, `presets.py`); environment variables power actual API keys via `llm_clients.py`.

## Data & Control Flow
- **Inbound:** REST and WebSocket requests create/update sessions and submit messages. Configuration is validated before sessions persist.
- **Processing:** Messages flow through conversation services that select providers, apply context/prompt templates, and stream completions back to clients.
- **Outbound:** Responses are persisted as `ChatMessage` rows and emitted to clients via HTTP responses or WebSocket events; analytics endpoints aggregate stats for dashboards.

## Integration Points
- **Inter-app dependencies:** Minimal direct coupling aside from using the shared `User` model and potential references from courses/quests for agenda generation.
- **External services:** Connects to third-party LLM providers (Anthropic, OpenAI) via `llm_clients.py` with provider-specific configuration (`providers.py`).
- **Shared libraries:** Uses DRF, Django Channels, and HTTP clients (`httpx`) for streaming.

## Operational Notes
- **Statefulness:** Sessions expire based on `expires_at`; TTL management occurs in model `save()` and service methods but lacks centralized scheduler.
- **Security & privacy:** Sessions rely on user ownership but lack explicit permission classes; configuration may include sensitive provider parameters stored as JSON.
- **Observability:** Logging is scattered; analytics helpers exist but no integration with metrics/tracing systems.

## Known Variants & Roadmaps
- **Alternate flows:** Supports preset-based configuration and ad hoc overrides; conversation processors enable experimental tool integrations.
- **Planned migrations:** Comments suggest migrating to provider-agnostic configs and better validation but no formal migration path documented.
- **Open questions:** How session TTL cleanup occurs in production and how WebSocket auth is enforced across environments.
