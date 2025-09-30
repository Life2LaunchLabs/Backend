# Users App Summary

## Purpose & Scope
- **Primary mission:** Provide custom email-based authentication, JWT token issuance, and profile management for the platform's user base.
- **Core consumers:** Authentication flows (register/login/logout), profile editors, and other apps needing user metadata or admin helpers.
- **Key entry points:** Function-based DRF views in `views.py` for register/login/profile/logout, serializers for auth/profile data, and the custom `User` model with helper methods (`models.py`).

## Domain Model
- **Primary models:** Custom `User` extending `AbstractUser` with email as username, anonymized identifiers, profile fields, and encrypted PII storage (`models.py`).
- **Supporting data:** `UserManager` implements email-based creation; `encryption.py` provides wrapper for encrypting sensitive data; management commands support admin bootstrap.
- **External relationships:** Links to `organizations.Organization` via `default_organization` and many-to-many admin relation; quests initialization invoked during user creation.

## Application Structure
- **API layer:** Function-based API endpoints using DRF decorators for register/login/profile/logout, returning JWT tokens via SimpleJWT (`views.py`).
- **Business logic:** Serializers handle validation, quest onboarding (`UserRegistrationSerializer`), and profile updates; model methods expose helper functions for names, anonymity, and organization admin features.
- **Background/operations:** Registration triggers quest initialization logic; management commands exist for superuser/admin tasks.
- **Configuration:** Relies on SimpleJWT settings, environment-specific storage for profile photos, and encryption secret management.

## Data & Control Flow
- **Inbound:** Anonymous register/login requests, authenticated profile fetch/update calls, and logout token blacklist requests.
- **Processing:** Serializers validate credentials, create users via custom manager, trigger quest initialization, and optionally encrypt PII.
- **Outbound:** Returns JWT tokens, serialized user/profile data, and confirmation messages for logout.

## Integration Points
- **Inter-app dependencies:** Tightly coupled with `apps.quests` for default quest enrollment during registration and with `apps.organizations` for admin helpers.
- **External services:** Uses SimpleJWT for token handling and relies on encryption utilities for PII management.
- **Shared libraries:** Standard DRF/Serializer patterns plus Django authentication base classes.

## Operational Notes
- **Statefulness:** Stores encrypted PII as text; quest initialization runs synchronously during registration (potential latency risk).
- **Security & privacy:** Custom encryption wrapper handles PII but key management unspecified; login endpoint uses SimpleJWT but lacks rate limiting.
- **Observability:** Logging exists during quest initialization but overall auth events lack structured metrics/auditing.

## Known Variants & Roadmaps
- **Alternate flows:** Potential for social/SSO integration; quest initialization currently hard-coded to V2 defaults.
- **Planned migrations:** Comments hint at future encrypted PII expansion but no roadmap provided.
- **Open questions:** How encryption keys are managed, how to handle failed quest initialization gracefully, and whether to adopt class-based views/viewsets for consistency.
