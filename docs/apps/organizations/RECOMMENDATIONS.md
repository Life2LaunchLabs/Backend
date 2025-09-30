# Organizations App Recommendations

## Snapshot Assessment
- **Overall health:** 🟢 Green leaning Yellow — domain is straightforward but lacks enforcement and observability required for multi-tenant production.
- **Top risks:** Absence of role-based authorization, no audit of membership changes, and organization scoping not enforced in dependent apps.
- **Immediate wins:** Add admin-only permissions to the ViewSet, emit audit logs on membership/default changes, and document how organization context should be propagated.

## Architecture & Design
- **Boundaries:** Establish clear ownership of organization membership updates (e.g., via dedicated services) instead of scattering logic across user methods and views.
- **Domain model:** Expand `OrganizationAdmin` with explicit role enum and optional status flags; consider soft-delete/audit tables for compliance.
- **State management:** Introduce signals or hooks when default organization changes to update cached context in other apps.

## Code Quality & Testing
- **Testing strategy:** Add API tests covering admin status retrieval, default organization updates, and permission failures.
- **Modularity:** Move business logic from views into a service layer shared with other apps that need to mutate organization relationships.
- **Error handling:** Provide clearer error codes/messages for inactive organizations or missing admin membership.

## API & Integration Surface
- **Contracts:** Publish API documentation describing admin status/default endpoints and expected payloads.
- **Security:** Ensure only organization admins can list organization data; apply throttling and audit logging for membership modifications.
- **Performance:** Prefetch admin relationships where needed; otherwise current footprint is light.

## Operations & Tooling
- **Monitoring:** Log all organization membership changes and expose metrics for active organizations vs. suspended ones.
- **Automation:** Provide management commands to bootstrap organizations, assign admins, and sync permissions from identity providers if applicable.
- **Documentation:** Create runbooks for onboarding new organizations and handling deactivation workflows.

## Suggested Roadmap
1. **Now (0-2 weeks):** Implement permission classes and audit logging; write regression tests.
2. **Next (1-2 months):** Introduce role enums/permissions matrix and propagate organization filters into dependent apps (activities, courses, quests).
3. **Later (Quarter+):** Integrate with centralized identity/SSO and automate org provisioning.

## Dependencies & Follow-Ups
- **Cross-team coordination:** Align with security/compliance and product owners on role definitions and audit requirements.
- **Blocking issues:** Need consistent organization concept across apps before enforcing filters.
- **Definition of done:** Role-based access enforced, membership changes logged, and downstream apps honor organization scoping.
