# Technical Debt Tracking

This document tracks known technical debt items that need to be addressed in future iterations.

## High Priority

(All items completed!)

---

## Medium Priority

(All items completed!)

---

## Low Priority

(No items currently)

---

## Completed Items

| ID | Description | Completed | Implementation |
|----|-------------|-----------|----------------|
| AUTH-001 | Token Blacklist for Logout | 2026-01-17 | `core/redis.py:TokenBlacklist`, `core/security.py:get_current_token`, `auth/router.py:logout` |
| LEADS-001 | Rate Limiting for Public Endpoints | 2026-01-17 | Already implemented via `middleware/rate_limit.py`. Settings: 3 req/min for inquiries |
| LEADS-002 | Notification Task for New Inquiries | 2026-01-17 | `leads/router.py:_send_inquiry_notification` using `NotificationService` |

---

## Implementation Details

### AUTH-001: Token Blacklist

Added Redis-based token blacklist for proper JWT invalidation:

```python
# Usage in logout endpoint
blacklist = await get_token_blacklist()
if blacklist:
    await blacklist.add(token.jti, token.expires_in_seconds)
```

Files changed:
- `core/redis.py` - Added `TokenBlacklist` class and `get_token_blacklist()` function
- `core/security.py` - Added `jti` to tokens, blacklist check in `get_current_token()`
- `modules/auth/router.py` - Updated `logout` to blacklist token

### LEADS-001: Rate Limiting

Already implemented via `RateLimitMiddleware`:

```python
# config.py settings
rate_limit_inquiry_requests: int = 3
rate_limit_inquiry_window_seconds: int = 60
```

The middleware automatically applies rate limiting to `/public/inquiries` endpoint.

### LEADS-002: Inquiry Notifications

Integrated `NotificationService` with inquiry creation:

```python
# Automatically sends notifications if tenant has:
# - settings.notify_on_inquiry = True
# - settings.inquiry_email and/or settings.telegram_chat_id configured
```

Non-blocking - failures are logged but don't affect the API response.

---

## How to Use This Document

1. **Adding new debt:** Use format `CATEGORY-XXX` for IDs
2. **Before starting work:** Update status to "In Progress" in the relevant TODO comment
3. **After completion:** Move item to "Completed Items" table
4. **Regular review:** Review this document during sprint planning

Categories: AUTH, LEADS, CONTENT, SEO, PERF, SECURITY
