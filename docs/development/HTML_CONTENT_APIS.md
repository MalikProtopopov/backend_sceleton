# API Endpoints with HTML Content
## Corporate CMS Admin Panel

**Date:** January 15, 2026  
**Purpose:** List of all API endpoints that accept or return HTML content

---

## 📋 Summary

The following API endpoints work with HTML content. These fields accept HTML markup and should be rendered using a rich text editor (WYSIWYG) on the frontend.

**Total:** 8 endpoints with HTML content fields

---

## ✅ Articles API

### 1. POST /api/v1/admin/articles
**Create Article**

**HTML Fields:**
- `locales[].content` - Full article content (HTML)

**Schema:**
```json
{
  "locales": [
    {
      "locale": "en",
      "title": "Article Title",
      "slug": "article-slug",
      "excerpt": "Short description",
      "content": "<p>Full HTML content here...</p><h2>Subtitle</h2><p>More content</p>",
      "meta_title": "SEO Title",
      "meta_description": "SEO Description"
    }
  ],
  "status": "draft",
  "topic_ids": []
}
```

**Documentation:** [`02-articles.md`](./api/02-articles.md)

---

### 2. PATCH /api/v1/admin/articles/{id}
**Update Article**

**HTML Fields:**
- `locales[].content` - Full article content (HTML)

**Schema:**
```json
{
  "locales": [
    {
      "locale": "en",
      "content": "<p>Updated HTML content...</p>"
    }
  ],
  "version": 1
}
```

**Documentation:** [`02-articles.md`](./api/02-articles.md)

---

### 3. GET /api/v1/admin/articles/{id}
**Get Article**

**HTML Fields in Response:**
- `locales[].content` - Full article content (HTML)

**Response Example:**
```json
{
  "id": "uuid",
  "locales": [
    {
      "locale": "en",
      "title": "Article Title",
      "content": "<p>Full HTML content...</p>",
      ...
    }
  ]
}
```

**Documentation:** [`02-articles.md`](./api/02-articles.md)

---

### 4. GET /api/v1/public/articles/{slug}
**Get Public Article**

**HTML Fields in Response:**
- `content` - Full article content (HTML)

**Response Example:**
```json
{
  "id": "uuid",
  "slug": "article-slug",
  "title": "Article Title",
  "content": "<p>Full HTML content...</p>",
  ...
}
```

**Documentation:** [`02-articles.md`](./api/02-articles.md)

---

## ✅ Cases API

### 5. POST /api/v1/admin/cases
**Create Case Study**

**HTML Fields:**
- `locales[].description` - Case description (HTML, optional)
- `locales[].results` - Case results/outcomes (HTML, optional)

**Schema:**
```json
{
  "locales": [
    {
      "locale": "en",
      "title": "Case Title",
      "slug": "case-slug",
      "description": "<p>Short HTML description...</p>",
      "results": "<h2>Results</h2><p>HTML content with outcomes...</p>",
      ...
    }
  ],
  "service_ids": ["uuid"],
  "is_published": false
}
```

**Documentation:** [`14-cases-dashboard-bulk.md`](./api/14-cases-dashboard-bulk.md)

---

### 6. PATCH /api/v1/admin/cases/{id}
**Update Case Study**

**HTML Fields:**
- `locales[].description` - Case description (HTML, optional)
- `locales[].results` - Case results/outcomes (HTML, optional)

**Documentation:** [`14-cases-dashboard-bulk.md`](./api/14-cases-dashboard-bulk.md)

---

### 7. GET /api/v1/admin/cases/{id}
**Get Case Study**

**HTML Fields in Response:**
- `locales[].description` - Case description (HTML, optional)
- `locales[].results` - Case results/outcomes (HTML, optional)

**Documentation:** [`14-cases-dashboard-bulk.md`](./api/14-cases-dashboard-bulk.md)

---

### 8. GET /api/v1/public/cases/{slug}
**Get Public Case Study**

**HTML Fields in Response:**
- `description` - Case description (HTML, optional)
- `results` - Case results/outcomes (HTML, optional)

**Documentation:** [`14-cases-dashboard-bulk.md`](./api/14-cases-dashboard-bulk.md)

---

## ⚠️ FAQ API (Plain Text, Not HTML)

**Note:** FAQ answers are stored as plain text (`Text` type), not HTML.

**Endpoints:**
- POST /api/v1/admin/faq
- PATCH /api/v1/admin/faq/{id}
- GET /api/v1/admin/faq/{id}
- GET /api/v1/public/faq

**Field:** `locales[].answer` - Plain text, not HTML

**Documentation:** [`03-faq.md`](./api/03-faq.md)

---

## ⚠️ Services API (Description May Contain HTML)

### Services Description

**Endpoints:**
- POST /api/v1/admin/services
- PATCH /api/v1/admin/services/{id}
- GET /api/v1/admin/services/{id}
- GET /api/v1/public/services

**HTML Fields:**
- `locales[].description` - Service description (can contain HTML, stored as `Text`)

**Note:** While stored as `Text` type, this field may contain HTML markup if the frontend allows it.

**Documentation:** [`05-services.md`](./api/05-services.md)

---

## ⚠️ Employees API (Description May Contain HTML)

### Employee Bio/Description

**Endpoints:**
- POST /api/v1/admin/employees
- PATCH /api/v1/admin/employees/{id}
- GET /api/v1/admin/employees/{id}
- GET /api/v1/public/employees

**HTML Fields:**
- `locales[].description` - Employee bio/description (can contain HTML, stored as `Text`)

**Note:** While stored as `Text` type, this field may contain HTML markup if the frontend allows it.

**Documentation:** [`06-employees.md`](./api/06-employees.md)

---

## ⚠️ Practice Areas API (Description May Contain HTML)

**Endpoints:**
- POST /api/v1/admin/practice-areas
- PATCH /api/v1/admin/practice-areas/{id}
- GET /api/v1/admin/practice-areas/{id}
- GET /api/v1/public/practice-areas

**HTML Fields:**
- `locales[].description` - Practice area description (can contain HTML, stored as `Text`)

**Documentation:** [`15-audit-export-search.md`](./api/15-audit-export-search.md)

---

## 📊 Summary Table

| Module | Endpoint | HTML Field | Type | Required |
|--------|----------|------------|------|----------|
| **Articles** | POST/PATCH/GET | `locales[].content` | HTML | Optional |
| **Cases** | POST/PATCH/GET | `locales[].description` | HTML | Optional |
| **Cases** | POST/PATCH/GET | `locales[].results` | HTML | Optional |
| **Services** | POST/PATCH/GET | `locales[].description` | Text (may be HTML) | Optional |
| **Employees** | POST/PATCH/GET | `locales[].description` | Text (may be HTML) | Optional |
| **Practice Areas** | POST/PATCH/GET | `locales[].description` | Text (may be HTML) | Optional |
| **FAQ** | POST/PATCH/GET | `locales[].answer` | Plain Text | Required |

---

## 🎨 Frontend Recommendations

### Rich Text Editors

For HTML content fields, use a WYSIWYG editor:

**Recommended Libraries:**
1. **Tiptap** (React/Vue) - Modern, extensible
2. **Quill** (React/Vue) - Popular, well-documented
3. **Draft.js** (React) - Facebook's editor
4. **CKEditor 5** (React/Vue/Angular) - Enterprise-grade

**Example with Tiptap:**
```tsx
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'

const ArticleEditor = ({ content, onChange }) => {
  const editor = useEditor({
    extensions: [StarterKit],
    content: content || '',
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML())
    },
  })

  return <EditorContent editor={editor} />
}
```

---

### HTML Sanitization

**Important:** Always sanitize HTML content before saving or displaying!

**Recommended Libraries:**
1. **DOMPurify** - Most popular, battle-tested
2. **sanitize-html** - Node.js/React compatible

**Example:**
```typescript
import DOMPurify from 'dompurify'

// Before saving
const sanitized = DOMPurify.sanitize(htmlContent, {
  ALLOWED_TAGS: ['p', 'h1', 'h2', 'h3', 'strong', 'em', 'ul', 'ol', 'li', 'a', 'img'],
  ALLOWED_ATTR: ['href', 'src', 'alt', 'title'],
})

// Before displaying
<div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(content) }} />
```

---

### Allowed HTML Tags

**Recommended whitelist for content fields:**

```typescript
const ALLOWED_TAGS = [
  'p', 'br', 'strong', 'em', 'u', 's',
  'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
  'ul', 'ol', 'li',
  'a', 'img',
  'blockquote', 'pre', 'code',
  'div', 'span',
  'table', 'thead', 'tbody', 'tr', 'th', 'td',
  'hr'
]

const ALLOWED_ATTR = {
  'a': ['href', 'title', 'target'],
  'img': ['src', 'alt', 'title', 'width', 'height'],
  'table': ['class'],
  'td': ['colspan', 'rowspan']
}
```

---

## 🔒 Security Considerations

### XSS Prevention

1. **Always sanitize on save** - Clean HTML before storing in database
2. **Sanitize on display** - Even if stored clean, sanitize again on render
3. **Content Security Policy** - Set CSP headers to prevent inline scripts
4. **Validate on backend** - Consider adding HTML validation in API

### Backend Validation (Optional)

You could add HTML validation in the backend:

```python
from html.parser import HTMLParser
from html import unescape

class HTMLValidator:
    ALLOWED_TAGS = {'p', 'h1', 'h2', 'h3', 'strong', 'em', ...}
    
    def validate(self, html: str) -> bool:
        # Parse and check tags
        # Return True if valid, False otherwise
        pass
```

---

## 📝 Database Schema

### Text Fields (Can Store HTML)

All HTML content is stored in PostgreSQL `Text` columns:

```sql
-- Articles
article_locales.content TEXT NULL

-- Cases
case_locales.description TEXT NULL
case_locales.results TEXT NULL

-- Services
service_locales.description TEXT NULL

-- Employees
employee_locales.description TEXT NULL

-- Practice Areas
practice_area_locales.description TEXT NULL
```

**Note:** No length limits on `Text` fields - they can store large HTML documents.

---

## 🧪 Testing HTML Content

### Test Cases

1. **Basic HTML:**
   ```json
   {
     "content": "<p>Hello <strong>world</strong>!</p>"
   }
   ```

2. **Complex HTML:**
   ```json
   {
     "content": "<h1>Title</h1><p>Paragraph with <a href='#'>link</a></p><ul><li>Item 1</li></ul>"
   }
   ```

3. **XSS Attempt (should be sanitized):**
   ```json
   {
     "content": "<script>alert('XSS')</script><p>Safe content</p>"
   }
   ```

4. **Empty content:**
   ```json
   {
     "content": null
   }
   ```

---

## 📚 Related Documentation

- [Articles API](./api/02-articles.md) - Full article endpoints
- [Cases API](./api/14-cases-dashboard-bulk.md) - Case study endpoints
- [Services API](./api/05-services.md) - Service endpoints
- [Employees API](./api/06-employees.md) - Employee endpoints
- [FAQ API](./api/03-faq.md) - FAQ endpoints (plain text)

---

## ✅ Checklist for Frontend

- [ ] Choose WYSIWYG editor (Tiptap/Quill/CKEditor)
- [ ] Implement HTML sanitization (DOMPurify)
- [ ] Configure allowed tags/attributes
- [ ] Test XSS prevention
- [ ] Handle empty/null content
- [ ] Add loading states for large content
- [ ] Implement content preview
- [ ] Add character count (optional)
- [ ] Test with special characters
- [ ] Test with large HTML documents

---

**Last Updated:** January 15, 2026  
**Next Review:** When implementing frontend rich text editors

