# {APP_NAME} App Summary

## Purpose & Scope
- **Primary mission:** {One-sentence description of what the app owns.}
- **Core consumers:** {Internal Django apps, API clients, background jobs, etc.}
- **Key entry points:** {REST endpoints, signals, Celery tasks, management commands.}

## Domain Model
- **Primary models:** {List the core models and their responsibilities.}
- **Supporting data:** {Auxiliary tables, through models, enums/constants.}
- **External relationships:** {Cross-app foreign keys, external APIs, third-party services.}

## Application Structure
- **API layer:** {Views/ViewSets, routers, DRF serializers exposed.}
- **Business logic:** {Services, utils, workflow managers that encapsulate rules.}
- **Background/operations:** {Management commands, scheduled jobs, signals.}
- **Configuration:** {Settings, feature flags, environment variables the app relies on.}

## Data & Control Flow
- **Inbound:** {How data enters the app and validation performed.}
- **Processing:** {How requests are orchestrated across modules.}
- **Outbound:** {How responses/events leave the app and who consumes them.}

## Integration Points
- **Inter-app dependencies:** {How this app coordinates with other Django apps.}
- **External services:** {LLM providers, storage buckets, messaging systems, etc.}
- **Shared libraries:** {Utilities shared across apps.}

## Operational Notes
- **Statefulness:** {Session handling, caching, long-running resources.}
- **Security & privacy:** {Sensitive data handling, permission layers.}
- **Observability:** {Logging, analytics, feature flags.}

## Known Variants & Roadmaps
- **Alternate flows:** {Legacy vs. new implementations, feature flags.}
- **Planned migrations:** {Schema or architecture work already hinted at in code.}
- **Open questions:** {Important unknowns for future maintainers.}
