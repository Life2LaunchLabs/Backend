# Project Overview

## Vision & Scope
- **Product intent:** {High-level goal and target users.}
- **System boundaries:** {What lives in this repo vs external services.}
- **Deployment targets:** {Environments, hosting platforms, CI/CD.}

## Application Map
- **Installed Django apps:** {List with one-line responsibilities.}
- **Shared libraries:** {Cross-cutting utilities, middleware, signals.}
- **External integrations:** {LLMs, storage, authentication providers, analytics.}

## Runtime Architecture
- **Request lifecycle:** {ASGI/WSGI entrypoints, middleware, routers.}
- **Data layer:** {Database(s), caching, messaging.}
- **Background work:** {Scheduled tasks, management commands, async workers.}

## Configuration & Environments
- **Settings strategy:** {Base/local/prod split, environment variable usage.}
- **Secrets management:** {Where secrets live, rotation policies.}
- **Feature flags:** {Runtime toggles, configuration stores.}

## Operational Considerations
- **Security posture:** {Authentication, authorization, multi-tenant boundaries.}
- **Observability:** {Logging, monitoring, error reporting.}
- **Scalability:** {Stateful components, concurrency limits, horizontal scaling.}

## Current Initiatives
- **Active migrations/refactors:** {In-flight architecture changes.}
- **Known gaps:** {Documentation, testing, tooling debt.}
- **Opportunities:** {Areas for investment or simplification.}
