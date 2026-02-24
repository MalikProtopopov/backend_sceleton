# ADR-003: Separate Locale Tables for Internationalization

**Status:** Accepted  
**Date:** 2026-02-24

## Context

We need multi-language content. Options considered: JSONB column for translations, separate `*Locale` tables per entity, or an EAV (entity-attribute-value) approach.

## Decision

Separate `*Locale` tables (e.g., `ArticleLocale`, `CaseLocale`, `ServiceLocale`, `EmployeeLocale`) with a foreign key to the parent entity. Each locale row holds `locale`, `title`, `slug`, and other translatable fields.

## Consequences

### Positive
- Proper relational model; queryable per-locale with standard SQL
- Easy to add new locales without schema changes
- Indexes and constraints apply per locale; good query performance

### Negative
- More tables; each translatable entity needs a companion locale table
- Joins required when fetching localized content

### Neutral
- Mappers (e.g., `article_to_response`) accept a `locale` parameter and raise `LocaleDataMissingError` when data is missing for that locale
