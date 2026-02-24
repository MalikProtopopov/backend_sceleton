# ADR-004: Soft Delete via SoftDeleteMixin

**Status:** Accepted  
**Date:** 2026-02-24

## Context

We need to preserve data for audit and SEO while allowing "deletion". Options: hard delete, soft delete with a flag, or archival to a separate store.

## Decision

`SoftDeleteMixin` adds a `deleted_at` timestamp. Records are marked deleted instead of removed. `BaseService` filters `deleted_at IS NULL` by default in all queries.

## Consequences

### Positive
- SEO URLs preserved; external links remain valid
- Foreign key integrity maintained; related records stay intact
- Complete audit trail; deleted content can be restored

### Negative
- Queries must always filter deleted records; accidental omission risks exposing deleted data

### Neutral
- `BaseService` handles filtering automatically; `include_deleted=True` bypasses for admin/audit use cases
