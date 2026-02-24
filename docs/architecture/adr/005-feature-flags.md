# ADR-005: Per-Tenant Feature Flags

**Status:** Accepted  
**Date:** 2026-02-24

## Context

Different tenants need different modules enabled (e.g., blog, cases, reviews, catalog). Options: global flags, per-tenant flags in database, or feature management SaaS.

## Decision

`FeatureFlag` table with `(tenant_id, feature_name, enabled)`. FastAPI dependencies `require_feature()` and `require_feature_public()` guard routes. Superusers and `platform_owner` bypass checks.

## Consequences

### Positive
- Fine-grained per-tenant control; each tenant can enable/disable modules independently
- Admin routes use `require_feature()` (auth required); public routes use `require_feature_public()` (returns 404 to hide feature existence)

### Negative
- New modules require a migration to seed the flag for existing tenants
- Database lookup on each protected request (can be cached if needed)

### Neutral
- Pre-defined checkers exist for `blog_module`, `cases_module`, `reviews_module`, `faq_module`, `team_module`, `services_module`, `catalog_module`, etc.
