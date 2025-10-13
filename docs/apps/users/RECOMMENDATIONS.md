# Users App Recommendations

## Snapshot Assessment
- **Overall health:** 🟠 Yellow — core auth works but synchronous quest onboarding, minimal rate limiting, and unclear encryption practices pose risks.
- **Top risks:** Registration depends on quests V2 code path (potentially slow/failure-prone), SimpleJWT endpoints lack throttling, and encryption keys/storage are unspecified.
- **Immediate wins:** Add rate limiting to auth endpoints, move quest initialization to an asynchronous job or guarded service, and document encryption key management.

## Architecture & Design
- **Boundaries:** Decouple quest onboarding from user creation by emitting a post-registration signal consumed by quests.
- **Domain model:** Formalize encrypted PII handling with dedicated model/field classes and rotation strategies; ensure profile photos respect storage policies.
- **State management:** Store audit timestamps for last login/profile update; integrate with organizations to ensure default org is consistent.

## Code Quality & Testing
- **Testing strategy:** Add tests for registration/login/profile flows including quest initialization failure scenarios; use factories for user creation.
- **Modularity:** Convert function-based views to class-based ViewSets for consistency with other apps; consolidate serializer validation.
- **Error handling:** Handle quest initialization errors gracefully (queue retry) and surface actionable error messages.

## API & Integration Surface
- **Contracts:** Document auth endpoints, token formats, and profile payloads; consider versioning for future SSO additions.
- **Security:** Enforce password policies (already partly via validators) and add throttling/captcha to mitigate brute force; ensure logout blacklisting is idempotent.
- **Performance:** Avoid synchronous calls to quests during registration; prefetch organization data when returning admin info.

## Operations & Tooling
- **Monitoring:** Track login/register success/failure metrics, quest onboarding latency, and encryption errors.
- **Automation:** Provide management commands for user import/export, password resets, and encryption key rotation.
- **Documentation:** Maintain runbooks for token revocation, password resets, and handling compromised credentials.

## Suggested Roadmap
1. **Now (0-2 weeks):** Implement throttling, decouple quest onboarding, and write regression tests for auth flows.
2. **Next (1-2 months):** Introduce structured encryption key management and audit logging for profile changes.
3. **Later (Quarter+):** Add SSO/social login support and advanced account management tooling.

## Dependencies & Follow-Ups
- **Cross-team coordination:** Align with quests on onboarding workflow changes and with security on encryption/key storage.
- **Blocking issues:** Need infrastructure support for secure key storage (e.g., KMS) before finalizing encryption strategy.
- **Definition of done:** Auth endpoints hardened with throttling/logging, quest onboarding asynchronous, and encryption documented/tested.
