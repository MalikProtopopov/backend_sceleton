# ADR-005: Per-Tenant Feature Flags

**Status:** Accepted  
**Date:** 2026-02-24  
**Updated:** 2026-03-01 — unified with billing/tenant_modules

## Context

Different tenants need different modules enabled (e.g., blog, cases, reviews, catalog). Options: global flags, per-tenant flags in database, or feature management SaaS.

## Decision

`FeatureFlag` table with `(tenant_id, feature_name, enabled)`. FastAPI dependencies `require_feature()` and `require_feature_public()` guard routes. Superusers and `platform_owner` bypass checks.

## Unified Access Control (2026-03-01)

**Source of truth for access:** `tenant_modules` (billing). Тариф, план и модули тенанта определяют доступ к функционалу.

- `FeatureFlagService.is_enabled()` → только `ModuleAccessService` (проверка `tenant_modules`). Fallback на `feature_flags` удалён.
- `feature_flags` остаётся для отображения в platform dashboard и обратной совместимости; при изменении через API синхронизируется в `tenant_modules`.
- Маппинг legacy-флагов в модули: `_FLAG_TO_MODULE` в `billing.service` (blog_module→content, cases_module→content, catalog_module→catalog_basic и т.д.).

## Consequences

### Positive
- Fine-grained per-tenant control; each tenant can enable/disable modules independently
- Admin routes use `require_feature()` (auth required); public routes use `require_feature_public()` (returns 404 to hide feature existence)
- **Unified logic:** тариф + модули тенанта — единственный источник прав; feature_flags синхронизируется при обновлении

### Negative
- New modules require a migration to seed the flag for existing tenants
- Database lookup on each protected request (can be cached if needed)

### Neutral
- Pre-defined checkers exist for `blog_module`, `cases_module`, `reviews_module`, `faq_module`, `team_module`, `services_module`, `catalog_module`, etc.
