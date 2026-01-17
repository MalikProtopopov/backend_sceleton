# Localization API

> Multi-language content and locale management

---

## Overview

The CMS supports multi-language content with the following capabilities:
- Multiple enabled locales per tenant
- Localized content for all major entities
- Default locale fallback
- RTL language support

---

## Locale Configuration

Each tenant has locale settings stored in `LocaleConfig` table.

### Data Model

```json
{
  "tenant_id": "tenant-uuid",
  "locale": "ru",
  "name": "Russian",
  "native_name": "Русский",
  "is_enabled": true,
  "is_default": true,
  "is_rtl": false
}
```

### Default Locales

| Code | Name | Native | RTL |
|------|------|--------|-----|
| `ru` | Russian | Русский | No |
| `en` | English | English | No |
| `de` | German | Deutsch | No |
| `ar` | Arabic | العربية | Yes |
| `zh` | Chinese | 中文 | No |

---

## Current Implementation

### Getting Locale Settings

Locale configuration is included in tenant settings:

```bash
GET /api/v1/admin/tenants/{tenant_id}
```

**Response includes:**
```json
{
  "id": "tenant-uuid",
  "name": "Company Name",
  "settings": {...},
  "locale_configs": [
    {
      "locale": "ru",
      "name": "Russian",
      "native_name": "Русский",
      "is_enabled": true,
      "is_default": true,
      "is_rtl": false
    },
    {
      "locale": "en",
      "name": "English",
      "native_name": "English",
      "is_enabled": true,
      "is_default": false,
      "is_rtl": false
    }
  ]
}
```

---

## Localized Content Structure

All content entities with translations use a `locales` array:

### Articles

```json
{
  "id": "article-uuid",
  "status": "published",
  "locales": [
    {
      "locale": "ru",
      "title": "Заголовок статьи",
      "slug": "zagolovok-stati",
      "excerpt": "Краткое описание...",
      "content": "<p>Полный текст...</p>",
      "meta_title": "SEO заголовок",
      "meta_description": "SEO описание"
    },
    {
      "locale": "en",
      "title": "Article Title",
      "slug": "article-title",
      "excerpt": "Brief description...",
      "content": "<p>Full content...</p>",
      "meta_title": "SEO Title",
      "meta_description": "SEO Description"
    }
  ]
}
```

### Localized Entities

| Entity | Localized Fields |
|--------|------------------|
| Article | title, slug, excerpt, content, meta_* |
| Topic | title, slug, description, meta_* |
| Service | title, slug, short_description, description, meta_* |
| Employee | first_name, last_name, position, slug, bio, meta_* |
| FAQ | question, answer |
| Review | content, company_name |
| Practice Area | title, slug, description |
| Advantage | title, description |
| Address | label, city, address_line |

---

## Public API Locale Parameter

All public endpoints accept `locale` query parameter:

```bash
# Get articles in Russian (default)
GET /api/v1/public/articles?tenant_id={uuid}&locale=ru

# Get articles in English
GET /api/v1/public/articles?tenant_id={uuid}&locale=en
```

### Response Behavior

- Returns localized fields for requested locale
- Falls back to default locale if translation missing
- Returns 404 if entity has no translation for requested locale (for single-item endpoints)

---

## Frontend Integration

### Locale Switcher Component

```jsx
const LocaleSwitcher = ({ locales, current, onChange }) => {
  return (
    <Dropdown
      value={current}
      onChange={onChange}
      options={locales.filter(l => l.is_enabled).map(l => ({
        value: l.locale,
        label: l.native_name
      }))}
    />
  )
}
```

### Content Editor with Locale Tabs

```jsx
const LocalizedContentEditor = ({ 
  entity, 
  locales, 
  onSave 
}) => {
  const [activeLocale, setActiveLocale] = useState(
    locales.find(l => l.is_default)?.locale || 'ru'
  )
  
  // Get locale data or empty object for new translations
  const getLocaleData = (locale) => {
    return entity.locales?.find(l => l.locale === locale) || {
      locale,
      title: '',
      slug: '',
      content: ''
    }
  }
  
  // Check translation completeness
  const getTranslationStatus = (locale) => {
    const data = entity.locales?.find(l => l.locale === locale)
    if (!data) return 'missing'
    if (!data.title || !data.content) return 'incomplete'
    return 'complete'
  }
  
  return (
    <div className="localized-editor">
      <Tabs value={activeLocale} onChange={setActiveLocale}>
        {locales.filter(l => l.is_enabled).map(locale => {
          const status = getTranslationStatus(locale.locale)
          return (
            <Tab 
              key={locale.locale} 
              value={locale.locale}
              className={`status-${status}`}
            >
              {locale.native_name}
              {status === 'complete' && ' ✓'}
              {status === 'incomplete' && ' ⚠️'}
              {status === 'missing' && ' ○'}
            </Tab>
          )
        })}
      </Tabs>
      
      <div className="locale-content" dir={getCurrentLocale()?.is_rtl ? 'rtl' : 'ltr'}>
        <LocaleForm 
          data={getLocaleData(activeLocale)}
          locale={activeLocale}
          onChange={(data) => updateLocaleData(activeLocale, data)}
        />
      </div>
    </div>
  )
}
```

### Locale Form Component

```jsx
const LocaleForm = ({ data, locale, onChange }) => {
  const handleChange = (field, value) => {
    onChange({ ...data, [field]: value })
  }
  
  // Auto-generate slug from title
  const generateSlug = (title) => {
    return title
      .toLowerCase()
      .replace(/[^a-z0-9а-яё]+/gi, '-')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '')
  }
  
  return (
    <div className="locale-form">
      <Input
        label="Title"
        value={data.title}
        onChange={(e) => {
          handleChange('title', e.target.value)
          // Auto-generate slug if empty
          if (!data.slug) {
            handleChange('slug', generateSlug(e.target.value))
          }
        }}
        required
      />
      
      <Input
        label="URL Slug"
        value={data.slug}
        onChange={(e) => handleChange('slug', e.target.value)}
        required
        hint={`/${locale}/${data.slug || 'url-slug'}`}
      />
      
      <Textarea
        label="Excerpt"
        value={data.excerpt}
        onChange={(e) => handleChange('excerpt', e.target.value)}
        maxLength={500}
      />
      
      <RichEditor
        label="Content"
        value={data.content}
        onChange={(value) => handleChange('content', value)}
      />
      
      <Collapsible title="SEO Settings">
        <Input
          label="Meta Title"
          value={data.meta_title}
          onChange={(e) => handleChange('meta_title', e.target.value)}
          maxLength={70}
          hint={`${data.meta_title?.length || 0}/70`}
        />
        
        <Textarea
          label="Meta Description"
          value={data.meta_description}
          onChange={(e) => handleChange('meta_description', e.target.value)}
          maxLength={160}
          hint={`${data.meta_description?.length || 0}/160`}
        />
      </Collapsible>
    </div>
  )
}
```

### Translation Status Dashboard

```jsx
const TranslationStatus = () => {
  // Note: This endpoint is NOT yet implemented - see gap-analysis.md
  const [status, setStatus] = useState(null)
  
  useEffect(() => {
    // This would call: GET /api/v1/admin/localization/status
    // Currently not implemented
  }, [])
  
  if (!status) return <Placeholder message="Translation status coming soon" />
  
  return (
    <Dashboard>
      <h2>Translation Coverage</h2>
      
      <Table>
        <thead>
          <tr>
            <th>Content Type</th>
            {Object.keys(status.overall).map(locale => (
              <th key={locale}>{locale.toUpperCase()}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Object.entries(status.by_type).map(([type, locales]) => (
            <tr key={type}>
              <td>{type}</td>
              {Object.entries(locales).map(([locale, percent]) => (
                <td key={locale}>
                  <ProgressBar value={percent} />
                  {percent}%
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </Table>
    </Dashboard>
  )
}
```

### RTL Support

```jsx
// RTL-aware wrapper component
const LocalizedContent = ({ locale, children }) => {
  const { locales } = useTenant()
  const localeConfig = locales.find(l => l.locale === locale)
  
  return (
    <div dir={localeConfig?.is_rtl ? 'rtl' : 'ltr'}>
      {children}
    </div>
  )
}

// CSS for RTL support
const styles = `
  [dir="rtl"] {
    text-align: right;
  }
  
  [dir="rtl"] .sidebar {
    left: auto;
    right: 0;
  }
  
  [dir="rtl"] .icon-arrow {
    transform: rotate(180deg);
  }
`
```

---

## Creating Localized Content

### Request Format

When creating content with translations:

```json
POST /api/v1/admin/articles

{
  "status": "draft",
  "locales": [
    {
      "locale": "ru",
      "title": "Заголовок",
      "slug": "zagolovok",
      "content": "..."
    },
    {
      "locale": "en",
      "title": "Title",
      "slug": "title",
      "content": "..."
    }
  ]
}
```

### Adding Translations Later

To add translations to existing content:

1. Get current content: `GET /admin/articles/{id}`
2. Add new locale to `locales` array
3. Update: `PATCH /admin/articles/{id}` with full `locales` array and `version`

---

## Known Gaps

See [gap-analysis.md](./gap-analysis.md) for:

1. **Locale Management CRUD** - No endpoints to add/remove/update locale settings
2. **Translation Status Report** - No endpoint to see translation completeness
3. **AI Translation** - Not implemented

### Missing Endpoints (Needed)

```
GET /api/v1/admin/locales
POST /api/v1/admin/locales
PATCH /api/v1/admin/locales/{locale}
DELETE /api/v1/admin/locales/{locale}
GET /api/v1/admin/localization/status
```

---

## Best Practices

### Content Guidelines

1. **Translate, don't transliterate** - Adapt content for local audience
2. **Keep slugs consistent** - Use similar slugs across locales when possible
3. **SEO per locale** - Write unique meta tags for each language
4. **Test RTL** - Verify layout for Arabic/Hebrew content

### Technical Guidelines

1. **Always include default locale** - Every entity should have default locale translation
2. **Handle missing translations** - Show fallback or "Translation pending" message
3. **Validate slugs** - Ensure unique slugs within each locale
4. **Store locales in array** - Don't use separate tables per language

