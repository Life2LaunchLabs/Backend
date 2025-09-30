# Project Overview

## Vision & Scope
- **Product intent:** Deliver an AI-assisted learning platform combining quests, courses, chat-based assistance, and activity sessions for users and organizations.
- **System boundaries:** This repo houses the Django backend (REST APIs, Channels WebSockets, management commands). External dependencies include third-party LLM providers and a separate frontend deployment.
- **Deployment targets:** Configured for Railway hosting (Procfile, railway.toml) with ASGI support via Daphne/Uvicorn, plus local development using Django runserver.

## Application Map
- **Installed Django apps:**
  - `apps.users` — authentication, profile management, quest onboarding.
  - `apps.courses` — course hierarchy/skill tree and progress tracking.
  - `apps.quests` — quest management (legacy + V2 enrollment system).
  - `apps.responses` — course assessment sessions and AI response storage.
  - `apps.chat` — configurable LLM chat sessions with WebSocket streaming.
  - `apps.organizations` — tenant administration and admin relationships.
  - (Commented) `apps.activities` — comprehensive activity authoring/sessions; code remains but app not installed.
- **Shared libraries:** `mysite` project with custom middleware, debug helpers, and centralized settings; DRF, SimpleJWT, and Django Channels provide cross-cutting infrastructure.
- **External integrations:** LLM providers (Anthropic, OpenAI) via chat app, PostgreSQL database, JWT auth, and optional storage for media/profile photos.

## Runtime Architecture
- **Request lifecycle:** ASGI application (`mysite.asgi`) enables HTTP and WebSocket handling. Middleware stack includes CORS, session, and WhiteNoise for static assets. REST endpoints use DRF routers across apps.
- **Data layer:** PostgreSQL via `psycopg2` stores relational data; JSONFields widely capture dynamic metadata. No caching layer configured.
- **Background work:** Management commands support data seeding, cleanup, and migration tasks; no Celery or async workers configured despite asynchronous needs (quest onboarding, session cleanup).

## Configuration & Environments
- **Settings strategy:** Single `settings.py` mixes development/production flags (DEBUG=True, hardcoded secret key) with Railway-specific overrides; environment variables supply database credentials.
- **Secrets management:** SECRET_KEY and provider keys not externalized; `.env` loading supported locally but production relies on environment variables without rotation guidance.
- **Feature flags:** Implicit toggles through code comments (e.g., legacy vs. V2 quests, activities) and environment checks; no centralized feature flag system.

## Operational Considerations
- **Security posture:** Uses SimpleJWT for auth but lacks rate limiting; organization scoping inconsistently enforced. CSRF/CORS configured for Railway domains with wildcard allowances.
- **Observability:** Minimal structured logging/metrics; relies on ad hoc logs within services and serializers. No monitoring/alerting integration in repo.
- **Scalability:** Channels enables WebSockets but no horizontal scaling guidance; session-heavy apps store state in DB without caching or task queues.

## Current Initiatives
- **Active migrations/refactors:** Ongoing migration from legacy quests/activities attempts to session/submission architectures; activities app partially merged into quests but still maintained separately.
- **Known gaps:** Sparse documentation (previously only template README), limited automated tests across apps, missing permission checks, and unclear data governance (agenda versions, encryption keys).
- **Opportunities:** Standardize architecture across apps, improve environment separation, adopt asynchronous workers for heavy onboarding, and implement observability/tooling to support production readiness.
