# ADR-002: BaseService as Service-Repository Hybrid

**Status:** Accepted  
**Date:** 2026-02-24

## Context

We needed a consistent CRUD pattern across 16+ modules. Options: separate Repository + Service layers, or a combined `BaseService` that encapsulates both concerns.

## Decision

Single `BaseService[ModelT]` class that provides CRUD, pagination, soft-delete, and tenant filtering. Services subclass `BaseService` and override `_get_default_options()` for eager loading. No separate repository layer.

## Consequences

### Positive
- Less boilerplate; consistent API across all modules
- Tenant and soft-delete filtering applied automatically
- Pagination, `_get_by_id`, `_list_all`, and `_build_base_query` reused everywhere

### Negative
- Services directly depend on SQLAlchemy; harder to swap ORM later
- No abstraction over persistence; business logic and data access are coupled

### Neutral
- Trade-off favors development speed and consistency over strict layering
