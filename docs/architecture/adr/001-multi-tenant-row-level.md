# ADR-001: Use Row-Level Tenant Isolation

**Status:** Accepted  
**Date:** 2026-02-24

## Context

The system serves multiple tenants. We needed to choose an isolation strategy. Options considered: schema-per-tenant, database-per-tenant, or row-level with `tenant_id`.

## Decision

Row-level isolation via `TenantMixin`, which adds a `tenant_id` foreign key to every tenant-scoped model. All tenants share the same schema and database.

## Consequences

### Positive
- Simple to implement; no per-tenant schema management
- Single schema and migrations for all tenants
- Lower operational complexity than schema-per-tenant or database-per-tenant

### Negative
- Every query must filter by `tenant_id`; missing filters risk data leakage
- All tenants share the same database resources

### Neutral
- `BaseService` handles tenant filtering automatically for models with `TenantMixin`
- No per-tenant schema migrations needed
