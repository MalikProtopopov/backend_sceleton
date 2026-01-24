# Админ панель: Проекты и Модули

Документация по организации раздела "Проекты" и управлению модулями на фронтенде.

## Архитектура системы

```
┌─────────────────────────────────────────────────────────────────┐
│                        ADMIN PANEL                               │
├─────────────────────────────────────────────────────────────────┤
│  Sidebar                                                         │
│  ┌─────────────────────────────┐                                │
│  │ 🏢 Проекты (platform_owner) │◄── Только для platform_owner   │
│  │   └─ Список всех tenants    │                                │
│  ├─────────────────────────────┤                                │
│  │ 📝 Статьи     (blog_module) │◄── Скрыто если disabled        │
│  │ 💼 Кейсы    (cases_module)  │                                │
│  │ ⭐ Отзывы (reviews_module)  │                                │
│  │ ❓ FAQ        (faq_module)  │                                │
│  │ 👥 Команда   (team_module)  │                                │
│  │ 📊 Заявки                   │◄── Всегда доступен             │
│  │ ⚙️ Настройки                │                                │
│  └─────────────────────────────┘                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Роли и доступы

### Иерархия ролей

| Роль | Описание | Доступ к проектам | Управление модулями |
|------|----------|-------------------|---------------------|
| `superuser` | Суперадмин | Все проекты | Да |
| `platform_owner` | Владелец платформы | Все проекты | Да |
| `site_owner` | Администратор сайта | Только свой tenant | Нет |
| `content_manager` | Контент-менеджер | Только свой tenant | Нет |
| `marketer` | Маркетолог | Только свой tenant | Нет |
| `editor` | Редактор | Только свой tenant | Нет |

### Permissions (разрешения)

```typescript
// Проверка роли для раздела "Проекты"
const canManageProjects = user.is_superuser || user.role === 'platform_owner';

// Проверка доступа к управлению модулями
const canManageModules = user.permissions.includes('features:update') || 
                         user.permissions.includes('platform:*');
```

---

## API Endpoints

### 1. Получение информации о текущем пользователе

```http
GET /api/v1/auth/me
Authorization: Bearer {token}
```

**Response:**
```json
{
  "id": "uuid",
  "tenant_id": "63d068f7-7a47-46fe-aeb0-c82588e995a4",
  "email": "admin@example.com",
  "first_name": "Admin",
  "last_name": "User",
  "is_superuser": true,
  "role": {
    "name": "platform_owner",
    "description": "Platform administrator"
  },
  "permissions": [
    "platform:read",
    "platform:update",
    "features:read",
    "features:update",
    "articles:*",
    "cases:*",
    ...
  ]
}
```

---

### 2. Получение включенных модулей для сайдбара

```http
GET /api/v1/auth/me/features
Authorization: Bearer {token}
```

**Response для обычного пользователя:**
```json
{
  "enabled_features": ["blog_module", "cases_module", "reviews_module"],
  "all_features_enabled": false
}
```

**Response для platform_owner/superuser:**
```json
{
  "enabled_features": [],
  "all_features_enabled": true
}
```

> **Важно:** Если `all_features_enabled: true` — показывать все разделы в сайдбаре.
> Иначе — показывать только те, что есть в `enabled_features`.

---

### 3. Список проектов (только platform_owner) {#list-projects}

```http
GET /api/v1/tenants?page=1&page_size=20&is_active=true
Authorization: Bearer {token}
```

**Доступ:** `platform_owner`, `superuser`

**Response:**
```json
{
  "items": [
    {
      "id": "63d068f7-7a47-46fe-aeb0-c82588e995a4",
      "name": "Клиника волос",
      "slug": "hair-clinic",
      "domain": "hair-clinic.com",
      "is_active": true,
      "logo_url": "https://...",
      "primary_color": "#1E40AF",
      "contact_email": "admin@hair-clinic.com",
      "version": 5,
      "created_at": "2026-01-15T10:00:00Z",
      "settings": {
        "default_locale": "ru",
        "timezone": "Europe/Moscow"
      }
    }
  ],
  "total": 15,
  "page": 1,
  "page_size": 20
}
```

---

### 3. Получение конкретного проекта

```http
GET /api/v1/tenants/{tenant_id}
Authorization: Bearer {token}
```

**Доступ:**
- `platform_owner` / `superuser` → любой tenant
- Остальные → только свой tenant

---

### 4. Создание проекта (только platform_owner)

```http
POST /api/v1/tenants
Authorization: Bearer {token}
Content-Type: application/json
```

**Request:**
```json
{
  "name": "Новый клиент",
  "slug": "new-client",
  "domain": "new-client.com",
  "is_active": true,
  "contact_email": "admin@new-client.com",
  "primary_color": "#3B82F6"
}
```

---

### 5. Обновление проекта

```http
PATCH /api/v1/tenants/{tenant_id}
Authorization: Bearer {token}
Content-Type: application/json
```

**Request:**
```json
{
  "name": "Обновленное название",
  "is_active": true,
  "version": 5
}
```

> ⚠️ `version` обязателен для optimistic locking

---

### 6. Список feature flags (модулей)

```http
GET /api/v1/feature-flags
Authorization: Bearer {token}
X-Tenant-ID: {tenant_id}
```

**Доступ:** `platform_owner`, `superuser`

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "tenant_id": "63d068f7-7a47-46fe-aeb0-c82588e995a4",
      "feature_name": "cases_module",
      "enabled": true,
      "description": "Case studies / portfolio module"
    },
    {
      "id": "uuid",
      "tenant_id": "63d068f7-7a47-46fe-aeb0-c82588e995a4",
      "feature_name": "blog_module",
      "enabled": false,
      "description": "Blog / articles module"
    }
  ],
  "available_features": {
    "cases_module": "Case studies / portfolio module",
    "reviews_module": "Client testimonials module",
    "seo_advanced": "Advanced SEO features",
    "multilang": "Multi-language content support",
    "analytics_advanced": "Detailed lead analytics",
    "blog_module": "Blog / articles module",
    "faq_module": "FAQ module",
    "team_module": "Team / employees module"
  }
}
```

---

### 7. Включение/отключение модуля

```http
PATCH /api/v1/feature-flags/{feature_name}
Authorization: Bearer {token}
X-Tenant-ID: {tenant_id}
Content-Type: application/json
```

**Request:**
```json
{
  "enabled": true
}
```

**Response:**
```json
{
  "id": "uuid",
  "tenant_id": "63d068f7-7a47-46fe-aeb0-c82588e995a4",
  "feature_name": "cases_module",
  "enabled": true,
  "description": "Case studies / portfolio module"
}
```

---

## Доступные модули (feature flags)

| Feature Name | Название | Описание |
|--------------|----------|----------|
| `blog_module` | Блог/Статьи | Модуль публикации статей |
| `cases_module` | Кейсы | Портфолио/Case studies |
| `reviews_module` | Отзывы | Отзывы клиентов |
| `faq_module` | FAQ | Часто задаваемые вопросы |
| `team_module` | Команда | Сотрудники компании |
| `multilang` | Мультиязычность | Поддержка нескольких языков |
| `seo_advanced` | Расширенное SEO | Redirects, custom meta |
| `analytics_advanced` | Аналитика | UTM, geo, device tracking |

---

## Frontend Implementation

### TypeScript Interfaces

```typescript
// types/tenant.ts
export interface Tenant {
  id: string;
  name: string;
  slug: string;
  domain: string | null;
  is_active: boolean;
  logo_url: string | null;
  primary_color: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  version: number;
  created_at: string;
  updated_at: string;
  settings: TenantSettings | null;
}

export interface TenantSettings {
  id: string;
  tenant_id: string;
  default_locale: string;
  timezone: string;
  date_format: string;
  time_format: string;
  notify_on_inquiry: boolean;
  inquiry_email: string | null;
  telegram_chat_id: string | null;
}

export interface FeatureFlag {
  id: string;
  tenant_id: string;
  feature_name: string;
  enabled: boolean;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface FeatureFlagsResponse {
  items: FeatureFlag[];
  available_features: Record<string, string>;
}

export interface User {
  id: string;
  tenant_id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_superuser: boolean;
  role: {
    name: string;
    description: string;
  } | null;
  permissions: string[];
}
```

### React Hooks

```typescript
// hooks/useProjects.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

export function useProjects(page = 1, pageSize = 20, isActive?: boolean) {
  return useQuery({
    queryKey: ['tenants', page, pageSize, isActive],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: String(page),
        page_size: String(pageSize),
      });
      if (isActive !== undefined) {
        params.append('is_active', String(isActive));
      }
      const { data } = await api.get(`/api/v1/tenants?${params}`);
      return data;
    },
  });
}

export function useProject(tenantId: string) {
  return useQuery({
    queryKey: ['tenant', tenantId],
    queryFn: async () => {
      const { data } = await api.get(`/api/v1/tenants/${tenantId}`);
      return data;
    },
    enabled: !!tenantId,
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (data: Partial<Tenant>) => {
      const { data: response } = await api.post('/api/v1/tenants', data);
      return response;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
    },
  });
}

export function useUpdateProject() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ id, ...data }: { id: string } & Partial<Tenant>) => {
      const { data: response } = await api.patch(`/api/v1/tenants/${id}`, data);
      return response;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
      queryClient.invalidateQueries({ queryKey: ['tenant', variables.id] });
    },
  });
}
```

```typescript
// hooks/useFeatureFlags.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

export function useFeatureFlags(tenantId: string) {
  return useQuery({
    queryKey: ['feature-flags', tenantId],
    queryFn: async () => {
      const { data } = await api.get('/api/v1/feature-flags', {
        headers: { 'X-Tenant-ID': tenantId },
      });
      return data as FeatureFlagsResponse;
    },
    enabled: !!tenantId,
  });
}

export function useToggleFeature(tenantId: string) {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ featureName, enabled }: { featureName: string; enabled: boolean }) => {
      const { data } = await api.patch(
        `/api/v1/feature-flags/${featureName}`,
        { enabled },
        { headers: { 'X-Tenant-ID': tenantId } }
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['feature-flags', tenantId] });
    },
  });
}
```

### Sidebar Component

```tsx
// hooks/useEnabledFeatures.ts
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

interface EnabledFeaturesResponse {
  enabled_features: string[];
  all_features_enabled: boolean;
}

export function useEnabledFeatures() {
  return useQuery({
    queryKey: ['enabled-features'],
    queryFn: async () => {
      const { data } = await api.get<EnabledFeaturesResponse>('/api/v1/auth/me/features');
      return data;
    },
    staleTime: 5 * 60 * 1000, // 5 минут
  });
}
```

```tsx
// components/Sidebar.tsx
import { useCurrentUser } from '@/hooks/useAuth';
import { useEnabledFeatures } from '@/hooks/useEnabledFeatures';

interface SidebarItem {
  name: string;
  href: string;
  icon: React.ComponentType;
  feature?: string; // Привязка к feature flag
  permission?: string; // Минимальное разрешение
}

const sidebarItems: SidebarItem[] = [
  // Всегда видимые
  { name: 'Дашборд', href: '/dashboard', icon: HomeIcon },
  { name: 'Заявки', href: '/inquiries', icon: InboxIcon, permission: 'inquiries:read' },
  
  // Зависят от feature flags
  { name: 'Статьи', href: '/articles', icon: DocumentIcon, feature: 'blog_module', permission: 'articles:read' },
  { name: 'Кейсы', href: '/cases', icon: BriefcaseIcon, feature: 'cases_module', permission: 'cases:read' },
  { name: 'Отзывы', href: '/reviews', icon: StarIcon, feature: 'reviews_module', permission: 'reviews:read' },
  { name: 'FAQ', href: '/faq', icon: QuestionIcon, feature: 'faq_module', permission: 'faq:read' },
  { name: 'Команда', href: '/team', icon: UsersIcon, feature: 'team_module', permission: 'employees:read' },
  
  // Настройки
  { name: 'Услуги', href: '/services', icon: CogIcon, permission: 'services:read' },
  { name: 'SEO', href: '/seo', icon: SearchIcon, permission: 'seo:read' },
  { name: 'Настройки', href: '/settings', icon: SettingsIcon, permission: 'settings:read' },
];

// Раздел для platform_owner
const platformItems: SidebarItem[] = [
  { name: 'Проекты', href: '/projects', icon: BuildingIcon },
];

export function Sidebar() {
  const { data: user } = useCurrentUser();
  const { data: features } = useEnabledFeatures();
  
  const isPlatformOwner = user?.is_superuser || user?.role?.name === 'platform_owner';
  
  // Проверка разрешения
  const hasPermission = (permission?: string) => {
    if (!permission) return true;
    if (user?.is_superuser) return true;
    
    // Проверяем точное совпадение или wildcard
    const resource = permission.split(':')[0];
    return user?.permissions.includes(permission) || 
           user?.permissions.includes(`${resource}:*`);
  };
  
  // Проверка включена ли фича (используем новый эндпоинт)
  const isFeatureEnabled = (feature?: string) => {
    if (!feature) return true;
    // all_features_enabled=true для platform_owner/superuser
    if (features?.all_features_enabled) return true;
    return features?.enabled_features.includes(feature) ?? false;
  };
  
  // Фильтруем элементы сайдбара
  const visibleItems = sidebarItems.filter(item => 
    hasPermission(item.permission) && isFeatureEnabled(item.feature)
  );
  
  return (
    <nav className="sidebar">
      {/* Раздел проектов для platform_owner */}
      {isPlatformOwner && (
        <div className="sidebar-section">
          <h3 className="sidebar-section-title">Платформа</h3>
          {platformItems.map(item => (
            <SidebarLink key={item.href} item={item} />
          ))}
        </div>
      )}
      
      {/* Основное меню */}
      <div className="sidebar-section">
        <h3 className="sidebar-section-title">Контент</h3>
        {visibleItems.map(item => (
          <SidebarLink key={item.href} item={item} />
        ))}
      </div>
    </nav>
  );
}
```

### Projects Page

```tsx
// pages/projects/index.tsx
import { useState } from 'react';
import { useProjects } from '@/hooks/useProjects';
import { ProjectCard } from '@/components/ProjectCard';

export default function ProjectsPage() {
  const [page, setPage] = useState(1);
  const [filter, setFilter] = useState<boolean | undefined>(undefined);
  
  const { data, isLoading } = useProjects(page, 20, filter);
  
  return (
    <div className="projects-page">
      <header className="page-header">
        <h1>Проекты</h1>
        <Button href="/projects/new">+ Создать проект</Button>
      </header>
      
      {/* Фильтры */}
      <div className="filters">
        <Select
          value={filter === undefined ? 'all' : filter ? 'active' : 'inactive'}
          onChange={(v) => setFilter(v === 'all' ? undefined : v === 'active')}
        >
          <option value="all">Все проекты</option>
          <option value="active">Активные</option>
          <option value="inactive">Неактивные</option>
        </Select>
      </div>
      
      {/* Сетка проектов */}
      {isLoading ? (
        <Skeleton count={6} />
      ) : (
        <div className="projects-grid">
          {data?.items.map((project) => (
            <ProjectCard key={project.id} project={project} />
          ))}
        </div>
      )}
      
      {/* Пагинация */}
      <Pagination
        page={page}
        totalPages={Math.ceil((data?.total || 0) / 20)}
        onPageChange={setPage}
      />
    </div>
  );
}
```

### Project Modules Page

```tsx
// pages/projects/[id]/modules.tsx
import { useParams } from 'next/navigation';
import { useProject } from '@/hooks/useProjects';
import { useFeatureFlags, useToggleFeature } from '@/hooks/useFeatureFlags';
import { Switch } from '@/components/ui/Switch';

// Маппинг feature_name -> человеко-понятное название и иконка
const FEATURE_META: Record<string, { name: string; icon: string; description: string }> = {
  blog_module: { 
    name: 'Блог / Статьи', 
    icon: '📝',
    description: 'Публикация статей и новостей' 
  },
  cases_module: { 
    name: 'Кейсы / Портфолио', 
    icon: '💼',
    description: 'Демонстрация выполненных проектов' 
  },
  reviews_module: { 
    name: 'Отзывы', 
    icon: '⭐',
    description: 'Отзывы клиентов' 
  },
  faq_module: { 
    name: 'FAQ', 
    icon: '❓',
    description: 'Часто задаваемые вопросы' 
  },
  team_module: { 
    name: 'Команда', 
    icon: '👥',
    description: 'Информация о сотрудниках' 
  },
  multilang: { 
    name: 'Мультиязычность', 
    icon: '🌐',
    description: 'Поддержка нескольких языков' 
  },
  seo_advanced: { 
    name: 'Расширенное SEO', 
    icon: '🔍',
    description: 'Редиректы, custom meta теги' 
  },
  analytics_advanced: { 
    name: 'Расширенная аналитика', 
    icon: '📊',
    description: 'UTM, geo, device tracking' 
  },
};

export default function ProjectModulesPage() {
  const { id: tenantId } = useParams<{ id: string }>();
  const { data: project } = useProject(tenantId);
  const { data: features, isLoading } = useFeatureFlags(tenantId);
  const toggleFeature = useToggleFeature(tenantId);
  
  const handleToggle = async (featureName: string, currentValue: boolean) => {
    await toggleFeature.mutateAsync({
      featureName,
      enabled: !currentValue,
    });
  };
  
  if (isLoading) return <Skeleton />;
  
  return (
    <div className="modules-page">
      <header className="page-header">
        <nav className="breadcrumb">
          <Link href="/projects">Проекты</Link>
          <span>/</span>
          <Link href={`/projects/${tenantId}`}>{project?.name}</Link>
          <span>/</span>
          <span>Модули</span>
        </nav>
        <h1>Управление модулями</h1>
        <p className="text-muted">
          Включайте и отключайте функционал для проекта "{project?.name}"
        </p>
      </header>
      
      <div className="modules-grid">
        {features?.available_features && 
          Object.entries(features.available_features).map(([featureName, description]) => {
            const flag = features.items.find(f => f.feature_name === featureName);
            const isEnabled = flag?.enabled ?? false;
            const meta = FEATURE_META[featureName] || { 
              name: featureName, 
              icon: '📦',
              description 
            };
            
            return (
              <div 
                key={featureName} 
                className={`module-card ${isEnabled ? 'enabled' : 'disabled'}`}
              >
                <div className="module-icon">{meta.icon}</div>
                <div className="module-info">
                  <h3 className="module-name">{meta.name}</h3>
                  <p className="module-description">{meta.description}</p>
                </div>
                <Switch
                  checked={isEnabled}
                  onChange={() => handleToggle(featureName, isEnabled)}
                  disabled={toggleFeature.isPending}
                />
              </div>
            );
          })
        }
      </div>
    </div>
  );
}
```

---

## Логика отображения в сайдбаре

### Алгоритм

```typescript
function shouldShowSidebarItem(
  item: SidebarItem,
  user: User,
  enabledFeatures: Set<string>
): boolean {
  // 1. Проверяем разрешение
  if (item.permission) {
    const hasPermission = checkPermission(user, item.permission);
    if (!hasPermission) return false;
  }
  
  // 2. Если platform_owner - показываем всё
  if (user.is_superuser || user.role?.name === 'platform_owner') {
    return true;
  }
  
  // 3. Проверяем feature flag
  if (item.feature && !enabledFeatures.has(item.feature)) {
    return false;
  }
  
  return true;
}
```

### Маппинг разделов → feature flags

| Раздел в сайдбаре | Feature Flag | Permission |
|-------------------|--------------|------------|
| Дашборд | - | - |
| Заявки | - | `inquiries:read` |
| Статьи | `blog_module` | `articles:read` |
| Кейсы | `cases_module` | `cases:read` |
| Отзывы | `reviews_module` | `reviews:read` |
| FAQ | `faq_module` | `faq:read` |
| Команда | `team_module` | `employees:read` |
| Услуги | - | `services:read` |
| SEO | - | `seo:read` |
| Настройки | - | `settings:read` |
| **Проекты** | - | `platform:*` (только platform_owner) |

---

## Best Practices

### 1. Кэширование feature flags

```typescript
// Кэшируем на 5 минут, обновляем в фоне
const { data: features } = useFeatureFlags(tenantId, {
  staleTime: 5 * 60 * 1000, // 5 минут
  refetchOnWindowFocus: false,
});
```

### 2. Optimistic Updates для переключателей

```typescript
const toggleFeature = useToggleFeature(tenantId);

// При клике сразу меняем UI
const handleToggle = (featureName: string, enabled: boolean) => {
  // Optimistic update
  queryClient.setQueryData(['feature-flags', tenantId], (old) => ({
    ...old,
    items: old.items.map(f => 
      f.feature_name === featureName ? { ...f, enabled: !enabled } : f
    ),
  }));
  
  // Затем отправляем запрос
  toggleFeature.mutate(
    { featureName, enabled: !enabled },
    {
      onError: () => {
        // Откатываем при ошибке
        queryClient.invalidateQueries(['feature-flags', tenantId]);
      },
    }
  );
};
```

### 3. Защита роутов

```typescript
// middleware.ts или layout.tsx
import { redirect } from 'next/navigation';

export default function ProjectsLayout({ children }) {
  const { data: user } = useCurrentUser();
  
  const canAccessProjects = user?.is_superuser || 
                            user?.role?.name === 'platform_owner';
  
  if (!canAccessProjects) {
    redirect('/dashboard');
  }
  
  return children;
}
```

### 4. Обработка 403 ошибок

```typescript
// При попытке доступа к отключенному модулю
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 403) {
      const detail = error.response.data?.detail;
      
      if (detail?.includes('Feature') && detail?.includes('disabled')) {
        // Показываем уведомление
        toast.error('Этот модуль отключен для вашего сайта');
        // Редиректим на дашборд
        router.push('/dashboard');
      }
    }
    return Promise.reject(error);
  }
);
```

---

## Структура страниц

```
/projects                     # Список проектов (platform_owner only)
/projects/new                 # Создание проекта
/projects/[id]               # Детали проекта
/projects/[id]/edit          # Редактирование проекта
/projects/[id]/modules       # Управление модулями (switchers)
/projects/[id]/settings      # Настройки проекта
/projects/[id]/users         # Пользователи проекта
```

---

## Примечания

1. **X-Tenant-ID header** — при работе с конкретным проектом из раздела "Проекты" передавайте `X-Tenant-ID` в заголовке запросов

2. **Переключение контекста** — при переходе в проект platform_owner работает "от имени" этого tenant'а

3. **Версионирование** — при обновлении tenant используйте `version` для optimistic locking

4. **Логотип** — загружается отдельным запросом `POST /tenants/{id}/logo` с `multipart/form-data`
