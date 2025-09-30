# Organizations App Summary

## Purpose & Scope
- **Primary mission:** Represent organizations/tenants, manage admin memberships, and expose APIs for users to inspect or set their default organization.
- **Core consumers:** Admin UI, other apps checking tenant scope (activities, users), and authentication flows needing organization context.
- **Key entry points:** Read-only `OrganizationViewSet`, admin status API views (`AdminStatusView`, `SetDefaultOrganizationView`), and serializers for organization/admin relationships (`serializers.py`).

## Domain Model
- **Primary models:** `Organization` with metadata and activation flags, and `OrganizationAdmin` as the through model linking users to organizations with role/permissions (`models.py`).
- **Supporting data:** Timestamp mixin provides auditing fields; JSON `permissions` field allows future granularity.
- **External relationships:** Many-to-many with custom `User` model via the through table; other apps reference organizations for scoping (e.g., activities).

## Application Structure
- **API layer:** DRF read-only ViewSet for organizations (`views.py`) plus custom APIViews for checking/setting admin status.
- **Business logic:** Model methods on `User` (in users app) implement admin helpers used by these views; no dedicated services.
- **Background/operations:** No scheduled jobs or management commands; relies on manual admin operations.
- **Configuration:** Assumes single shared organization namespace with boolean `is_active` gating.

## Data & Control Flow
- **Inbound:** Authenticated requests fetch active organizations or update default organization; admin status view aggregates user-related data.
- **Processing:** Views delegate to user model helper methods and serializers to shape responses; permission checks ensure user is admin before mutation.
- **Outbound:** Returns serialized organization data and admin metadata for client dashboards.

## Integration Points
- **Inter-app dependencies:** Tight coupling with `apps.users` for admin helper methods; `apps.activities` references organizations on authored content.
- **External services:** None.
- **Shared libraries:** Uses DRF APIView/ViewSet pattern and Django ORM ManyToMany features.

## Operational Notes
- **Statefulness:** Organization membership persists in relational tables; no caching or TTL concerns.
- **Security & privacy:** Basic admin check ensures only organization admins can set defaults, but no role-based authorization beyond `role` string.
- **Observability:** No logging or audit trail for membership changes; relies on database history.

## Known Variants & Roadmaps
- **Alternate flows:** Potential for future differentiated admin roles via `role`/`permissions` fields, but not yet implemented.
- **Planned migrations:** None noted; expectation of future permission granularity implied by JSON field.
- **Open questions:** How organization scoping should propagate to other apps and whether non-admin reads should be allowed.
