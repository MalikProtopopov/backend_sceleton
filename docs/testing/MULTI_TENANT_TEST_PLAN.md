# Multi-Tenant SaaS Backend: Test Plan (Phases 1–7)

---

## A) Quality Criteria and Coverage

### Security Invariants (MUST hold at all times)

| # | Invariant | Violation Impact |
|---|-----------|-----------------|
| S1 | Deactivated tenant (`is_active=false`) users CANNOT login, refresh tokens, or call any authenticated endpoint | Data breach / unauthorized access |
| S2 | Public API DOES NOT serve content for deactivated tenants | Data leak |
| S3 | `platform_owner` / `is_superuser` bypass tenant deactivation for their own access only | Platform inoperability |
| S4 | Disabled feature flags return 403 `feature_disabled` on all corresponding admin routes | Unauthorized feature access |
| S5 | Regular users (site_owner, editor, etc.) CANNOT use `tenant_id` query param to access other tenants | Tenant data isolation breach |
| S6 | Only `platform_owner` / `is_superuser` can cross-tenant via `tenant_id` param | Privilege escalation |
| S7 | Passwords are NEVER included in welcome emails or API responses | Credential exposure |
| S8 | Soft-deleted users cannot login; soft-deleted tenants are not served | Zombie access |
| S9 | Password reset tokens expire after 1 hour and are single-use by type | Account takeover |
| S10 | Login rate limiting enforced (10/min per IP) | Brute force |
| S11 | Audit logs are immutable and cover all critical operations | Compliance / forensics |
| S12 | Error messages do not leak internal details (stack traces, SQL, internal IDs) | Information disclosure |

### Coverage Targets

| Level | Scope | Min Coverage | Run Frequency |
|-------|-------|-------------|---------------|
| Unit | Services (`AuthService`, `UserService`, `TenantService`, `FeatureFlagService`, `RoleService`, `AuditService`, `EmailService`) + security utilities | 90% line | Every PR |
| Integration (API) | All auth, tenant, user management, feature flag endpoints | 85% line | Every PR |
| E2E / Scenario | 10 critical user journeys (login→work→logout, tenant lifecycle, cross-tenant mgmt) | N/A (scenario coverage) | Nightly |
| Security / Negative | All items from Section E | 100% case coverage | Every PR |

---

## B) Test Strategy by Level

### B1. Unit Tests

**What to mock:**
- `AsyncSession` (DB) → `AsyncMock` (verify `.add()`, `.flush()`, `.execute()` calls)
- `Redis` client → `AsyncMock` (verify cache get/set/invalidate)
- `EmailService` → `AsyncMock` (verify `send_welcome_email`, `send_password_reset_email` called with correct args)
- `get_token_blacklist()` → mock returns `AsyncMock` blacklist
- Time → `freezegun.freeze_time` for token expiry tests

**Services to test in isolation:**

| Service | Key Methods | Mock DB? |
|---------|------------|----------|
| `AuthService` | `authenticate`, `refresh_tokens`, `_check_tenant_active`, `request_password_reset`, `reset_password` | Yes |
| `UserService` | `create`, `update`, `soft_delete`, `change_password`, `list_users` | Yes |
| `TenantService` | `create`, `update`, `soft_delete`, `list_tenants` | Yes |
| `FeatureFlagService` | `is_enabled`, `update_flag`, `get_flags` | Yes |
| `RoleService` | `create_role`, `update_role`, `delete_role` | Yes |
| `AuditService` | `log` | Yes |
| `EmailService` | `send_welcome_email`, `send_password_reset_email` | N/A (HTTP mock) |
| `_check_tenant_active` (security.py) | Redis cache hit, cache miss→DB, inactive tenant | Yes + Redis mock |
| `TenantStatusCache` | `is_tenant_active`, `set_status`, `invalidate` | Redis mock |
| Token utilities | `create_password_reset_token`, `decode_password_reset_token`, `create_access_token` | No mocks |

**Side-effect validation pattern:**

```python
# Example: verify audit log created on user create
mock_db.add.assert_called()
audit_call = [c for c in mock_db.add.call_args_list if isinstance(c.args[0], AuditLog)]
assert len(audit_call) == 1
assert audit_call[0].args[0].action == "create"
assert audit_call[0].args[0].resource_type == "user"
```

### B2. Integration Tests (API)

**Infrastructure required:**
- PostgreSQL (test DB at `localhost:5433/cms`, existing Docker)
- Redis (test instance at `localhost:6379` or `6380`)
- Email provider: `console` mode (verify via log capture or `unittest.mock.patch`)
- Alembic migrations applied before test suite

**What NOT to mock:**
- Database (real async session with rollback per test)
- SQLAlchemy models and queries
- FastAPI dependency injection chain
- Redis (real instance for rate limiting / blacklist / tenant cache tests)

**What to mock:**
- External email providers (SendGrid/Mailgun HTTP calls) → `respx` or `unittest.mock.patch`
- Time for token expiry → `freezegun`

**Test pattern:**

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_returns_403_for_inactive_tenant(client, inactive_tenant, inactive_tenant_user):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": inactive_tenant_user.email, "password": "testpass123"},
        headers={"X-Tenant-ID": str(inactive_tenant.id)},
    )
    assert response.status_code == 403
    data = response.json()
    assert data["detail"] == "Organization is currently suspended. Contact platform administrator."
    # Verify error_code field in RFC 7807 response
    assert "tenant_inactive" in data["type"]
```

### B3. E2E / Contract Tests

**Critical user journeys (10 scenarios):**

1. **Platform owner: full tenant lifecycle** — create tenant → create user in that tenant → enable features → deactivate tenant → verify lockout
2. **Regular user: login → work → logout** — login → call /me → call feature endpoint → logout → verify token revoked
3. **Cross-tenant user management** — platform_owner lists users of tenant B, creates user in tenant B, verifies isolation
4. **Feature flag toggle** — enable blog_module → access articles → disable blog_module → verify 403 on articles
5. **Welcome email flow** — create user with `send_credentials=true` → verify email sent → login → verify `force_password_change=true` → change password → verify flag cleared
6. **Password reset flow** — forgot-password → get token → reset-password → login with new password
7. **Rate limiting** — 10 failed logins → 11th returns 429 → wait → login succeeds
8. **Audit trail** — perform actions → query audit logs → verify all actions recorded
9. **Soft delete cascade** — soft-delete user → verify cannot login; soft-delete tenant → verify API blocks
10. **Feature catalog** — platform_owner sees all enabled; regular user sees mix of enabled/disabled with correct `can_request`

### B4. Smoke / Regression for CI

**Smoke set (fast, <30s):**
- `POST /auth/login` — valid credentials → 200
- `GET /auth/me` — valid token → 200
- `GET /auth/me/features` — valid token → 200
- `GET /api/v1/tenants` — platform_owner → 200
- `GET /health` → 200

**Regression set (every PR):**
- All unit tests (`tests/unit/`)
- All integration tests (`tests/integration/`)
- All API tests (`tests/test_*.py`, `tests/api/`)
- Security/negative tests (`tests/security/`)

---

## C) Test Data and Fixtures

### C1. Required Entities

```
conftest.py (project-wide fixtures)
├── Tenants
│   ├── active_tenant        — is_active=True, slug="active-tenant"
│   ├── inactive_tenant      — is_active=True → set is_active=False after creation
│   ├── deleted_tenant       — soft-deleted (deleted_at != None)
│   └── tenant_b             — second active tenant (for cross-tenant tests)
│
├── Roles (in active_tenant)
│   ├── platform_owner_role  — name="platform_owner", is_system=True, permissions=["platform:*"]
│   ├── site_owner_role      — name="site_owner", is_system=True, permissions=["*"]
│   ├── editor_role          — name="editor", permissions=["articles:read","articles:create","articles:update"]
│   └── tenant_b_role        — role in tenant_b for isolation tests
│
├── Users
│   ├── platform_owner_user  — role=platform_owner_role, is_active=True, tenant=active_tenant
│   ├── superuser            — is_superuser=True, tenant=active_tenant
│   ├── site_owner_user      — role=site_owner_role, is_active=True, tenant=active_tenant
│   ├── editor_user          — role=editor_role, is_active=True, tenant=active_tenant
│   ├── inactive_user        — is_active=False, tenant=active_tenant
│   ├── deleted_user         — soft-deleted, tenant=active_tenant
│   ├── inactive_tenant_user — is_active=True, tenant=inactive_tenant
│   ├── tenant_b_user        — role=tenant_b_role, tenant=tenant_b
│   └── force_pwd_user       — force_password_change=True, tenant=active_tenant
│
├── Feature Flags (per tenant)
│   ├── active_tenant: blog_module=True, cases_module=True, reviews_module=False, faq_module=True, team_module=False
│   ├── inactive_tenant: all True (doesn't matter — tenant blocked)
│   └── tenant_b: blog_module=True, cases_module=False
│
├── Auth Tokens (pre-generated)
│   ├── platform_owner_token, platform_owner_headers
│   ├── superuser_token, superuser_headers
│   ├── site_owner_token, site_owner_headers
│   ├── editor_token, editor_headers
│   ├── inactive_tenant_token (valid JWT, but tenant is inactive)
│   └── expired_token (created with -1h expiry)
│
├── Redis State
│   ├── Clean state per test (flush test keys in fixture teardown)
│   ├── rate_limit_state: pre-populated for threshold tests
│   └── blacklisted_jti: a revoked token JTI
│
├── Email
│   └── mock_email_service: patch EmailService, capture calls via spy/AsyncMock
│
└── Audit Logs
    └── initial_audit_count: count of audit_logs before test (for delta assertions)
```

### C2. Fixture Code Outline

```python
# tests/conftest.py additions

@pytest_asyncio.fixture
async def inactive_tenant(db_session):
    tenant = Tenant(id=uuid4(), slug=f"inactive-{uuid4().hex[:8]}", name="Inactive Corp", is_active=False)
    db_session.add(tenant)
    await db_session.flush()
    return tenant

@pytest_asyncio.fixture
async def tenant_b(db_session):
    tenant = Tenant(id=uuid4(), slug=f"tenant-b-{uuid4().hex[:8]}", name="Tenant B Corp", is_active=True)
    db_session.add(tenant)
    await db_session.flush()
    return tenant

@pytest_asyncio.fixture
async def platform_owner_role(db_session, test_tenant):
    from app.modules.auth.models import Permission, RolePermission
    role = Role(id=uuid4(), tenant_id=test_tenant.id, name="platform_owner", is_system=True)
    db_session.add(role)
    await db_session.flush()
    # Add platform:* permission
    perm = await db_session.execute(select(Permission).where(Permission.code == "platform:read"))
    # ... link permissions
    return role

@pytest_asyncio.fixture
async def feature_flags_mixed(db_session, test_tenant):
    """Create feature flags: blog=True, cases=True, reviews=False, faq=True, team=False."""
    from app.modules.tenants.models import FeatureFlag
    flags_config = {
        "blog_module": True, "cases_module": True, "reviews_module": False,
        "faq_module": True, "team_module": False, "seo_advanced": True,
        "multilang": False, "analytics_advanced": False,
    }
    flags = []
    for name, enabled in flags_config.items():
        flag = FeatureFlag(tenant_id=test_tenant.id, feature_name=name, enabled=enabled)
        db_session.add(flag)
        flags.append(flag)
    await db_session.flush()
    return flags

@pytest.fixture
def mock_email_service(monkeypatch):
    """Mock EmailService to capture email sends."""
    from unittest.mock import AsyncMock
    mock_welcome = AsyncMock(return_value=True)
    mock_reset = AsyncMock(return_value=True)
    monkeypatch.setattr("app.modules.notifications.service.EmailService.send_welcome_email", mock_welcome)
    monkeypatch.setattr("app.modules.notifications.service.EmailService.send_password_reset_email", mock_reset)
    return {"welcome": mock_welcome, "reset": mock_reset}

@pytest_asyncio.fixture
async def audit_log_count(db_session, test_tenant):
    """Return current audit log count for delta assertions."""
    from sqlalchemy import func, select
    from app.modules.auth.models import AuditLog
    result = await db_session.execute(
        select(func.count()).select_from(AuditLog).where(AuditLog.tenant_id == test_tenant.id)
    )
    return result.scalar() or 0
```

---

## D) Test Case Matrix

### Phase 1: Tenant Lifecycle Enforcement

| ID | Component | Scenario | Preconditions | Steps | Expected Result | Type | Priority |
|----|-----------|----------|---------------|-------|-----------------|------|----------|
| T1-01 | AuthService | Login blocked for inactive tenant | `inactive_tenant`, `inactive_tenant_user` | `POST /auth/login` with valid creds, `X-Tenant-ID: inactive_tenant.id` | 403, `error_code=tenant_inactive`, message="Organization is currently suspended..." | Integration | P0 |
| T1-02 | AuthService | Refresh blocked for inactive tenant | User logged in, then tenant deactivated | `POST /auth/refresh` with valid refresh_token for inactive tenant | 403 `tenant_inactive` | Integration | P0 |
| T1-03 | Security | Authenticated request blocked for inactive tenant | Valid token for `inactive_tenant_user` | `GET /auth/me` with token | 403 `tenant_inactive` | Integration | P0 |
| T1-04 | Security | Platform owner bypasses inactive tenant check | `platform_owner_user` in active_tenant, token contains `role=platform_owner` | `GET /auth/me` | 200, user info returned | Integration | P0 |
| T1-05 | Security | Superuser bypasses inactive tenant check | `superuser` with is_superuser=True | Any authenticated endpoint | 200 | Integration | P0 |
| T1-06 | Dependencies | Public API blocked for inactive tenant | `inactive_tenant` | `GET /api/v1/public/articles?tenant_id=<inactive>` | 404 `tenant_not_found` | Integration | P0 |
| T1-07 | Tenant | Default tenant checks is_active (single-tenant mode) | Default tenant set to inactive | Request using default tenant resolution | Error (RuntimeError / 500) | Unit | P1 |
| T1-08 | Redis | Tenant status cached in Redis (30s TTL) | Active tenant, Redis available | Login → check Redis key `tenant_status:<id>` exists with value "1" | Key exists, TTL ~30s | Integration | P1 |
| T1-09 | Redis | Cache invalidated on tenant deactivation | Active tenant cached | `PATCH /tenants/{id}` with `is_active: false` → check Redis key deleted | Cache cleared | Integration | P1 |
| T1-10 | Redis | Cache invalidated on tenant soft-delete | Active tenant cached | `DELETE /tenants/{id}` → check Redis key deleted | Cache cleared | Integration | P1 |
| T1-11 | Security | Token valid by expiry but tenant deactivated mid-session | User has valid access_token, tenant becomes inactive | `GET /auth/me` with still-valid token | 403 `tenant_inactive` | Integration | P0 |

### Phase 2: Feature Flag Route Coverage

| ID | Component | Scenario | Preconditions | Steps | Expected Result | Type | Priority |
|----|-----------|----------|---------------|-------|-----------------|------|----------|
| T2-01 | article_router | Blog disabled → articles admin blocked | `blog_module=False` for tenant | `GET /api/v1/admin/articles` with auth | 403, `error_code=feature_disabled`, `detail.feature=blog_module`, `detail.contact_admin=true` | Integration | P0 |
| T2-02 | topic_router | Blog disabled → topics admin blocked | `blog_module=False` | `POST /api/v1/admin/topics` with auth | 403 `feature_disabled` | Integration | P0 |
| T2-03 | case_router | Cases disabled → cases admin blocked | `cases_module=False` | `GET /api/v1/admin/cases` | 403, `detail.feature=cases_module` | Integration | P0 |
| T2-04 | review_router | Reviews disabled → reviews admin blocked | `reviews_module=False` | `GET /api/v1/admin/reviews` | 403, `detail.feature=reviews_module` | Integration | P0 |
| T2-05 | faq_router | FAQ disabled → FAQ admin blocked | `faq_module=False` | `GET /api/v1/admin/faq` | 403, `detail.feature=faq_module` | Integration | P0 |
| T2-06 | employee_router | Team disabled → employees admin blocked | `team_module=False` | `GET /api/v1/admin/employees` | 403, `detail.feature=team_module` | Integration | P0 |
| T2-07 | bulk_router | Bulk op blocked for disabled resource type | `reviews_module=False` | `POST /api/v1/admin/bulk` with `resource_type=reviews` | 403 `feature_disabled` | Integration | P0 |
| T2-08 | bulk_router | Bulk op allowed for enabled resource type | `blog_module=True` | `POST /api/v1/admin/bulk` with `resource_type=articles` | 200 (or expected result) | Integration | P1 |
| T2-09 | article_router | Blog enabled → articles admin works | `blog_module=True` | `GET /api/v1/admin/articles` | 200 | Integration | P0 |
| T2-10 | Security | Superuser bypasses feature flag check | `blog_module=False`, superuser token | `GET /api/v1/admin/articles` | 200 | Integration | P0 |
| T2-11 | Security | Platform owner bypasses feature flag check | `blog_module=False`, platform_owner token | `GET /api/v1/admin/articles` | 200 | Integration | P1 |
| T2-12 | feature_check | Error message is user-friendly (not technical) | Any feature disabled | Trigger 403 | Message = "This section is not available for your organization. Contact your administrator to enable this feature." | Integration | P1 |

### Phase 3: Cross-Tenant User Management

| ID | Component | Scenario | Preconditions | Steps | Expected Result | Type | Priority |
|----|-----------|----------|---------------|-------|-----------------|------|----------|
| T3-01 | auth/router | Platform owner lists users of another tenant | `platform_owner_user`, `tenant_b` with users | `GET /auth/users?tenant_id=<tenant_b.id>` | 200, returns tenant_b users | Integration | P0 |
| T3-02 | auth/router | Platform owner creates user in another tenant | `platform_owner_user`, `tenant_b` | `POST /auth/users?tenant_id=<tenant_b.id>` with user data | 201, user created in tenant_b | Integration | P0 |
| T3-03 | auth/router | Site owner CANNOT list users of another tenant | `site_owner_user`, `tenant_b` | `GET /auth/users?tenant_id=<tenant_b.id>` | 403 `permission_denied`, `required_permission=platform:read` | Integration | P0 |
| T3-04 | auth/router | Editor CANNOT use tenant_id param | `editor_user` | `GET /auth/users?tenant_id=<tenant_b.id>` | 403 `permission_denied` | Integration | P0 |
| T3-05 | auth/router | Platform owner updates user in another tenant | `platform_owner_user`, `tenant_b_user` | `PATCH /auth/users/<tenant_b_user.id>?tenant_id=<tenant_b.id>` | 200 | Integration | P0 |
| T3-06 | auth/router | Platform owner deletes user in another tenant | `platform_owner_user`, `tenant_b_user` | `DELETE /auth/users/<tenant_b_user.id>?tenant_id=<tenant_b.id>` | 204 | Integration | P1 |
| T3-07 | auth/router | Omitting tenant_id defaults to own tenant | `platform_owner_user` | `GET /auth/users` (no tenant_id param) | 200, returns own tenant users only | Integration | P0 |
| T3-08 | tenants/router | Tenant list supports search by name | Multiple tenants | `GET /tenants?search=Acme` | 200, filtered results | Integration | P1 |
| T3-09 | tenants/router | Tenant list supports sort_by name asc | Multiple tenants | `GET /tenants?sort_by=name&sort_order=asc` | 200, sorted alphabetically | Integration | P1 |
| T3-10 | tenants/router | Tenant response includes users_count | Tenant with 3 active users | `GET /tenants` | `items[0].users_count == 3` | Integration | P1 |

### Phase 4: Welcome Email

| ID | Component | Scenario | Preconditions | Steps | Expected Result | Type | Priority |
|----|-----------|----------|---------------|-------|-----------------|------|----------|
| T4-01 | UserService | Welcome email sent when send_credentials=true | `mock_email_service` | Create user with `send_credentials: true` | `mock_email_service.welcome.assert_called_once_with(to_email=..., first_name=..., tenant_name=...)` | Unit | P0 |
| T4-02 | UserService | No email when send_credentials=false | `mock_email_service` | Create user with `send_credentials: false` | `mock_email_service.welcome.assert_not_called()` | Unit | P0 |
| T4-03 | UserService | New user has force_password_change=True | — | Create user via service | `user.force_password_change == True` | Unit | P0 |
| T4-04 | auth/router | Login response includes force_password_change | User with `force_password_change=True` | `POST /auth/login` | Response `user.force_password_change == true` | Integration | P0 |
| T4-05 | auth/router | /me returns force_password_change | `force_pwd_user` | `GET /auth/me` | `force_password_change == true` | Integration | P0 |
| T4-06 | UserService | change_password clears force_password_change | `force_pwd_user` | Call `change_password()` | `user.force_password_change == False` | Unit | P0 |
| T4-07 | EmailService | Welcome email does NOT contain password | `console` provider, capture log | Create user | Log output does NOT contain password string | Integration | P0 |
| T4-08 | UserService | Email failure does not block user creation | Mock email raises exception | Create user with `send_credentials: true` | User created successfully (201), email error logged | Unit | P1 |
| T4-09 | auth/router | UserResponse schema includes force_password_change | — | `GET /auth/users/{id}` | Response has `force_password_change` field | Integration | P1 |

### Phase 5: Feature Catalog

| ID | Component | Scenario | Preconditions | Steps | Expected Result | Type | Priority |
|----|-----------|----------|---------------|-------|-----------------|------|----------|
| T5-01 | auth/router | Full catalog returned for regular user | `editor_user`, mixed feature flags | `GET /auth/me/features` | All 8 features in response, `enabled` matches DB, `can_request = !enabled` | Integration | P0 |
| T5-02 | auth/router | Platform owner gets all_features_enabled=true | `platform_owner_user` | `GET /auth/me/features` | `all_features_enabled=true`, all features `enabled=true` | Integration | P0 |
| T5-03 | auth/router | Superuser gets all_features_enabled=true | `superuser` | `GET /auth/me/features` | `all_features_enabled=true` | Integration | P0 |
| T5-04 | auth/router | Locale=ru returns Russian titles | `editor_user` | `GET /auth/me/features?locale=ru` | `features[0].title` is Russian (e.g. "Блог / Статьи") | Integration | P1 |
| T5-05 | auth/router | Locale=en returns English titles | `editor_user` | `GET /auth/me/features?locale=en` | `features[0].title` is English (e.g. "Blog / Articles") | Integration | P1 |
| T5-06 | auth/router | Disabled feature has can_request=true | `reviews_module=False` | `GET /auth/me/features` | Feature with `name=reviews_module` has `enabled=false, can_request=true` | Integration | P0 |
| T5-07 | auth/router | Response includes tenant_id | `editor_user` | `GET /auth/me/features` | `tenant_id == editor_user.tenant_id` | Integration | P1 |
| T5-08 | auth/router | After toggling flag, catalog reflects change | Toggle `reviews_module` from False→True | `GET /auth/me/features` again | `reviews_module.enabled=true, can_request=false` | Integration | P1 |

### Phase 6: Audit Logs

| ID | Component | Scenario | Preconditions | Steps | Expected Result | Type | Priority |
|----|-----------|----------|---------------|-------|-----------------|------|----------|
| T6-01 | AuthService | Login creates audit log | `test_user` | `POST /auth/login` | AuditLog with `action=login, resource_type=auth, user_id=test_user.id` | Integration | P0 |
| T6-02 | auth/router | Logout creates audit log | Authenticated user | `POST /auth/logout` | AuditLog with `action=logout, resource_type=auth` | Integration | P0 |
| T6-03 | UserService | User create → audit log | Platform_owner | `POST /auth/users` | AuditLog: `action=create, resource_type=user, changes.email=<email>` | Integration | P0 |
| T6-04 | UserService | User update → audit log with changes diff | Platform_owner | `PATCH /auth/users/{id}` with `is_active: false` | AuditLog: `action=update, changes.is_active.old=True, changes.is_active.new=False` | Integration | P0 |
| T6-05 | UserService | User delete → audit log | Platform_owner | `DELETE /auth/users/{id}` | AuditLog: `action=delete, resource_type=user` | Integration | P0 |
| T6-06 | TenantService | Tenant create → audit log | Platform_owner | `POST /tenants` | AuditLog: `action=create, resource_type=tenant, changes.name=<name>` | Integration | P0 |
| T6-07 | TenantService | Tenant deactivation → audit log with is_active diff | Platform_owner | `PATCH /tenants/{id}` with `is_active: false` | AuditLog: `changes.is_active.old=True, changes.is_active.new=False` | Integration | P0 |
| T6-08 | TenantService | Tenant delete → audit log | Platform_owner | `DELETE /tenants/{id}` | AuditLog: `action=delete, resource_type=tenant` | Integration | P1 |
| T6-09 | FeatureFlagService | Feature toggle → audit log | Platform_owner | `PATCH /feature-flags/blog_module` | AuditLog: `resource_type=feature_flag, changes.enabled.old/new` | Integration | P0 |
| T6-10 | RoleService | Role create → audit log | Platform_owner | `POST /auth/roles` | AuditLog: `action=create, resource_type=role, changes.name=<name>` | Integration | P1 |
| T6-11 | RoleService | Role delete → audit log | Platform_owner | `DELETE /auth/roles/{id}` | AuditLog: `action=delete, resource_type=role` | Integration | P1 |
| T6-12 | UserService | Password change → audit log (no plaintext password) | `test_user` | `POST /auth/me/password` | AuditLog: `changes.password.old="***", changes.password.new="***"` | Integration | P0 |
| T6-13 | AuditService | Audit log has correct actor_id | Platform_owner creates user | Check audit log | `user_id == platform_owner.id` (not the created user's id) | Integration | P1 |

### Phase 7: Password Reset, Sort, Rate Limiting

| ID | Component | Scenario | Preconditions | Steps | Expected Result | Type | Priority |
|----|-----------|----------|---------------|-------|-----------------|------|----------|
| T7-01 | auth/router | Forgot password returns 204 for existing user | `test_user`, `mock_email_service` | `POST /auth/forgot-password` with user's email | 204, `mock_email_service.reset.assert_called_once()` | Integration | P0 |
| T7-02 | auth/router | Forgot password returns 204 for nonexistent email | — | `POST /auth/forgot-password` with `nobody@example.com` | 204 (no error, no email sent) | Integration | P0 |
| T7-03 | auth/router | Reset password with valid token | Generated reset token | `POST /auth/reset-password` with token + new password | 204, user can login with new password | Integration | P0 |
| T7-04 | auth/router | Reset password with expired token | Token created with `freeze_time` 2 hours ago | `POST /auth/reset-password` | 401 `token_expired` | Integration | P0 |
| T7-05 | auth/router | Reset password with invalid token type | Use access_token as reset token | `POST /auth/reset-password` | 401 `invalid_token` | Integration | P1 |
| T7-06 | auth/router | Reset password clears force_password_change | `force_pwd_user`, valid reset token | `POST /auth/reset-password` | `user.force_password_change == False` | Integration | P1 |
| T7-07 | auth/router | Rate limit: 10 logins allowed per minute | Clean Redis | 10x `POST /auth/login` with wrong password | All 10 return 401 | Integration | P0 |
| T7-08 | auth/router | Rate limit: 11th login blocked | 10 failed logins | 11th `POST /auth/login` | 429 `rate_limit_exceeded`, `retry_after` field present | Integration | P0 |
| T7-09 | auth/router | Rate limit: correct login also blocked after 10 | 10 failed logins from same IP | 11th with correct password | 429 (rate limit is per-IP, not per-user) | Integration | P0 |
| T7-10 | auth/router | Rate limit: different IP not affected | 10 logins from IP-A | Login from IP-B | 200 (or 401 for wrong creds, but not 429) | Integration | P1 |
| T7-11 | tenants/router | Tenant list sort_by=created_at desc (default) | 3 tenants | `GET /tenants` | Items ordered by created_at desc | Integration | P1 |

---

## E) Negative and Security Tests

### E1. Tenant Traversal

| ID | Scenario | Steps | Expected |
|----|----------|-------|----------|
| SEC-01 | Editor tries to read users of another tenant via tenant_id param | `GET /auth/users?tenant_id=<tenant_b.id>` with editor_headers | 403 `permission_denied` |
| SEC-02 | Site_owner tries to create user in another tenant | `POST /auth/users?tenant_id=<tenant_b.id>` with site_owner_headers | 403 `permission_denied` |
| SEC-03 | Editor tries to read a specific user from another tenant | `GET /auth/users/<tenant_b_user.id>?tenant_id=<tenant_b.id>` | 403 `permission_denied` |
| SEC-04 | Forged tenant_id in X-Tenant-ID header (nonexistent UUID) | `POST /auth/login` with `X-Tenant-ID: <random_uuid>` | 404 `tenant_not_found` |
| SEC-05 | Forged tenant_id param pointing to deleted tenant | `GET /auth/users?tenant_id=<deleted_tenant.id>` as platform_owner | 404 `not_found` (soft-deleted) |

### E2. Feature Flag Bypass

| ID | Scenario | Steps | Expected |
|----|----------|-------|----------|
| SEC-06 | Direct URL to disabled module endpoint | `GET /api/v1/admin/reviews` when reviews_module=False | 403 `feature_disabled` |
| SEC-07 | POST to disabled module endpoint | `POST /api/v1/admin/cases` when cases_module=False | 403 `feature_disabled` |
| SEC-08 | Bulk operation with mixed enabled/disabled | `POST /admin/bulk` with resource_type=reviews (disabled) | 403 `feature_disabled` |

### E3. Token After Tenant Deactivation

| ID | Scenario | Steps | Expected |
|----|----------|-------|----------|
| SEC-09 | Access token valid by time but tenant deactivated | 1) Login (get token), 2) Deactivate tenant, 3) Use token for /me | 403 `tenant_inactive` |
| SEC-10 | Refresh token used after tenant deactivation | 1) Login, 2) Deactivate tenant, 3) POST /auth/refresh | 403 `tenant_inactive` |

### E4. Soft-Delete Enforcement

| ID | Scenario | Steps | Expected |
|----|----------|-------|----------|
| SEC-11 | Deleted user cannot login | `POST /auth/login` with deleted_user credentials | 401 `invalid_credentials` |
| SEC-12 | Deleted tenant not served by public API | `GET /public/articles?tenant_id=<deleted_tenant.id>` | 404 `tenant_not_found` |
| SEC-13 | Deleted tenant not returned in tenant list | `GET /tenants` as platform_owner | deleted_tenant NOT in items |

### E5. Information Leakage

| ID | Scenario | Steps | Expected |
|----|----------|-------|----------|
| SEC-14 | Login with wrong password does not reveal user existence | `POST /auth/login` with wrong email | 401 message = "Invalid email or password" (not "User not found") |
| SEC-15 | Forgot password does not reveal user existence | `POST /auth/forgot-password` with wrong email | 204 (same as valid email) |
| SEC-16 | 403 feature_disabled does not reveal internal IDs | Trigger feature_disabled | Response has no user_id, tenant internal info, only `feature` name |
| SEC-17 | 403 tenant_inactive does not reveal tenant details | Trigger tenant_inactive | Response has no tenant name, slug, or internal data |
| SEC-18 | Error responses never contain stack traces in production | Trigger 500 error | `detail` field says "An unexpected error occurred", no traceback |

### E6. Race Conditions (Conceptual — manual or stress test)

| ID | Scenario | Notes |
|----|----------|-------|
| SEC-19 | Feature flag disabled between permission check and DB query | Requires concurrent request; verify no partial data leaked. Test with thread + event. |
| SEC-20 | Tenant deactivated between token validation and DB fetch | Redis cache TTL (30s) means up to 30s delay. Verify cache invalidation works within expected window. |

---

## F) Recommended Stack and Test Structure

### F1. Stack

| Tool | Purpose |
|------|---------|
| `pytest>=8.0` | Test runner |
| `pytest-asyncio>=0.23` | Async test support |
| `pytest-cov>=4.1` | Coverage |
| `pytest-xdist>=3.3` | Parallel execution for unit tests |
| `pytest-timeout>=2.1` | Prevent hanging tests |
| `pytest-mock>=3.11` | `monkeypatch` / `mocker` fixture |
| `httpx>=0.26` | `AsyncClient` for API tests |
| `factory-boy>=3.3` | Test data factories |
| `faker>=19.0` | Random data generation |
| `freezegun>=1.2` | Time freezing for token expiry |
| `respx>=0.20` | Mock httpx HTTP calls (for email providers) |

All already present in `pyproject.toml[dev]` except `freezegun` and `respx`.

**Add to `pyproject.toml`:**

```toml
[project.optional-dependencies]
dev = [
    # ... existing ...
    "freezegun>=1.2.0",
    "respx>=0.20.0",
]
```

### F2. Directory Structure

```
backend/tests/
├── conftest.py                          # Shared fixtures (DB, app, clients, roles, tenants)
├── fixtures/
│   ├── __init__.py
│   ├── factories.py                     # Factory Boy factories (existing + FeatureFlagFactory)
│   └── multi_tenant.py                  # New: multi-tenant specific fixtures
│
├── unit/
│   ├── __init__.py
│   ├── services/
│   │   ├── test_auth_service.py         # Update: add tenant_inactive, reset_password tests
│   │   ├── test_user_service.py         # New: create/update/delete with audit + email
│   │   ├── test_tenant_service.py       # New: create/update/delete with audit + cache
│   │   ├── test_feature_flag_service.py # New: is_enabled, update_flag with audit
│   │   ├── test_role_service.py         # New: CRUD with audit
│   │   ├── test_audit_service.py        # New: AuditService.log()
│   │   └── test_email_service.py        # New: welcome_email, reset_email
│   └── core/
│       ├── test_security.py             # Update: _check_tenant_active, reset token utils
│       └── test_tenant_status_cache.py  # New: Redis cache operations
│
├── integration/
│   ├── __init__.py
│   ├── test_tenant_lifecycle.py         # New: Phase 1 — login/refresh/API blocked for inactive
│   ├── test_feature_flags_routes.py     # New: Phase 2 — each module route returns 403
│   ├── test_cross_tenant_users.py       # New: Phase 3 — platform_owner cross-tenant
│   ├── test_welcome_email.py            # New: Phase 4 — email flow
│   ├── test_feature_catalog.py          # New: Phase 5 — /me/features catalog
│   ├── test_audit_logs.py              # New: Phase 6 — audit on all operations
│   ├── test_password_reset.py           # New: Phase 7 — forgot/reset password
│   ├── test_rate_limiting.py            # New: Phase 7 — login rate limits
│   └── test_tenant_search_sort.py       # New: Phase 7 — tenant list search/sort
│
├── security/
│   ├── __init__.py
│   ├── test_tenant_isolation.py         # New: Section E — tenant traversal, data leak
│   ├── test_feature_bypass.py           # New: direct URL to disabled features
│   ├── test_token_after_deactivation.py # New: valid token + inactive tenant
│   ├── test_soft_delete_enforcement.py  # New: deleted users/tenants blocked
│   └── test_information_leakage.py      # New: error messages don't leak info
│
├── e2e/
│   ├── __init__.py
│   ├── test_tenant_lifecycle_e2e.py     # New: full tenant lifecycle journey
│   ├── test_user_onboarding_e2e.py      # New: create user → email → login → change pwd
│   └── test_cross_tenant_workflow_e2e.py # New: platform_owner manages multiple orgs
│
├── test_auth.py                         # Existing — update with new endpoints
├── test_health.py                       # Existing
└── test_public_api.py                   # Existing — update with tenant_inactive tests
```

### F3. Stabilizing Time and UUIDs

**Time:**

```python
from freezegun import freeze_time

@freeze_time("2026-02-11 12:00:00")
async def test_reset_token_expires_after_1_hour():
    token = create_password_reset_token(user_id, tenant_id, email)
    
    # Advance time by 61 minutes
    with freeze_time("2026-02-11 13:01:00"):
        with pytest.raises(TokenExpiredError):
            decode_password_reset_token(token)
```

**UUIDs:**

```python
# Use deterministic UUIDs in fixtures for readable assertions
TENANT_A_ID = UUID("aaaaaaaa-0000-0000-0000-000000000001")
TENANT_B_ID = UUID("bbbbbbbb-0000-0000-0000-000000000002")
# In factories, use uuid4() for non-deterministic but collision-free IDs
```

### F4. Testing Email Side Effects

```python
# Option 1: monkeypatch (recommended for integration tests)
@pytest.fixture
def mock_email(monkeypatch):
    from unittest.mock import AsyncMock
    mock = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "app.modules.notifications.service.EmailService.send_welcome_email",
        mock,
    )
    return mock

async def test_user_create_sends_email(authenticated_client, mock_email):
    response = await authenticated_client.post("/api/v1/auth/users", json={...})
    assert response.status_code == 201
    mock_email.assert_called_once()
    call_kwargs = mock_email.call_args.kwargs
    assert call_kwargs["to_email"] == "new@example.com"
    assert "password" not in str(call_kwargs)  # Security: no password in email args

# Option 2: respx for external providers (if testing SendGrid/Mailgun)
import respx

@respx.mock
async def test_sendgrid_email():
    respx.post("https://api.sendgrid.com/v3/mail/send").respond(202)
    result = await email_service.send_welcome_email(...)
    assert result is True
```

### F5. Naming Convention

```
test_<component>_<action>_<scenario>

Examples:
test_auth_service_login_rejects_inactive_tenant
test_user_create_sends_welcome_email_when_send_credentials_true
test_feature_flag_blog_disabled_returns_403_on_admin_articles
test_rate_limit_blocks_after_10_failed_logins
test_audit_log_created_on_user_delete
```

---

## G) CI Integration Plan

### G1. PR Pipeline (fast, <5 min)

```yaml
# .github/workflows/test.yml — update existing

jobs:
  lint:
    # Existing — ruff check + format
    
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -e ".[dev]"
        working-directory: backend
      - run: pytest tests/unit -v -n auto --tb=short --timeout=10 --junitxml=reports/unit.xml
        working-directory: backend
    # No DB / Redis needed

  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env: { POSTGRES_DB: cms, POSTGRES_USER: postgres, POSTGRES_PASSWORD: postgres }
        ports: ["5433:5432"]
        options: --health-cmd pg_isready
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
        options: --health-cmd "redis-cli ping"
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install -e ".[dev]"
        working-directory: backend
      - run: alembic upgrade head
        working-directory: backend
      - run: pytest tests/integration tests/security tests/test_*.py -v --tb=short --timeout=30 --junitxml=reports/integration.xml
        working-directory: backend

  coverage:
    needs: [unit-tests, integration-tests]
    runs-on: ubuntu-latest
    services: # same as integration-tests
    steps:
      - run: pytest tests/unit tests/integration --cov=app --cov-report=xml --cov-report=html --cov-fail-under=80
      - uses: codecov/codecov-action@v4
```

### G2. Nightly Pipeline (heavy, <15 min)

```yaml
# .github/workflows/nightly.yml
on:
  schedule:
    - cron: "0 3 * * *"  # 3 AM UTC

jobs:
  full-test-suite:
    services: # postgres + redis
    steps:
      - run: |
          pytest tests/ -v \
            --timeout=60 \
            --junitxml=reports/full.xml \
            --cov=app --cov-report=xml \
            --cov-fail-under=85
      # E2E tests included here
```

### G3. Parallelization and Flakiness Prevention

| Strategy | Implementation |
|----------|---------------|
| Parallel unit tests | `pytest -n auto` (pytest-xdist) — safe because no shared state |
| Sequential integration tests | No `-n` flag — share DB; rollback per test ensures isolation |
| Test isolation | Each test gets fresh `db_session` with automatic rollback |
| Redis isolation | Flush test keys in fixture teardown (`await redis.flushdb()` or key prefix) |
| Deterministic order | No test should depend on execution order; use `pytest-randomly` to detect |
| Retry flaky tests | `pytest-rerunfailures` with `--reruns 2` in CI (last resort) |
| Timeout | `--timeout=30` per test (10 for unit, 30 for integration) |

### G4. CI Artifacts

| Artifact | Format | Purpose |
|----------|--------|---------|
| Test results | JUnit XML (`reports/*.xml`) | GitHub Actions test summary |
| Coverage report | XML + HTML (`htmlcov/`) | Codecov upload + downloadable artifact |
| Failure screenshots | N/A (backend only) | — |
| Test logs | stdout (captured by pytest) | Debug failing tests |

### G5. Minimum Pass Criteria

| Gate | Threshold |
|------|-----------|
| Unit tests | 100% pass |
| Integration tests | 100% pass |
| Security tests | 100% pass |
| Coverage | ≥80% (PR), ≥85% (nightly) |
| Lint | 0 errors |
| No new `# type: ignore` | Policy |
