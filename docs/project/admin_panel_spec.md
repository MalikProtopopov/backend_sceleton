psql -U postgres -d cms_db -f /Users/mak/mediannback/docs/test_db/mediann_seed.sql# Admin Panel Product Spec + UX Blueprint
## Corporate CMS Engine v1.0 — Administrative Interface

**Document Version:** 1.0  
**Date:** January 14, 2026  
**Audience:** Product Managers, UX Designers, Frontend/Backend Engineers  
**Status:** ✅ Ready for Design & Development

---

## 📑 Table of Contents

1. [Executive Summary](#executive-summary)
2. [User Roles & Jobs-to-be-Done (JTBD)](#user-roles--jobs-to-be-done)
3. [Information Architecture (IA) & Navigation](#information-architecture--navigation)
4. [Core CRUD UX Patterns](#core-crud-ux-patterns)
5. [Forms & Content Editors](#forms--content-editors)
6. [Publishing & Content Workflow](#publishing--content-workflow)
7. [Localization Management](#localization-management)
8. [SEO Center](#seo-center)
9. [Media Library](#media-library)
10. [Leads & Inquiries Management](#leads--inquiries-management)
11. [Security, RBAC & Audit](#security-rbac--audit)
12. [Accessibility (WCAG/ARIA)](#accessibility-wcagarial)
13. [Screen List & Component Inventory](#screen-list--component-inventory)
14. [Design System & UI Kit Requirements](#design-system--ui-kit-requirements)
15. [Implementation Roadmap](#implementation-roadmap)
16. [Risks & Antipatterns](#risks--antipatterns)

---

## Executive Summary

This admin panel is designed as a **reusable, multi-tenant engine** serving content editors, marketing managers, SEO specialists, HR teams, and system administrators. The architecture prioritizes:

- **Efficiency:** Bulk operations, keyboard shortcuts, rapid data entry
- **Safety:** Soft deletes, draft autosave, confirmation dialogs for destructive actions
- **Clarity:** Consistent status indicators, clear error messages, audit trails
- **Scalability:** Role-based access control, feature flags for tenant customization
- **Accessibility:** WCAG 2.1 Level AA compliance, keyboard-first navigation

**Key Principle:** The panel should feel like a "spreadsheet with superpowers"—fast, predictable, and familiar to power users while remaining discoverable for casual users.

---

## User Roles & Jobs-to-be-Done

### 1. **Owner / Director**

**JTBD:** "I need a bird's-eye view of the company site: what's published, what's in review, who's working on what, and key metrics."

**Top Tasks:**
- Review publishing status dashboard
- Check team workload
- Approve sensitive content (press releases, job postings)
- Audit who changed what (via Audit Log)

**Data Access:** All entities (read + approve)  
**Permissions:** Publish/Archive; Manage users and roles; View audit logs  
**Pain Points (typical):** Hid in menus, hard to find what's in review  
**Frequency:** 2–3 times per week  

---

### 2. **Marketing Manager / Product Lead**

**JTBD:** "I need to manage articles, case studies, testimonials, and hero images to drive traffic and build brand authority. I want to schedule content, track performance, and ensure consistency."

**Top Tasks:**
- Create/edit articles and case studies with rich media
- Schedule publication dates
- Manage SEO metadata (title, description, OG)
- Bulk tag/categorize content
- View what's published vs. drafts
- Monitor inquiries/leads pipeline

**Data Access:** Articles, Cases, Reviews, Media, Leads, Analytics Dashboard  
**Permissions:** Create, Edit, Publish own content; Approve others' (optional)  
**Pain Points (typical):** Slow bulk edits, lost drafts, confusing publish workflow  
**Frequency:** Daily  

---

### 3. **Content Editor / Copy Writer**

**JTBD:** "I write and refine content. I need to save drafts frequently, see what I've changed, and hand off to the manager for review."

**Top Tasks:**
- Create articles in rich editor (markdown/WYSIWYG)
- Auto-save drafts
- See version history / compare changes
- Submit for review
- Receive feedback and revise
- Manage article categories/topics

**Data Access:** Articles, Topics, Media  
**Permissions:** Create, Edit own drafts; Submit for review  
**Pain Points (typical):** Unsaved work lost; no version history; hard to see feedback  
**Frequency:** Daily  

---

### 4. **SEO Specialist**

**JTBD:** "I need to optimize every page URL for search: meta titles, descriptions, canonical tags, hreflang for languages, og tags, and robots directives. I want to detect missing SEO and generate default values fast."

**Top Tasks:**
- Edit SEO for articles, pages, and service URLs
- View SEO preview (Google snippet appearance)
- Bulk generate defaults (title from article title, meta desc from first 160 chars)
- Filter pages missing SEO
- View hreflang configuration per language
- Export SEO metadata
- Set robots, canonical, noindex flags

**Data Access:** All URLs, SEO Center, Articles (linked)  
**Permissions:** Edit SEO for all; No content create/delete  
**Pain Points (typical):** Manual data entry per URL tedious, previews missing, language versions confusing  
**Frequency:** Daily, especially during content pushes  

---

### 5. **HR / People Operations**

**JTBD:** "I manage team member profiles, departments, bios, and links to social media. I want fast bulk edits and a team directory view."

**Top Tasks:**
- Create/edit team member profiles
- Assign to departments/practice areas
- Upload photos, edit bios
- Manage team hierarchy
- Bulk assign practice areas

**Data Access:** Team Members, Practice Areas, Media  
**Permissions:** Create, Edit team members; No publish  
**Pain Points (typical):** Photo uploads slow, bios not versioned, no bulk operations  
**Frequency:** 2–3 times per week  

---

### 6. **Sales / Lead Manager**

**JTBD:** "I need to see and manage all incoming inquiries (leads) from forms, update status, assign to team, and export for CRM."

**Top Tasks:**
- View new inquiries (priority order)
- Update status (New → In Progress → Done)
- Assign to sales rep
- View inquiry source, UTM, device type
- Add internal notes/comments
- Bulk export to CSV
- Filter by date, status, source

**Data Access:** Inquiries/Leads, basic Analytics  
**Permissions:** View, Update status, Add comments; No delete  
**Pain Points (typical):** Hard to filter by source, missing UTM data, no bulk actions  
**Frequency:** Daily  

---

### 7. **System Administrator**

**JTBD:** "I configure the entire system: user accounts, roles, permissions, custom fields, integrations, backup/restore, and monitor system health."

**Top Tasks:**
- Create/manage user accounts and assign roles
- Configure role permissions (granular RBAC)
- Monitor audit logs (who did what)
- Manage API integrations (Zapier, CRM, email)
- View system settings (site name, brand colors, default language)
- Manage webhooks, custom fields
- View error logs / system health

**Data Access:** All (System access)  
**Permissions:** Full access; Critical actions require MFA  
**Pain Points (typical):** No way to see permission matrix at a glance, audit logs buried  
**Frequency:** 2–3 times per week (higher during setup)  

---

### Priority Matrix (JTBD Impact vs. Frequency)

| Role | Create Content | Manage Status | Review | Publish | Bulk Operations | Audit/Admin |
|------|---|---|---|---|---|---|
| **Owner** | — | ✅✅ | ✅✅✅ | ✅✅✅ | — | ✅✅✅ |
| **Marketing** | ✅✅✅ | ✅✅ | — | ✅✅ | ✅✅ | — |
| **Editor** | ✅✅✅ | ✅ | — | — | — | — |
| **SEO** | — | — | — | — | ✅✅✅ | — |
| **HR** | ✅✅ | — | — | — | ✅✅ | — |
| **Sales** | — | ✅✅✅ | — | — | ✅✅ | — |
| **Admin** | — | — | — | — | ✅✅ | ✅✅✅ |

---

## Information Architecture & Navigation

### 1. Main Sections (Left Sidebar Navigation)

```
ADMIN PANEL STRUCTURE
├── 📊 DASHBOARD
│   ├─ Overview (stats, recent activity)
│   └─ Publishing Calendar
│
├── 📝 CONTENT
│   ├─ Articles (+ Topics)
│   ├─ Case Studies
│   ├─ FAQ
│   ├─ Services & Practice Areas
│   └─ Advantages / Features
│
├── 👥 PEOPLE & COMPANY
│   ├─ Team Members (+ departments)
│   ├─ Practice Areas
│   ├─ Contact Block (main contact info)
│   └─ Offices / Locations
│
├── ⭐ SOCIAL PROOF
│   ├─ Reviews / Testimonials
│   └─ Case Studies (alt view)
│
├── 💼 LEADS & CRM
│   ├─ Inquiries / Form Submissions
│   └─ Inquiry Forms (manage form fields)
│
├── 📁 MEDIA & DOCS
│   ├─ Media Library (images, videos, docs)
│   └─ Collections (folders/tags)
│
├── 🌐 LOCALIZATION
│   ├─ Languages (add/manage locales)
│   └─ Translation Status Report
│
├── 🔍 SEO CENTER
│   ├─ SEO by URL (route management)
│   └─ Redirects (301/302)
│
├── 👤 USERS & SECURITY
│   ├─ Team Accounts (create/edit users)
│   ├─ Roles & Permissions (RBAC editor)
│   ├─ Audit Log (change history)
│   ├─ Active Sessions (logout users)
│   └─ MFA Management
│
└── ⚙️ SETTINGS
    ├─ Site Settings (name, tagline, colors)
    ├─ Integrations (APIs, webhooks)
    ├─ Email Templates
    └─ Backup & Export
```

### 2. Navigation Pattern

**Primary Navigation:** Left sidebar (collapsible for smaller screens)
- Always visible at breakpoint ≥1024px
- Slide-out on mobile
- Sections have icons + labels
- Active state highlighted (bold + colored left border)

**Secondary Navigation (Breadcrumbs):**
- Display: Dashboard > Content > Articles > [Article Title]
- Clickable links for navigation
- Useful for deep navigation

**Tertiary (Tabs & Sub-tabs):**
- Articles → "Published" | "Draft" | "Scheduled" | "Archived"
- SEO Center → "Missing SEO" | "By Language" | "Bulk Actions"

**Global Search & Command Palette:**
- Keyboard shortcut: `Cmd/Ctrl + K` opens command palette
- Search across entities: articles, team members, forms
- Quick actions: "Publish Article", "Create User", "View Audit Log"
- Helps power users bypass deep navigation

**Top Bar Elements:**
- Site/Tenant name (left)
- Current user + role (right)
- Notifications bell (in progress)
- Settings / Profile menu (right dropdown)
- Logout link

---

### 3. IA Naming Conventions

**Section Names:**
- Use business terms, not technical jargon
- ✅ "Team Members" not "Users"
- ✅ "Inquiries" not "Leads API"
- ✅ "Localization" not "i18n Config"

**Action Labels:**
- Use verbs + noun: "Create Article", "Publish", "Add Language"
- ✅ "Add Team Member" not "New User"
- ✅ "Send for Review" not "Transition WF State"

---

## Core CRUD UX Patterns

### 1. **List View (Data Table)**

**When to use:** Browsing 10+ items (articles, team members, leads)

**Key Components:**

#### A. Table Header
```
[Select All ☑️] | Title | Author | Status | Published | Actions ↑↓
```

- **Column Headers:** Clickable for sorting; show ▲▼ indicator
- **Select All Checkbox:** For bulk operations
- **Sticky Header:** Remains visible while scrolling down
- **Column Customization:** "Show/Hide Columns" menu (save preference to localStorage)
- **Sort Direction:** Clear visual indicator (▲ = ascending, ▼ = descending)

**Recommended Columns (per entity):**
- **Articles:** Title (link), Author, Status (badge), Published date, Actions
- **Team Members:** Name (avatar + link), Department, Role, Email, Actions
- **Inquiries:** Name, Email, Date, Source, Status, Actions
- **SEO URLs:** Path, Page Title, SEO Completion %, Modified, Actions

#### B. Table Body
- **Row Height:** 44px (fits touch targets for mobile)
- **Row Hover State:** Light background (var(--color-secondary-hover)) on desktop
- **Alternating Row Colors:** Optional, improves readability for wide tables
- **Avatar/Images:** 32px thumbnails for people/media
- **Status Badge:** Color-coded (Published = green, Draft = gray, Scheduled = blue, Archived = muted)
- **Text Truncation:** Use ellipsis with tooltip on hover for long text
- **Right-Align Numbers:** Dates, counts, percentages

#### C. Bulk Operations (Row Selection)
- **Multi-select:** Checkbox per row; Shift+Click selects range
- **Select All:** Checkbox in header
- **Selection Feedback:** 
  - Row highlight (background color change)
  - Counter: "5 selected" near filter section
  - Sticky action bar at bottom of viewport (fixed position)
  
**Bulk Actions Toolbar (appears when rows selected):**
```
[5 selected] | [Publish] [Unpublish] [Archive] [Delete] [More ▼]
```
- **Batch Actions:** Publish, Unpublish, Archive, Delete, Assign Tag, Assign Owner
- **Confirmation:** Show dialog before destructive operations
- **Async Feedback:** Toast notification when batch operation completes
- **Error Handling:** If some rows fail, show list of which ones and why

#### D. Pagination & Row Density
- **Default Row Count:** 25 rows per page (balance density vs. scroll load)
- **Options:** 10, 25, 50, 100 rows per page
- **Pagination Style:** Page-based (not infinite scroll)
  - Show "Page 1 of 5" + Previous/Next buttons
  - Allow jumping to page (text input)
  - Show total count: "42 total articles"
- **Density Control:** Toggle icon in table toolbar
  - Compact (32px rows)
  - Normal (44px rows, default)
  - Spacious (56px rows)

#### E. Filtering & Search
**Search Bar (above table):**
- Single text input: "Search by title, author, email..."
- Debounce input to 300ms before API call
- Show result count: "25 of 42 articles"
- Clear button (X icon)
- Keyboard focus on load (Cmd/Ctrl+K lands here after palette)

**Quick Filters (Chips):**
- Pre-defined filters for common scenarios
- Examples:
  - Articles: [My Drafts] [Published] [Needs Review] [This Week]
  - Inquiries: [New] [In Progress] [Closed] [High Priority]
- Visual feedback: Active filter chip has filled background
- Removable: X icon on chip
- Saved filters: "Save current filter as..." option

**Advanced Filters (Expandable Panel):**
```
Status: [Draft ☐ Published ☐ Archived ☐] [Apply]
Author: [Dropdown]
Date Range: [From] [To]
Priority: [High ☐ Medium ☐ Low ☐]
[Clear All] [Save as...]
```
- Nested accordion for complex filters
- Operator choices: is / is not / contains / date range
- Save filter preset for reuse
- Indicator badge on filter icon if filter active

#### F. Empty State
- When no results:
  - Icon + message: "No articles yet"
  - CTA button: "[Create your first article]"
  - If filtered: "No results match. [Clear filters]"
  - Illustration optional (keeps mood positive)

#### G. Error State
- If data load fails:
  - Error icon + message
  - "Failed to load articles. [Retry]"
  - Log error to console (don't expose backend details)

#### H. Loading State
- Skeleton loaders for table rows (match row height)
- Show 5–10 placeholder rows while loading
- Animated pulse effect on skeletons
- Disable interactions during load

---

### 2. **Create / Edit Form View**

**When to use:** Creating new item or editing existing item (click row to edit)

**Navigation:**
- Link from list: Click row title → opens detail/edit view (or modal on mobile)
- URL: `/admin/articles/new` or `/admin/articles/{id}/edit`
- Breadcrumbs: Content > Articles > [Title] or Content > Articles > New Article

**Form Layout:**

#### A. Form Sections (Accordions)
Group logically related fields:

**Article Form Example:**
```
▶ Basic Information (expanded by default)
  - Title (required, text input, max 255)
  - Slug (auto-generated from title, editable, uniqueness check)
  - Category / Topic (dropdown or multi-select)
  - Featured (toggle/checkbox)

▶ Content
  - Body (rich text editor, WYSIWYG/Markdown)
  - Featured Image (media picker or upload)
  - Alt Text (required if image, accessibility)

▶ Publishing
  - Status (radio or dropdown: Draft / Scheduled / Published / Archived)
  - Publish Date (date + time picker, if Scheduled)
  - Author (auto-filled, read-only or reassign)

▶ SEO (collapsible, often starts collapsed)
  - Meta Title (text, 60 char limit with counter)
  - Meta Description (textarea, 160 char limit with counter)
  - Focus Keyword (text, for guidance only)

▶ Localization (if multi-language)
  - [EN] [FR] [DE] tabs
  - Shows which languages are complete/incomplete
  - Missing language indicator (⚠️ icon)

▶ Advanced (collapsed)
  - Revision History (link to version timeline)
  - Custom Fields (if enabled)
  - Webhooks / Integrations
```

#### B. Form Validation & Error Handling

**Client-Side Validation (Real-time):**
- Show inline errors below field immediately
- Error message: Clear, specific, actionable
  - ✅ "Title is required"
  - ✅ "Slug must be unique (already used in: 'Old Article')"
  - ❌ "Invalid input"
  - ❌ "Error 400"

**Field-Level Errors (Display):**
```
Title [________] ❌ Required field
        ^ red border, error icon
      ✓ Error message in red text below
```

- Red border around field
- Error icon (⚠️ or ⊘)
- Error text in red, accessible color contrast (4.5:1)
- `aria-invalid="true"` and `aria-describedby="title-error"`

**Required Field Indicator:**
- Asterisk (*) or label text: "Title *"
- Avoid using color alone (WCAG requirement)

**Async Validation (Server-Side):**
- Slug uniqueness check: Request API `/validate/slug?slug=my-article&type=article`
- Debounce to 500ms to avoid excessive API calls
- Show loading spinner if validating
- Display result: ✅ "Available" or ❌ "Already used"

**Form Submission Errors:**
- Top-of-form alert (error summary):
  ```
  ⊘ Please fix 2 errors before submitting
  • Title is required
  • Slug must be unique
  ```
- Clicking error links scrolls to field and focuses input
- `role="alert"` for screen readers

---

#### C. Auto-Save & Draft Management

**Auto-Save Drafts:**
- Every 5–10 seconds, save form state as draft
- Show status indicator: "Saving..." → "Saved at 2:45 PM"
- Visual feedback: Subtle icon or text, not intrusive
- Only save if content changed (avoid unnecessary API calls)
- Disable auto-save for read-only views

**Unsaved Changes Warning:**
- If user tries to leave with unsaved changes: Confirm dialog
  ```
  "You have unsaved changes. Leave anyway? [Cancel] [Leave]"
  ```
- Only show if meaningful changes (not just cursor moved)

**Draft History:**
- "Revision History" button in form footer
- Shows timeline of saves with timestamps
- Compare versions side-by-side (optional for v2)
- Restore to previous version

---

#### D. Rich Text Editor (for Body Content)

**Type:** WYSIWYG (TipTap, Slate, or similar)

**Toolbar Features:**
```
[B] [I] [U] [❌] | [H1] [H2] [H3] | [•] [1.] [>] | [Link 🔗] [Image 🖼️] [Code] [Quote]
```

- **Text Formatting:** Bold, Italic, Underline, Strikethrough
- **Headings:** H1, H2, H3 dropdowns
- **Lists:** Bullet list, Numbered list, Blockquote
- **Links:** Insert/edit link, open in new tab checkbox
- **Media:** Insert image, video (YouTube embed)
- **Code Block:** Syntax highlighting, language selector
- **Table:** Insert table, edit cols/rows
- **Undo/Redo:** Keyboard: Cmd+Z / Cmd+Shift+Z

**Media Picker Modal (on Image icon click):**
- Tab 1: Upload new (drag & drop, file input)
  - Max 10MB per image
  - Accepted: JPG, PNG, WebP, GIF
  - Auto-resize to max 2560px width
  - Show upload progress
  - Alt text input (required)
- Tab 2: From Media Library (search + filter by tag)
- Tab 3: Recent uploads (quick access)
- Preview: Show selected image with size
- Insert with alt text

**Inline Formatting Tips:**
- Show help text: "Cmd+B for bold, Cmd+I for italic, Cmd+K for link"
- Keyboard shortcuts must work
- Mouse toolbar for discovery

**Word Count & Length Limits:**
- Display live word count
- Optional: Recommend 400–1200 words for articles
- Warn if exceeding character limit (rare)

---

#### E. Media & File Pickers

**Single File Input (Featured Image):**
```
[Select Image] [Browse...]
    ↓
    Thumbnail of selected image or placeholder
    [Remove] [Replace]
    Alt Text: [____________________]
```

- Click to open media picker
- Show thumbnail of current image
- Remove and Replace buttons
- Alt text field (required for accessibility)

**Multiple File Input (Gallery):**
```
[+ Add Images]
  ☑️ img1.jpg (remove)
  ☑️ img2.png (remove)
  ☑️ img3.webp (remove)
  [Reorder via drag]
```

- Drag to reorder
- Bulk remove selected images
- Alt text per image

---

#### F. Form Footer & Save Actions

```
[Save Draft] [Preview] [Publish] [Schedule]
       ↓
     If saving, show: "Saving..." → checkmark icon + "Saved"
     If error: Red text "Failed to save"
```

**Button States:**
- **Save Draft:** Always available (grey)
  - Updates status to "Draft"
  - Doesn't require all fields
  - Success toast: "Article saved as draft"

- **Preview:** Opens preview of public page (new tab)
  - Shows how article appears on website
  - Language-aware (shows selected locale)
  - Read-only view

- **Publish:** Requires valid Title + Body + Status: "Published"
  - Enables if form validates
  - Click → confirmation dialog (if not yet published)
    ```
    "Publish 'Article Title'? This will be live immediately.
    [Cancel] [Publish]"
    ```
  - Success: Navigate to list view, toast notification

- **Schedule (optional v2):** Set publish date in future
  - Opens date/time picker
  - Validation: Date must be in future
  - Status changes to "Scheduled"
  - Notification sent on scheduled time

**Disabled States:**
- Buttons disabled if form has errors (red-bordered fields visible)
- Show tooltip on hover: "Fix errors before publishing"

---

### 3. **Detail / Read-Only View**

**When to use:** Viewing published/archived items (no edit mode)

**Layout:**
- Same sections as edit form, but all fields read-only
- Remove buttons: [Save Draft], [Publish]
- Add buttons: [Edit] (opens edit form), [Archive/Restore], [View on Site]
- Show: Published date, author, last edited by, view count (if tracked)

---

### 4. **Mobile Responsive Patterns**

**Breakpoints:**
- Mobile: < 768px (phones)
- Tablet: 768px – 1024px
- Desktop: ≥ 1024px

**Table on Mobile:**
- Option A: Horizontal scroll (left/right)
  - Freeze first column (checkbox + title)
  - Show scroll hint: "← Scroll for more"
- Option B: Card layout
  - Each row becomes a card
  - Swipe to reveal actions
  - Less data density, but scannable

**Form on Mobile:**
- Stack vertically (already responsive with flexbox)
- Single-column layout
- Sticky footer with Save button
- Accordions collapse by default (save space)

**List on Mobile:**
- Hide less critical columns (Author, Last Modified)
- Show: Title, Status, Quick Actions (menu icon)
- Pagination: Show "Page 1 of 5" with Next/Prev buttons
- Search bar as sticky top element

---

## Forms & Content Editors

### 1. **Article Form Workflow**

**Scenario:** Marketing Manager creates a blog article

**Step 1: Form Opens (New Article)**
- Auto-focus on Title field
- All fields empty except:
  - Author: Auto-filled with current user
  - Status: Default "Draft"
- Accordion sections: "Basic Information" open, rest collapsed

**Step 2: Fill Basic Fields**
- Title: "How to Optimize Your Website for SEO"
- Slug: Auto-generated to "how-to-optimize-your-website-for-seo"
- Topic: Select from dropdown [Technical SEO, Content Marketing, Tools, ...]
- User can edit slug manually
- Real-time validation: Slug must be unique

**Step 3: Write Content**
- Expand "Content" accordion
- Click in Body field, WYSIWYG editor loads
- Start typing or paste from Google Docs (strips formatting, user confirms)
- Insert featured image: Click [Image 🖼️] → media picker → select or upload → choose alt text
- Auto-save kicks in every 10 seconds: "Saved at 2:46 PM"

**Step 4: SEO Metadata**
- Expand "SEO" accordion (usually collapsed)
- System suggests:
  - Meta Title: "[Article Title] | Company Name" (autofill, editable)
  - Meta Description: First 160 chars of body (editable)
- Editor refines:
  - Meta Title: "How to Optimize Your Website for SEO in 2026"
  - Meta Description: "Proven SEO optimization techniques to improve your website ranking..."
- Character counters show: "62/60" (red if over limit)

**Step 5: Publish & Schedule**
- Expand "Publishing" accordion
- Status: Choose from dropdown
  - Draft (keep private)
  - Scheduled (pick future date/time)
  - Published (go live immediately)
- If Scheduled: Date/Time picker appears
- Click [Publish] button → Confirmation dialog → "Publishing..."
- Success: Navigate to list view, green toast: "Article published!"

**Step 6: View on Site**
- Button [View on Site] opens new tab showing live article

---

### 2. **Localization Workflow Within Forms**

**Scenario:** Article needs translation to French and German

**Form With Language Tabs:**
```
Article Edit: "How to Optimize Your Website"

Tabs: [EN ✅] [FR ⚠️] [DE ⚠️]
       ^EN selected
```

**EN Tab (English - default):**
- All fields filled and published
- Edit capability enabled
- Show: "Published" status

**FR Tab (French - incomplete):**
- ⚠️ icon indicates "Missing Translation"
- Fields show:
  - Title: [EN fallback: "How to Optimize..."] (grayed out, read-only)
  - Title (FR): [Empty input]
  - Body: [EN fallback text] (grayed out)
  - Body (FR): [Empty textarea]
- CTA: "[Translate Now]" → opens translation tool (v2: AI suggestion)
- Status: "Not Translated"

**DE Tab (German - similar to FR):**
- Same pattern
- Status: "Not Translated"

**Tab Behavior:**
- Save each language independently
- Validate required fields per language
- Translation status report: "EN: 100% | FR: 30% | DE: 0%"
- Prevent deleting language if content exists and is published

**Translation Status Dashboard (v2):**
- Table of all articles
- Columns: Title | EN | FR | DE | Completion %
- Filter: "Only incomplete translations"
- Bulk action: "Mark completed" or "Send to translator"

---

### 3. **Form Validation Checklist**

**Client-Side (Immediate Feedback):**
- ✅ Required field check (real-time)
- ✅ Slug format validation (alphanumeric + hyphen)
- ✅ Meta title/description character limits
- ✅ Email format (if applicable)
- ✅ URL format for links
- ✅ Image alt text required if image present

**Server-Side (On Submit):**
- ✅ Slug uniqueness
- ✅ File size limits (images, documents)
- ✅ Permission check (user can edit this entity)
- ✅ Business logic (e.g., can't publish without category)
- ✅ Rate limits (prevent spam)

**Error Messages (WCAG Compliant):**
```
Bad: "Invalid value"
Good: "Title must be between 3 and 255 characters. Currently: 2 characters."

Bad: "Error 422"
Good: "Slug 'my-article' is already used by another article. Choose a different slug."

Bad: "Image too big"
Good: "Image size is 15MB. Max allowed: 10MB. Please resize and try again."
```

**Required Field Indicators:**
- Label text: "Title *" (asterisk in label, not color-only)
- Aria: `aria-required="true"` on input element
- Tab title: Show summary "1 required field missing"

---

## Publishing & Content Workflow

### 1. **Content Workflow States**

**State Machine:**
```
Draft → (Review) → Published → (Archive)
  ↑                              ↓
  └──────────────────────────────┘
```

**States & Transitions:**

| State | Who Can Edit | Can Publish | Can Review | Can Archive | Visibility |
|-------|---|---|---|---|---|
| **Draft** | Creator, Editor, Owner | Only if role allows | ✅ Send to review | ✅ Archive to remove | 🔒 Private |
| **In Review** (optional) | Creator + Reviewer | No (wait for approval) | ✅ Approve/Reject | ❌ | 🔒 Private |
| **Published** | Only via edit then re-publish | ✅ Unpublish | — | ✅ Archive | 🌐 Public |
| **Scheduled** | Creator | ✅ Publish now | ✅ Can cancel | ✅ Archive | 🔒 Private (until time) |
| **Archived** | — (read-only) | ❌ | — | ✅ Restore | 🔒 Private (hidden) |

**State Transition UI:**

**Draft Article:**
```
[Save Draft] [Preview] [Submit for Review] [Schedule] [Publish]
                          ↓
                    Sends notification to reviewers
                    Article locked from further edits (option)
                    Status → "In Review"
```

**In Review:**
```
[Save Draft] [Preview] [Approve] [Request Changes]
                          ↓
                    If Approve: Status → "Published"
                    If Request: Sends feedback to creator
                    Status → "Draft" (back for revision)
```

**Published:**
```
[Edit] [Preview] [Schedule Update] [Unpublish] [Archive]
                                      ↓
                    Creates new draft of current article
                    Original stays live
                    Updates can be scheduled for later
```

**Archived:**
```
[View] [Restore] [Permanently Delete] (with confirmation)
         ↓
      Status → "Draft"
      Can be published again
```

---

### 2. **Approval & Review Workflow**

**For Organizations Requiring Review:**

**Config (Admin Settings):**
```
Content Moderation: [Enabled] [Disabled]
Require Review For:
  ☑️ Articles
  ☑️ Case Studies
  ☐ FAQ
  ☐ Team Members
Review Roles:
  ☑️ Editors (can review other's content)
  ☑️ Content Manager (can approve)
  ☑️ Owner (final approval for sensitive content)
```

**Creator's View (In Review State):**
- Status badge: "In Review" (blue/yellow)
- Message: "Waiting for approval from [John Editor] since 2 hours ago"
- Can see reviewer comments below each field
- Edit and resubmit button: "[Make Changes]" → resubmits

**Reviewer's View (Notification + Dashboard):**
- Email notification: "Article 'How to SEO' needs your review" + link
- Dashboard "Review Queue" card: Shows pending count
- Reviewer opens article, sees all content + "Review Panel" on right:
  ```
  REVIEW
  ─────────
  Submitter: Alice (Content Writer)
  Submitted: 2 hours ago
  Deadline: Jan 16 (if SLA configured)
  
  [Approve] [Request Changes]
  
  Add Comment:
  [Comment textarea...] [Send]
  
  ─────────
  Reviewer: Bob
  Decision: Pending
  ```

**Approve Flow:**
- Click [Approve] → Confirmation: "Publish article?" → Published
- Notification sent to creator: "Your article 'How to SEO' was approved"

**Request Changes Flow:**
- Click [Request Changes]
- Comment field: "Please add more examples in the SEO section"
- Status → Back to "Draft"
- Notification to creator: "Changes requested for your article"
- Creator can view comments, make changes, resubmit

---

### 3. **Publishing Calendar & Scheduling**

**Calendar View (Optional but Recommended):**
```
PUBLISHING CALENDAR
January 2026

Sun  Mon  Tue  Wed  Thu  Fri  Sat
                    13   14   15
           [2 scheduled]
           • How to SEO (Jan 15 2PM)
           • Case Study: Client X (Jan 15 6PM)
     16   17   18   19   20   21   22
```

- Click day to see scheduled content
- Drag article card to reschedule
- Show all statuses: Draft (gray), Scheduled (blue), Published (green)
- Time zone shown: "All times in EST"

**Scheduling Form:**
```
Publish On: [Date Picker] [Time Picker]
Example: Friday, January 15, 2026 at 2:00 PM EST
[⚠️ Scheduling will publish automatically]
```

- Date picker (calendar UI)
- Time picker (24-hour or 12-hour + AM/PM)
- Timezone aware (stored as UTC, shown in user's timezone)
- Validation: Date must be in future

---

### 4. **Version History & Diff (Optional for MVP, Add v1.5)**

**Version History Modal:**
```
REVISION HISTORY: "How to Optimize Your Website"

Version | Author | Date | Action | Preview
────────────────────────────────────────────────
v3      | Bob    | Jan 14, 2:15 PM | Published | [View]
v2      | Alice  | Jan 14, 1:30 PM | Submitted | [View] [Compare]
v1      | Alice  | Jan 14, 1:00 PM | Created   | [View] [Compare]

[Restore to v2]  [Download JSON]
```

- Click [Compare] to see diff between versions
- Click [Restore] to revert to older version (creates new version, doesn't delete)
- Shows: Who changed it, when, what action (created/edited/published)

**Diff View (v2):**
- Side-by-side: v1 vs. v2
- Highlight changed text (red = removed, green = added)
- Field-level diffs (Title, Body, Meta Description)

---

## Localization Management

### 1. **Language Configuration**

**Admin Setting: Manage Languages**
```
ACTIVE LANGUAGES
Language | Code | Default | Status | Action
─────────────────────────────────────────────
English  | en   | ☑️      | Active | [Edit] [Set as Default]
French   | fr   | ☐       | Active | [Edit] [Deactivate]
German   | de   | ☐       | Active | [Edit] [Deactivate]

[+ Add Language]
```

**Add Language Modal:**
```
Language: [Dropdown: English, French, German, Spanish, ...]
Language Code: [Auto-filled: en, fr, de, es]
Native Name: [Auto-filled, editable]
Default Language: ☑️ (only one allowed)
Fallback Language: [Dropdown] (if translation missing, show this)
Status: ☑️ Active
RTL: ☐ (right-to-left for Arabic, Hebrew)

[Cancel] [Add]
```

**Edit Language:**
- Same fields as Add, can modify except Code (frozen)
- Deactivate warning: "If you deactivate French, published French content will not be accessible"
- Cannot delete language if published content exists
- Option: "Migrate content to fallback language before deactivating"

---

### 2. **Translation Status Reporting**

**Dashboard View: Translation Completeness**
```
LOCALIZATION STATUS

Overall Completion:
┌─────────────────────────────┐
│ English: 100% ████████████ │
│ French:   65% ████████     │
│ German:   30% ████         │
└─────────────────────────────┘

By Content Type:
                    EN    FR    DE
Articles            20/20 12/20 ⚠️ 5/20
Team Members        10/10 10/10 ✅ 10/10
FAQ                 5/5   3/5   ⚠️ 0/5

[Generate Missing Translations Report]
[Bulk Update Status]
```

**Missing Translations Report:**
```
ENTITIES NEEDING TRANSLATION (Filtered: FR)

Type | Title | Last Modified | Status
─────────────────────────────────────────
Article | SEO Guide | 3 days ago | No French version
Article | Case Study | Today | Partial (title only)
FAQ | How to contact? | 1 week ago | Missing
Team | John Doe | 2 weeks ago | No French bio

[Select All] [Export as CSV] [Send to Translator]
```

- Filter by language, content type, date range
- Export button: CSV or JSON format
- Integration (v2): Send to translation service (Crowdin, Lokalise)

---

### 3. **Language Tabs in Forms**

**Article Form with Localization:**
```
[EN ✅] [FR ⚠️ Incomplete] [DE 🔴 Not Started]

EN Tab (English - Default):
Title: "How to Optimize Your Website"
Body: [Rich text content...]
Status: Published

FR Tab (French):
Title (FR): [empty or partial]
   ⚠️ Missing French translation
   Fallback (EN): "How to Optimize Your Website"
   [Auto-Translate (v2)] [Manual]

DE Tab (German):
Title (DE): [empty]
   🔴 Not Translated
   Fallback (EN): "How to Optimize Your Website"
   [Auto-Translate (v2)] [Manual]

Indicators:
✅ Complete (all required fields filled)
⚠️ Incomplete (some fields missing)
🔴 Not Started (no content entered)
```

**Tab Behavior:**
- Switching tabs auto-saves previous language
- Validation errors shown per language
- Character limits and placeholders shown for each language

---

### 4. **Fallback & Language Selector**

**Frontend Language Selector (Not Admin, but Relevant):**
- Public site shows: "English | Français | Deutsch"
- If user selects French but article is not translated:
  - Option A: Show fallback (English) with banner: "This page not yet translated to French"
  - Option B: Hide content (don't show incomplete translations)
  - Configured in Settings

**Admin's Control:**
```
If Translation Missing:
☑️ Show fallback language (EN)
☐ Hide content entirely
Default Fallback Language: [English]
```

---

### 5. **Localization Workflow Best Practices**

**For Non-Technical Teams:**
1. Create content in primary language (English)
2. Publish English version
3. Mark for translation: Click [Mark for Translation] → Select languages
4. System sends CSV export to translator
5. Translator returns completed CSV
6. Admin imports: [Import Translations] → select file → preview → confirm
7. Translated content appears in language tabs

**Optional: Automation (v2)**
- Use translation API (OpenAI, DeepL, Google Translate) for auto-translation
- Mark as "Machine Translated - Review Required"
- Humans review and edit

---

## SEO Center

### 1. **SEO by URL Management**

**Purpose:** Manage meta tags, canonical, robots, hreflang per route/URL

**List View: All URLs**
```
ROUTES & SEO METADATA

Route | Page Type | Meta Title | Meta Desc | Robots | SEO % | Actions
──────────────────────────────────────────────────────────────────────────
/     | Home     | Company... | Founded  | index  | 100%  | [Edit]
/about| About    | (empty)    | (empty)  | index  | 0%    | [Edit] ⚠️
/blog | Blog List| Blog Post  | Latest   | index  | 50%   | [Edit]
/articles/seo-guide | Article | How to... | Proven SEO | index | 90% | [Edit]
/contact | Contact | Contact U | Get in t | noindex| 40%   | [Edit]
```

**Filters & Search:**
- Search by route path
- Filter by page type (Homepage, Article, Service, Team, etc.)
- Filter by completion: "Only missing SEO", "Only incomplete"
- Filter by robots: "index", "noindex", "nofollow"
- Language filter: "EN", "FR", "DE"

**SEO Completion Indicator:**
- % based on: Meta Title filled (30%), Meta Description (30%), OG Image (20%), Canonical (10%), Robots (10%)
- Color coding:
  - ✅ 100%: Green
  - ⚠️ 50–99%: Yellow
  - 🔴 < 50%: Red

---

### 2. **SEO Editor for a Single URL**

**Route Details Edit Form:**
```
URL: /articles/how-to-optimize-website

Basic
─────────
Meta Title (60 chars):
[How to Optimize Your Website for SEO in 2026]
Status: ✅ 62/60 (warn if >60)

Meta Description (160 chars):
[Proven SEO optimization techniques to improve your website ranking...]
Status: ✅ 145/160

Preview Snippet (as appears in Google):
┌─────────────────────────────────────┐
│ How to Optimize Your Website for... │
│ yoursite.com > blog > seo-guide    │
│ Proven SEO optimization techniques  │
│ to improve your website ranking...  │
└─────────────────────────────────────┘

Advanced
──────────
Canonical URL:
[https://yoursite.com/articles/how-to-optimize-website]
Self-referential (correct) ✅ or points to another URL

Robots Meta Tag:
[index, follow ▼] (options: index/noindex, follow/nofollow)

OG Image (Open Graph for Social):
[Image preview or upload] 
Recommended: 1200x630px

OG Title: [auto-filled from Meta Title, editable]

OG Description: [auto-filled from Meta Description, editable]

Hreflang (for Multi-Language):
If multilingual site:
┌────────────────┐
│ Lang | URL      │
├────────────────┤
│ en   | .../en  │
│ fr   | .../fr  │
│ de   | .../de  │
│ x-default | /  │
└────────────────┘
[+ Add Language Variant]

Sitemap:
☑️ Include in sitemap
Priority: [0.8 ▼] (0.0-1.0)
Change Frequency: [weekly ▼]

Custom Fields (if enabled):
JSON-LD (schema.org):
[textarea with JSON structure for rich snippets]

[Save] [Reset] [Preview URL]
```

**Preview URL Button:**
- Opens new tab showing live page
- Helps verify meta tags are applied correctly
- Right-click → "View Page Source" → Ctrl+F "meta" to find tags

---

### 3. **Bulk SEO Operations**

**Bulk Edit Form:**
```
BULK SEO UPDATE

Select Templates:
☑️ Auto-generate Meta Title from Article Title
☑️ Auto-generate Meta Description from first 160 chars of body
☑️ Set Robots to: [index, follow ▼]
☑️ Set Canonical to: [self-referential ▼]
☑️ Set OG Image to: [Featured Image]

Apply To:
Articles from category: [Select Topic]
Published only: ☑️
Language: [English ▼]

[Preview Changes] [Apply]
```

**Preview Changes:**
- Table showing before/after for each URL
- Confirm before applying
- Undo available if mistakes

**Export SEO:**
```
[Export All Routes as CSV] 
Columns: Route | Meta Title | Meta Desc | Canonical | Robots | OG Title | OG Desc
Format: CSV (Excel-friendly)
```

---

### 4. **Robots & Canonical Rules**

**Guidelines (Help Text in Form):**

**Meta Robots:**
- `index, follow` (default): Page is indexable and links are followed
- `noindex, follow`: Don't index this page but follow links (use for duplicates, drafts)
- `noindex, nofollow`: Completely hidden from search (use for login, admin, etc.)

**Canonical Tag:**
- Use self-referential (`<link rel="canonical" href="https://yoursite.com/page/">`) for all pages
- Use cross-domain canonical only for true duplicates (e.g., republished article from another source)
- Must be absolute URL (not relative path)

**Hreflang Best Practices:**
```
English (en):   https://yoursite.com/articles/seo-guide
French (fr):    https://yoursite.com/fr/articles/seo-guide
German (de):    https://yoursite.com/de/articles/seo-guide
Default (x-default): https://yoursite.com/

Each page should have SELF-REFERENTIAL canonical:
- English page: <link rel="canonical" href=".../articles/seo-guide">
- French page: <link rel="canonical" href=".../fr/articles/seo-guide">
```

---

### 5. **JSON-LD (Structured Data)**

**Auto-Generated Schemas (Insert Button):**
```
[+ Insert Schema] → Dropdown:
  • Article (blog post schema)
  • BreadcrumbList (for breadcrumbs)
  • Organization (company info)
  • LocalBusiness (office locations)
  • FAQ (FAQ schema)
  • Product (if e-commerce)
```

**Example: Article Schema (Auto-Populated):**
```json
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "How to Optimize Your Website for SEO",
  "description": "Proven SEO optimization techniques...",
  "image": "https://yoursite.com/images/seo-guide.jpg",
  "author": {
    "@type": "Person",
    "name": "Alice Writer"
  },
  "datePublished": "2026-01-14",
  "dateModified": "2026-01-14"
}
```

- User can edit JSON in text area
- Validation: Warn if invalid JSON
- Preview: Show how schema appears in search results (Google Rich Snippet preview)

---

## Media Library

### 1. **Media Upload & Management**

**Media Library List View:**
```
MEDIA LIBRARY

[+ Upload] [Import from URL] | Search: [____] | Filter: [Type ▼] [Size ▼] [Date ▼]

Grid View (default):
┌──────┐  ┌──────┐  ┌──────┐
│ img1 │  │ img2 │  │ pdf  │
│ .jpg │  │ .png │  │ .pdf │
│ 2.3M │  │ 1.5M │  │ 450K │
└──────┘  └──────┘  └──────┘

[Show as List] [Density: Normal ▼]
```

**Upload Modal:**
```
UPLOAD FILES

Drag & drop files here or [Select Files]

Accepted: JPG, PNG, WebP, GIF, PDF, DOC, DOCX, MP4
Max: 50MB per file, 5 files at once

Progress:
image1.jpg ████████░░ 80% Uploading
image2.jpg ███████░░░ 70% Uploading
[Cancel All]

Results (after upload):
✅ image1.jpg 2.3MB
✅ image2.jpg 1.8MB
[Close]
```

**File Details Panel (Right Sidebar):**
```
SELECT: image1.jpg (open file details)

File Info:
─────────
Name: image1.jpg
Type: Image/JPEG
Size: 2.3MB
Dimensions: 1920 x 1080
Uploaded: Jan 14, 2:30 PM by Alice
URL: https://cdn.yoursite.com/img1.jpg

Metadata:
─────────
Title: [Sunset Landscape] (optional, for organization)
Alt Text: [Beautiful sunset over mountains] (for images, accessibility)
Tags: [+ Add Tags] (help organize: "hero", "blog", "social", "press")

Collections/Folders:
[Blog] [Homepage] [Social Media] [✕] [+ Add]

Usage:
─────────
In Use: 3 places
• Article: "How to Sunset Photo" (link)
• Home Banner (link)
• Facebook Post Draft (link)
[View All]

Actions:
─────────
[Replace File] [Download] [Copy URL] [Duplicate] [Delete]

[Replace File] Modal:
Upload new version, keep same filename & URL
Old file kept in version history (restore if needed)
```

---

### 2. **Collections & Organization**

**Folder Structure:**
```
Collections:
├── Blog (12 files)
├── Homepage (8 files)
├── Team (25 files)
├── Press Kit (6 files)
└── Social Media (34 files)
```

**Create Collection:**
```
[+ New Collection]
Name: [Social Media]
Description: Images for social media posts (optional)
Sharing: Public / Private
[Create]
```

**Batch Operations (Multi-Select):**
```
[✓] image1.jpg [✓] image2.jpg [✓] image3.jpg  | [3 selected]

Bulk Actions:
[Add to Collection] [Add Tag] [Delete] [Download as ZIP] [Change Permissions]
```

---

### 3. **Media in Content**

**Insert Media in Article (Rich Editor):**
```
Click [Image 🖼️] in toolbar
→ Opens Media Picker Modal

Tabs:
1. Recent (12 recently used)
2. Search (global search by name, tag)
3. Upload (upload new file)

Preview:
┌─────────────────┐
│  Selected Image │
│  1920x1080      │
│  2.3MB          │
└─────────────────┘

Alt Text: [Beautiful sunset landscape] (required, a11y)

Sizing:
Width: [auto ▼] (options: auto, small, medium, large, full-width)
[Insert]
```

**Media Reuse Protection:**
- If user tries to delete media that's in use: Confirmation
  ```
  "This image is used in 3 articles. Delete anyway? [Cancel] [Delete]"
  ```
- Link shows where it's used (click to navigate to article)

---

### 4. **File Permissions & Versions**

**File Versions (On Replace):**
```
image1.jpg - Versions

Current (Jan 14, 2:30 PM by Alice)
└ v2.jpg [Download] [Restore] [Delete]

Previous (Jan 12, 1:15 PM by Bob)
└ v1.jpg [Download] [Restore] [Delete]
```

**Permissions (Advanced):**
- Public (viewable by anyone with link)
- Restricted (only logged-in users)
- Private (only file owner and admins)
- Custom (assign per user/role)

---

## Leads & Inquiries Management

### 1. **Inquiries List**

**View: Incoming Form Submissions**
```
INQUIRIES / FORM SUBMISSIONS

[Add Filter] | Search: [____] | View: [List ▼] [Board ▼]

Filters:
☑️ Status: [All ▼] (options: New, In Progress, Done, Spam)
☑️ Source: [All ▼] (options: Contact Form, Demo Request, Newsletter, etc.)
☑️ Date: [Last 7 Days ▼]
☑️ Priority: [All ▼] (if priority field exists)
☑️ Assigned To: [All ▼]

[List View]
┌─────────────────────────────────────────────────────────────┐
│ ☑ Name | Email | Submitted | Source | Status | Assigned | … │
├─────────────────────────────────────────────────────────────┤
│ ☑ John D. | john@.. | Jan 14, 2PM | Contact Form | New | [unassigned] │
│ ☑ Sarah M | sarah@.. | Jan 13, 10AM | Demo Request | In Progress | Bob │
│ ☑ Team A | team@.. | Jan 13, 5PM | Newsletter | Done | Alice │
└─────────────────────────────────────────────────────────────┘

[Kanban View]
  New (5)          In Progress (2)     Done (12)
  ┌──────────┐     ┌──────────┐        ┌──────────┐
  │ John D.  │     │ Sarah M  │        │ Team A   │
  │ john@... │     │ sarah.. │        │ team@... │
  │ Contact  │     │ Demo    │        │ Contact  │
  └──────────┘     └──────────┘        └──────────┘
  [Drag to move]
```

**Row Actions (Inline):**
- Click row to open detail/reply view
- Quick actions dropdown: [View] [Assign] [Mark Done] [Delete] [Spam]

---

### 2. **Inquiry Detail & Reply**

**Inquiry Card View:**
```
FROM: John Doe <john@example.com>
PHONE: +1-555-123-4567
SUBMITTED: January 14, 2026 at 2:15 PM EST
SOURCE: Contact Form (from homepage)
FORM TYPE: "General Inquiry"

MESSAGE:
─────────
"Hi, I'm interested in learning about your SEO services. 
Can we schedule a consultation? Our website is example.com and we're targeting 
500+ keywords across multiple languages."

CONTEXT:
─────────
IP Address: 192.168.1.1
Device: Desktop / Chrome / macOS
Referrer: google.com
UTM: utm_source=google | utm_medium=cpc | utm_campaign=seo_jan_2026
Landing Page: /services/seo

STATUS & ASSIGNMENT:
─────────────────────
Status: [New ▼] (options: New, In Progress, Done, Spam)
Assigned To: [Bob ▼] (assign to team member)
Priority: [Normal ▼] (Low, Normal, High)
Tags: [+ Sales Lead] [+ High Value] [+ UK Market]

INTERNAL NOTES:
─────────────────
[Add internal note - not visible to customer]
[Previous notes...]
"Contacted 2 hours ago - no response yet. Follow up tomorrow."

ACTIONS:
──────────────────────────────────────────
[Reply via Email] [Schedule Call] [Send Proposal] [Archive] [Spam] [Delete]

[Reply via Email]:
To: john@example.com
Subject: Re: General Inquiry
Body: [Rich text editor]
[Send] [Save Draft]

Email History (if exchange):
You → John: "Thanks for inquiry..." (Jan 14, 2:20 PM)
John → You: "[Customer message...]" (Jan 14, 2:15 PM)
```

---

### 3. **Inquiry Forms Configuration**

**Form Builder (Simple):**
```
INQUIRY FORMS

[+ Create New Form]

Form: "Contact Form" (Homepage)
─────────────────────────────
Status: ☑️ Active
Embed Code: <iframe src="..."> or [Copy HTML]

Fields:
┌─────────────┬─────────┬──────────┐
│ Field       │ Type    │ Required │
├─────────────┼─────────┼──────────┤
│ Name        │ Text    │ ☑️       │
│ Email       │ Email   │ ☑️       │
│ Phone       │ Tel     │ ☐        │
│ Company     │ Text    │ ☐        │
│ Message     │ Textarea│ ☑️       │
│ Budget      │ Dropdown│ ☐        │
└─────────────┴─────────┴──────────┘

[+ Add Field] [Remove Field] [Reorder (drag)]

Notifications:
☑️ Email admin on submission: [admin@yoursite.com]
☑️ Send auto-reply to submitter: [Subject] [Body template]
☐ Post to Slack webhook: [URL]

Spam Protection:
☑️ CAPTCHA: [reCAPTCHA v3]
☑️ Rate limit: [1 submission per IP per hour]

[Save Form] [Preview Form]
```

---

### 4. **Bulk Inquiry Actions**

**Bulk Select & Actions:**
```
[5 selected] | [Mark as In Progress] [Mark as Done] [Export to CSV] [Delete] [Send Email]

[Export to CSV]:
Columns: Name, Email, Phone, Company, Message, Source, Date, Assigned To
[Download inquiry_export_jan14.csv]

[Send Email]:
To: [5 selected submitters]
Subject: [Special offer for you]
Body: [Rich text]
[Preview] [Send]
```

---

## Security, RBAC & Audit

### 1. **Role-Based Access Control (RBAC) Matrix**

**Roles Defined:**

| Feature | Owner | Admin | Editor | Manager | SEO | Sales | Viewer |
|---------|-------|-------|--------|---------|-----|-------|--------|
| **CONTENT** | | | | | | | |
| Create Article | ✅ | ✅ | ✅ | ✅ | — | — | — |
| Edit Own | ✅ | ✅ | ✅ | ✅ | — | — | — |
| Edit Others | ✅ | ✅ | — | ✅ | — | — | — |
| Publish | ✅ | ✅ | — | ✅ | — | — | — |
| Archive | ✅ | ✅ | — | ✅ | — | — | — |
| **SEO** | | | | | | | |
| View SEO | ✅ | ✅ | ✅ | ✅ | ✅ | — | — |
| Edit SEO | ✅ | ✅ | ✅ | ✅ | ✅ | — | — |
| Bulk SEO | ✅ | ✅ | — | ✅ | ✅ | — | — |
| **PEOPLE** | | | | | | | |
| Create User | ✅ | ✅ | — | — | — | — | — |
| Edit User | ✅ | ✅ | — | — | — | — | — |
| Assign Role | ✅ | ✅ | — | — | — | — | — |
| **LEADS** | | | | | | | |
| View Inquiries | ✅ | ✅ | — | ✅ | — | ✅ | — |
| Update Status | ✅ | ✅ | — | ✅ | — | ✅ | — |
| Assign | ✅ | ✅ | — | ✅ | — | ✅ | — |
| Export | ✅ | ✅ | — | ✅ | — | ✅ | — |
| **ADMIN** | | | | | | | |
| Manage Users | ✅ | ✅ | — | — | — | — | — |
| Manage Roles | ✅ | ✅ | — | — | — | — | — |
| View Audit Log | ✅ | ✅ | — | — | — | — | — |
| Manage Settings | ✅ | ✅ | — | — | — | — | — |
| **MEDIA** | | | | | | | |
| Upload | ✅ | ✅ | ✅ | ✅ | ✅ | — | — |
| Delete | ✅ | ✅ | — | ✅ | — | — | — |
| **LOCALIZATION** | | | | | | | |
| Add Language | ✅ | ✅ | — | — | — | — | — |
| Translate | ✅ | ✅ | ✅ | ✅ | ✅ | — | — |

**Legend:**
- ✅ = Full Permission
- — = No Permission
- ☑️ (Future) = Can be enabled in v2

---

### 2. **Creating & Editing Roles**

**Admin > Roles & Permissions:**
```
ROLES & PERMISSIONS

System Roles (cannot edit):
├── Owner (Full access)
├── Admin (Full access except delete users)
└── Viewer (Read-only)

Custom Roles:
├── Editor (Can create & publish content)
├── Content Manager (Edit + bulk operations)
├── SEO Specialist (SEO only, no content)

[+ Create Role]
[Edit] [Duplicate] [Delete] (for custom roles only)
```

**Role Editor:**
```
EDIT ROLE: "Content Manager"

Role Name: Content Manager
Description: Can create, edit, and publish content. Manage bulk operations.

PERMISSIONS (Grouped by Module):

CONTENT
☑️ Create articles
☑️ Edit own articles
☑️ Edit other's articles
☑️ Publish articles
☑️ Archive articles
☐ Delete articles (not permitted)

SEO
☑️ View SEO
☑️ Edit SEO
☑️ Bulk SEO operations
☐ Configure robots/redirects

MEDIA
☑️ Upload media
☑️ Delete own media
☐ Delete other's media (not permitted)

LEADS
☑️ View inquiries
☑️ Update status
☑️ Assign inquiries
☑️ Export inquiries
☐ Delete inquiries (not permitted)

ADMIN
☐ Manage users
☐ Manage roles
☐ View audit logs
☐ Manage settings

[Save] [Cancel] [Reset to Default]
```

---

### 3. **User Management**

**Users List:**
```
USERS & TEAM ACCOUNTS

[+ Add User]

User | Email | Role | Status | Last Active | MFA | Actions
──────────────────────────────────────────────────────────────────
Alice | alice@.. | Admin | Active | Today, 2PM | ☑️ | [Edit] [Suspend] [Reset MFA]
Bob | bob@.. | Editor | Active | Yesterday | ☐ | [Edit] [Suspend] [Reset MFA] ⚠️
Carol | carol@.. | SEO Specialist | Active | 3 days ago | ☑️ | [Edit] [Suspend]
Dave | dave@.. | Viewer | Suspended | 1 week ago | — | [Edit] [Reactivate]

[Set MFA Requirement] [Bulk Actions]
```

**Create User:**
```
NEW USER

Email: [user@example.com] (must be unique)
First Name: [John]
Last Name: [Doe]
Role: [Editor ▼] (options: Owner, Admin, Editor, SEO, Manager, Viewer)
Status: ☑️ Active

Send Invitation Email: ☑️
  Subject: "You've been invited to [Company] Admin Panel"
  Body: [Auto-generated invite link, expires in 7 days]

[Create User] [Cancel]
```

**Edit User:**
```
EDIT USER: Alice (alice@example.com)

Email: alice@example.com (read-only)
First Name: Alice
Last Name: Smith
Role: [Admin ▼]
Status: ☑️ Active

MFA Status: ☑️ Enabled (Jan 14, 2025)
[Reset MFA] (will require re-setup on next login)

Sessions:
─────────
Device | IP | Last Active | Action
Chrome/macOS | 192.168.1.1 | 2 hours ago | [Logout]
Safari/iOS | 203.0.113.45 | 12 hours ago | [Logout]
[Logout All Sessions] (force user to re-authenticate)

Permissions (inherited from Role):
[View inherited permissions from Admin role]

Last Login: Jan 14, 2026 at 2:15 PM EST
[Save] [Reset Password] [Delete User] [Cancel]
```

**Delete User:**
```
DELETE USER: alice@example.com?

⚠️ Warning: Alice is assigned as author/editor for 15 articles.

Options:
○ Delete user (reassign content to: [Admin ▼])
○ Suspend user instead (user can't login, content remains)

Content Reassignment:
Reassign to: [Admin ▼]
  Articles by Alice: 15 (reassign to selected admin)
  Inquiries assigned: 8 (reassign to selected manager)

[Cancel] [Confirm Delete]
```

---

### 4. **Multi-Factor Authentication (MFA)**

**MFA Enforcement (Admin Setting):**
```
SECURITY SETTINGS

MFA Requirement:
☑️ Require MFA for: [All Admin Users ▼]
   Options: All Users | Admins Only | Optional

Method:
☑️ TOTP (Authenticator App: Google Authenticator, Authy, Microsoft Authenticator)
☐ SMS (Twilio integration)
☐ Email (magic link)
☑️ Backup Codes (single-use codes for recovery)

Grace Period: [7 days] (how long users have to set up MFA after enforcement)
```

**User MFA Setup (First Login After Requirement):**
```
SETUP MULTI-FACTOR AUTHENTICATION

Step 1: Download Authenticator App
Install Google Authenticator, Authy, or Microsoft Authenticator on your phone.

Step 2: Scan QR Code
┌─────────────┐
│  [QR CODE]  │
│ Cannot scan?│
│ Enter code: │
│ abcd-efgh   │
└─────────────┘

Step 3: Enter Code
Google Authenticator shows: 123456
Enter Code: [123456]
[Verify]

Step 4: Backup Codes
Save these codes in a safe place. Each code can be used once if you lose access to your authenticator.

Code 1: abcd-1234
Code 2: efgh-5678
...
Code 10: ijkl-9012

[Copy] [Download] [Print]

[I saved my backup codes] [Skip] [Next]
```

**On Login (With MFA Enabled):**
```
EMAIL: alice@example.com
PASSWORD: [••••••••]
[Continue]

MULTI-FACTOR AUTHENTICATION

Enter the 6-digit code from your authenticator app:
[      ]

[Use backup code instead]
[Didn't receive code?]
[Login]
```

---

### 5. **Audit Log**

**Audit Log View:**
```
AUDIT LOG / ACTIVITY HISTORY

[Filter by User] [Filter by Action] [Filter by Date] [Filter by Entity]

Action | User | Entity | Details | Timestamp | IP | User Agent
─────────────────────────────────────────────────────────────────────────
Publish | Alice | Article | "SEO Guide" published | Jan 14, 2:15 PM | 192.. | Chrome/macOS
Edit | Bob | Article | Title changed | Jan 14, 2:10 PM | 203.. | Safari/iOS
Create | Carol | User | alice@example.com created | Jan 14, 1:45 PM | 198.. | Chrome/Win
Delete | Dave | Media | "old-image.jpg" soft deleted | Jan 13, 11:30 AM | 209.. | Firefox/Linux
UpdateRole | Admin | User | Bob role: Editor → Admin | Jan 13, 10:00 AM | 192.. | Chrome/macOS
MFADisabled | Alice | Security | MFA disabled by admin | Jan 12, 5:20 PM | — | —
SessionLogout | Bob | Session | Logged out from all devices | Jan 12, 3:00 PM | 203.. | —

[Export to CSV] [Download] [Print]

Detailed View (Click row):
───────────────────────────────────────
Action: Update
Entity: Article #42
Entity Name: "How to Optimize Your Website"
User: Alice Smith (alice@example.com)
Role: Admin
Timestamp: Jan 14, 2026 at 2:15 PM EST
IP Address: 192.168.1.1 (ISP: Comcast)
Device: Chrome 120, macOS Sonoma

Changes (Fields Modified):
Title: "Old Title" → "How to Optimize Your Website"
Body: "[12,543 chars] → [13,201 chars]" (see full diff)
Status: "Draft" → "Published"
published_at: NULL → "2026-01-14T14:15:00Z"

Audit Trail: Log stored and immutable
Retention: 90 days (configurable)
```

**Audit Log Export:**
```
[Export to CSV]

audit_log_jan14_2026.csv
─────────────────────────
timestamp, user, email, action, entity_type, entity_id, entity_name, changes, ip, user_agent
2026-01-14T14:15:00Z, Alice Smith, alice@example.com, publish, article, 42, "How to Optimize Your Website", "{...}", 192.168.1.1, "Chrome 120..."
...
```

**Automatic Audit Fields (Always Captured):**
- Timestamp (when action occurred)
- User (who performed action)
- Action type (create, edit, delete, publish, archive, etc.)
- Entity (article, user, media, form, etc.)
- Entity ID & name
- Old value → New value (for updates)
- IP address
- User-Agent (browser, OS)
- Status (success/error)

---

### 6. **Security Best Practices**

**Session Management:**
- Session timeout: 30 minutes of inactivity (configurable)
- Absolute session limit: 8 hours (force re-login)
- Secure cookies: `HttpOnly`, `Secure`, `SameSite=Lax`
- Session binding: IP address + User-Agent (detect suspicious activity)

**Password Policy:**
```
SECURITY SETTINGS > Password Requirements

☑️ Minimum length: [12 characters]
☑️ Require uppercase: A-Z
☑️ Require lowercase: a-z
☑️ Require numbers: 0-9
☑️ Require special: !@#$%
☑️ No reuse of last [5] passwords
☑️ Expiration: [90 days]
☑️ Reset required after: First login, Password compromise detected

Strength Indicator (on password change):
[Weak] [Fair] [Good] [Strong] [Very Strong]
```

**Sensitive Action Confirmations:**
- Deleting user: Confirmation dialog
- Changing role: "This will give [User] access to [X] sensitive features"
- Resetting password: Email confirmation sent to user
- Disabling MFA: Confirmation + explanation why

**Dangerous Action Logging:**
- All admin actions logged (immutable audit trail)
- Delete operations: Can be undone (soft delete + restore)
- Permission changes: Logged immediately
- MFA changes: Notification sent to user

---

## Accessibility (WCAG/ARIA)

### 1. **Keyboard Navigation Checklist**

**Core Requirement:** All functionality must be operable via keyboard alone (no mouse).

| Element | Keyboard Support |
|---------|---|
| **Links** | Tab to focus, Enter to activate |
| **Buttons** | Tab to focus, Space/Enter to activate |
| **Form Fields** | Tab through inputs in logical order, Tab+Shift backwards |
| **Dropdowns** | Tab to open, Arrow keys to navigate, Enter to select |
| **Checkboxes/Radios** | Tab to focus, Space to toggle |
| **Modal/Dialog** | Tab cycles within modal, Escape to close, focus returned to trigger |
| **Data Table** | Tab through selectable rows, Space to select, Arrow keys for navigation |
| **Rich Editor** | Tab through toolbar buttons, Ctrl+B/I/U for formatting |
| **Search** | Enter to search, Escape to clear |

**Focus Management:**
- Visible focus indicator (not removed by CSS): 2px outline in brand color
- Focus visible on: Links, buttons, inputs, rows, dropdowns
- Focus order matches logical flow (left-to-right, top-to-bottom)
- Modal dialogs: Focus trapped within modal, Escape closes, focus returns to trigger button

```css
/* Ensure focus visible (don't remove!) */
*:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}
```

---

### 2. **ARIA Attributes for Complex Components**

**Data Table:**
```html
<table role="table">
  <thead>
    <tr>
      <th scope="col" role="columnheader">
        <input type="checkbox" aria-label="Select all rows">
      </th>
      <th scope="col" role="columnheader" aria-sort="ascending">
        Title
      </th>
      <th scope="col" role="columnheader">Status</th>
      <th scope="col" role="columnheader">Actions</th>
    </tr>
  </thead>
  <tbody>
    <tr aria-selected="false">
      <td><input type="checkbox" aria-label="Select row 'Article Title'"></td>
      <td>Article Title</td>
      <td><span role="status">Published</span></td>
      <td>
        <button aria-label="Edit 'Article Title'">Edit</button>
      </td>
    </tr>
  </tbody>
</table>
```

**Form with Error Handling:**
```html
<div class="form-group">
  <label for="title">Title <span aria-label="required">*</span></label>
  <input
    id="title"
    type="text"
    required
    aria-required="true"
    aria-invalid="false"
    aria-describedby="title-error"
  >
  <div id="title-error" role="alert">
    ❌ Title is required
  </div>
</div>
```

**Modal Dialog:**
```html
<div
  role="dialog"
  aria-labelledby="modal-title"
  aria-modal="true"
>
  <h2 id="modal-title">Publish Article?</h2>
  <p>This will make the article live immediately.</p>
  <button autofocus>Publish</button>
  <button>Cancel</button>
</div>
```

**Combobox (Autocomplete/Dropdown):**
```html
<div class="combobox-wrapper">
  <input
    role="combobox"
    aria-autocomplete="list"
    aria-expanded="false"
    aria-controls="listbox-id"
    aria-owns="listbox-id"
  >
  <ul id="listbox-id" role="listbox">
    <li role="option">Option 1</li>
    <li role="option" aria-selected="true">Option 2</li>
    <li role="option">Option 3</li>
  </ul>
</div>
```

**Loading & Status Messages:**
```html
<!-- Loading -->
<div role="status" aria-live="polite" aria-label="Loading">
  Saving article... 
</div>

<!-- Success -->
<div role="status" aria-live="assertive" class="success">
  ✅ Article published successfully!
</div>

<!-- Error -->
<div role="alert" aria-live="assertive" class="error">
  ⊘ Failed to save. Please try again.
</div>
```

---

### 3. **Color Contrast & Readability**

**Minimum Contrast Ratios (WCAG AA):**
- Normal text (< 18px): **4.5:1** (text vs. background)
- Large text (≥ 18px): **3:1**
- UI components & borders: **3:1**

**Testing Tools:**
- WebAIM Contrast Checker
- Chrome DevTools (Lighthouse Accessibility audit)
- axe DevTools extension

**Examples:**
```
✅ Black text (#000) on white (#FFF): 21:1 (excellent)
✅ Dark blue (#003D99) on white: 8.6:1 (passes)
❌ Gray (#808080) on white: 4.48:1 (fails, need darker gray)
❌ Using color alone for error (red icon without text): Inaccessible
✅ Error with icon + text: "❌ Title is required" (accessible)
```

---

### 4. **Accessible Forms**

**Form Labels (Always Visible):**
```html
<!-- ✅ Good: Label associated with input -->
<label for="email">Email Address *</label>
<input id="email" type="email" required aria-required="true">

<!-- ❌ Bad: Placeholder as label -->
<input placeholder="Enter email" type="email"> <!-- No label! -->

<!-- ❌ Bad: Label not associated -->
<label>Email Address</label>
<input type="email"> <!-- Which input? -->
```

**Error Messages (Accessible):**
```html
<!-- ✅ Good: Error linked to field -->
<label for="title">Title *</label>
<input
  id="title"
  aria-required="true"
  aria-invalid="true"
  aria-describedby="title-error"
>
<div id="title-error" role="alert">
  Title is required
</div>

<!-- ❌ Bad: Generic error, not linked -->
<input id="title">
<div class="error">Please fill all fields</div> <!-- Which field? -->
```

**Help Text & Hints:**
```html
<label for="slug">URL Slug *</label>
<input
  id="slug"
  aria-describedby="slug-hint"
>
<small id="slug-hint">
  Lowercase letters and hyphens only. 
  Example: "my-article-title"
</small>
```

---

### 5. **Accessible Data Tables**

**Requirements:**
- `<table>` semantic markup (not divs)
- `<thead>` for header row
- `<tbody>` for body rows
- `scope="col"` on header cells
- `scope="row"` on row header cells (if applicable)

```html
<table>
  <caption>Articles by Status</caption> <!-- Optional but helpful -->
  <thead>
    <tr>
      <th scope="col">Title</th>
      <th scope="col">Author</th>
      <th scope="col">Status</th>
      <th scope="col">Published Date</th>
      <th scope="col">Actions</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>How to Optimize</td>
      <td>Alice</td>
      <td>Published</td>
      <td>Jan 14, 2026</td>
      <td>
        <button aria-label="Edit 'How to Optimize'">Edit</button>
      </td>
    </tr>
  </tbody>
</table>
```

**Sortable Headers:**
```html
<th scope="col" role="columnheader" aria-sort="ascending">
  <button>
    Title
    <span aria-label="Sorted ascending">▲</span>
  </button>
</th>
```

---

### 6. **Accessible Rich Text Editors**

**Toolbar with ARIA Labels:**
```html
<div role="toolbar" aria-label="Text formatting">
  <button title="Bold (Ctrl+B)" aria-label="Bold" aria-pressed="false">
    <strong>B</strong>
  </button>
  <button title="Italic (Ctrl+I)" aria-label="Italic" aria-pressed="false">
    <em>I</em>
  </button>
  <button title="Underline (Ctrl+U)" aria-label="Underline" aria-pressed="false">
    <u>U</u>
  </button>
</div>
```

**Keyboard Shortcuts Display:**
```html
<details>
  <summary>Keyboard Shortcuts</summary>
  <ul>
    <li>Ctrl+B: Bold</li>
    <li>Ctrl+I: Italic</li>
    <li>Ctrl+K: Insert Link</li>
  </ul>
</details>
```

---

### 7. **Semantic HTML & Landmarks**

**Page Structure:**
```html
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Articles | Admin Panel</title>
</head>
<body>
  <header role="banner">
    <h1>Admin Panel</h1>
    <nav aria-label="Main navigation">
      <ul>
        <li><a href="/admin">Dashboard</a></li>
        <li><a href="/admin/articles">Articles</a></li>
        ...
      </ul>
    </nav>
  </header>

  <main role="main">
    <h1>Articles</h1>
    <!-- Content -->
  </main>

  <aside role="complementary" aria-label="Sidebar">
    <!-- Secondary content -->
  </aside>

  <footer role="contentinfo">
    <p>&copy; 2026 Company Name</p>
  </footer>
</body>
</html>
```

**Landmarks Help Screen Readers:**
- `<header>` / `role="banner"`: Site header
- `<nav>` / `role="navigation"`: Navigation
- `<main>` / `role="main"`: Main content
- `<aside>` / `role="complementary"`: Sidebar
- `<footer>` / `role="contentinfo"`: Footer
- `<section>` with `aria-labelledby`: Section regions

---

## Screen List & Component Inventory

### 1. **Admin Panel Screen List**

| Screen | URL | Purpose | Roles | MVP | Complexity |
|--------|-----|---------|-------|-----|------------|
| **Dashboard** | `/admin` | Overview stats, recent activity | All | ✅ | Low |
| **Articles List** | `/admin/articles` | Browse, search, filter articles | Editor+ | ✅ | Medium |
| **Article New** | `/admin/articles/new` | Create new article | Editor+ | ✅ | High |
| **Article Edit** | `/admin/articles/:id` | Edit article, manage versions | Editor+ | ✅ | High |
| **Case Studies** | `/admin/cases` | Manage cases (similar to articles) | Editor+ | ✅ | High |
| **Team Members** | `/admin/team` | Create/edit team profiles | HR+ | ✅ | Medium |
| **Services** | `/admin/services` | Manage services + practice areas | Editor+ | ✅ | Medium |
| **FAQ** | `/admin/faq` | Create/manage FAQ items | Editor+ | ✅ | Medium |
| **Reviews** | `/admin/reviews` | Manage testimonials | Editor+ | ✅ | Low |
| **Inquiries** | `/admin/leads` | Manage form submissions | Sales+ | ✅ | Medium |
| **Media Library** | `/admin/media` | Upload, organize, manage files | All | ✅ | Medium |
| **Languages** | `/admin/localization` | Add/manage languages, translation status | Admin+ | ⏳ v1.5 | Medium |
| **SEO Center** | `/admin/seo` | Manage meta tags per URL | SEO+ | ⏳ v1.5 | High |
| **Users** | `/admin/users` | Create/manage user accounts | Admin | ✅ | Medium |
| **Roles** | `/admin/roles` | Configure role permissions (RBAC) | Owner/Admin | ✅ | High |
| **Audit Log** | `/admin/audit` | View change history | Admin+ | ✅ | Low |
| **Settings** | `/admin/settings` | Site-wide configuration | Admin | ⏳ v2 | Low |
| **Integrations** | `/admin/integrations` | Connect external services | Admin | ⏳ v2 | Medium |

**MVP Scope:**
- ✅ Core CRUD for articles, team, services
- ✅ User management & RBAC
- ✅ Media upload
- ✅ Inquiry form handling
- ✅ Audit log
- ⏳ v1.5: Localization, SEO Center, Publishing Calendar
- ⏳ v2: Integrations, Email templates, Custom fields

---

### 2. **Core UI Components Required**

**Layout & Navigation:**
- Sidebar navigation (expandable/collapsible)
- Top bar with user menu
- Breadcrumb navigation
- Tabs (for language, status filtering)
- Accordion (for form sections)

**Data Display:**
- Data table (sortable, filterable, paginated)
- Empty state illustration
- Loading skeleton
- Error state message
- Status badge (color-coded)
- Avatar with fallback

**Forms & Inputs:**
- Text input (with validation state)
- Email input
- Password input
- Textarea
- Select dropdown
- Multi-select dropdown
- Checkbox
- Radio button group
- Date picker
- Time picker
- Date range picker
- File upload (drag & drop)
- Rich text editor (WYSIWYG)
- Slug input (with auto-generation)
- Tag input (auto-complete)

**Actions & Feedback:**
- Primary button (main action)
- Secondary button (alternative action)
- Danger button (destructive action)
- Button with loading state
- Disabled button (with tooltip)
- Icon button
- Floating action button (FAB) - optional
- Dropdown menu
- Context menu (right-click)
- Tooltip (on hover)
- Modal dialog
- Confirmation dialog
- Toast notification (success, error, warning)
- Alert banner (top of page)
- Progress indicator
- Spinner/Loader

**Media & Preview:**
- Image thumbnail with delete/replace
- Image upload with progress
- Document icon with type indicator
- Media picker modal
- Preview modal (image, video)
- Lightbox gallery

**Data Visualization (v2+):**
- Simple line chart (publish rate over time)
- Bar chart (traffic by article)
- Pie chart (content by category)
- Stat card (key metric)

---

## Design System & UI Kit Requirements

### 1. **Design System Foundations**

**Color Palette:**
- Brand color (primary): Teal/Blue
- Semantic colors:
  - Success: Green (#22C55E)
  - Error: Red (#EF4444)
  - Warning: Amber (#F59E0B)
  - Info: Blue (#3B82F6)
- Neutral: Gray scale (5 shades: 50, 200, 400, 600, 900)
- Background: White / Very light gray (#F5F5F5)

**Typography:**
- Font family: System stack (San Francisco, Segoe UI, Helvetica, Arial)
- Sizes:
  - Heading 1: 32px / 40px line-height, bold
  - Heading 2: 24px / 32px, semibold
  - Heading 3: 20px / 28px, semibold
  - Body: 14px / 20px, regular
  - Small: 12px / 16px, regular
  - Code: Monospace 12px
- Font weight: Light (300), Regular (400), Semibold (600), Bold (700)

**Spacing System (8px grid):**
- xs: 4px
- sm: 8px
- md: 16px
- lg: 24px
- xl: 32px
- 2xl: 48px

**Radius:**
- sm: 4px (small elements)
- md: 8px (buttons, inputs, default)
- lg: 12px (cards, modals)
- full: 9999px (pills, avatars)

**Shadows:**
- sm: 0 1px 2px rgba(0,0,0,0.05)
- md: 0 4px 6px rgba(0,0,0,0.07)
- lg: 0 10px 15px rgba(0,0,0,0.1)

**Icons:**
- Library: Feather Icons, Heroicons, or custom SVG
- Size: 16px (small), 20px (default), 24px (large)
- Stroke width: 2px (consistent)

---

### 2. **Component Specifications**

**Button Component:**
```
PRIMARY BUTTON
Text: "Publish"
State: Default | Hover | Pressed | Disabled | Loading
Color: Brand (teal)
Padding: 8px 16px
Radius: 8px
Font-weight: 600
Min-width: 100px
Height: 40px

.btn--primary:hover {
  background: darker teal
  cursor: pointer
}

.btn--primary:focus-visible {
  outline: 2px solid brand color
  outline-offset: 2px
}

.btn--primary:disabled {
  opacity: 0.5
  cursor: not-allowed
}

.btn--primary.loading {
  icon: spinner
  text hidden or disabled
  pointer-events: none
}
```

**Input Component:**
```
Text Input
Placeholder: "Search articles..."
Height: 36px
Padding: 8px 12px
Border: 1px solid #ddd
Border-radius: 8px
Font-size: 14px

States:
Default: Gray border
Focus: Brand color border + shadow
Error: Red border, error icon on right
Disabled: Light gray background, opacity 0.6
Loading: Spinner on right

Help text below:
Font-size: 12px, gray color
```

**Data Table:**
```
Header:
- Height: 44px
- Font-weight: 600
- Background: Light gray (#F5F5F5)
- Borders: Bottom border 1px solid #ddd

Body Row:
- Height: 44px (default density)
- Alternating background: None or very subtle gray
- Hover: Light background change
- Border: Bottom 1px solid #eee (subtle)

Padding:
- Cell left/right: 12px
- Row height: 44px (fits touch target for mobile)

Sticky Header:
- Header stays fixed when scrolling
- Box-shadow to indicate stickiness
```

---

### 3. **Recommended Design Tool & Implementation**

**Design Tool:**
- Figma (cloud-based, collaborative)
- Storybook for component library

**Frontend Framework:**
- React + TypeScript (industry standard for admin panels)
- UI Library options:
  - Headless UI (unstyled, accessible components)
  - Radix UI (low-level accessible primitives)
  - MUI (Material Design, comprehensive but opinionated)
  - shadcn/ui (Tailwind + Headless UI, highly customizable)

**Styling:**
- Tailwind CSS (utility-first, scalable)
- CSS Modules (scoped styles)
- CSS-in-JS (Styled Components, Emotion) - if needed

**Testing:**
- Storybook for component documentation & visual testing
- Jest + React Testing Library for unit/integration tests
- Playwright for E2E tests

---

## Implementation Roadmap

### **Phase 1: MVP (Weeks 1–8)**

**Goal:** Core CRUD + publishing + basic RBAC

**Features:**
- ✅ Dashboard (overview stats)
- ✅ Articles CRUD (create, edit, publish, archive)
- ✅ Team Members CRUD
- ✅ Services/Practice Areas CRUD
- ✅ Case Studies CRUD
- ✅ Inquiries management
- ✅ Media Library (upload, organize)
- ✅ Basic RBAC (Owner, Admin, Editor, Viewer)
- ✅ User management (create, assign role)
- ✅ Audit Log (basic)
- ✅ Draft auto-save

**NOT Included:**
- ❌ Localization (language tabs)
- ❌ SEO Center (meta management)
- ❌ Publishing calendar
- ❌ Advanced workflows (review/approval)
- ❌ MFA enforcement
- ❌ Custom fields

---

### **Phase 2: Enhancement (Weeks 9–14)**

**Goal:** Localization, SEO, Advanced workflows

**Features:**
- ✅ Localization: Language management, translation tabs, translation status reports
- ✅ SEO Center: Meta title/description, canonical, robots, OG tags, hreflang
- ✅ Publishing Calendar: Schedule content, view publishing timeline
- ✅ Content Review Workflow: Draft → Review → Publish
- ✅ Version History: See change history, restore versions
- ✅ Bulk Operations: Publish/archive/delete multiple items
- ✅ Advanced Filters: Save filter presets, quick filters

**Refinements:**
- Better error messages
- Keyboard shortcuts (Cmd+K command palette)
- Performance optimization (pagination, caching)

---

### **Phase 3: Polish (Weeks 15–18)**

**Goal:** Security, Accessibility, Performance

**Features:**
- ✅ MFA enforcement (TOTP)
- ✅ Session management (timeout, logout all)
- ✅ Enhanced audit log (detailed change tracking)
- ✅ Full WCAG 2.1 AA compliance (accessibility audit)
- ✅ Responsive design (mobile-friendly)
- ✅ Notification center (task status updates)
- ✅ API rate limiting & DDoS protection

**Performance:**
- Lazy load sections
- Optimize data table rendering (virtualization for 1000+ rows)
- Image optimization (lazy load, responsive images)
- Minify assets
- CDN for static files

---

### **Phase 4: Advanced Features (v2, Post-Launch)**

**Features:**
- ☐ Custom fields per entity
- ☐ Integrations (Zapier, Make, etc.)
- ☐ Email templates editor
- ☐ AI-powered content suggestions (auto-generate meta descriptions, SEO recommendations)
- ☐ Analytics dashboard (traffic, engagement by article)
- ☐ Export/Import (CSV, JSON)
- ☐ Webhooks for external systems
- ☐ Branching/staging environment (preview changes)
- ☐ User activity heatmap (who's doing what)
- ☐ A/B testing framework (title, description variants)

---

## Risks & Antipatterns

### ❌ Common Admin Panel Antipatterns (What to AVOID)

| Antipattern | Problem | Solution |
|-------------|---------|----------|
| **Nested Menus (3+ levels)** | Users get lost; can't find features | Keep hierarchy ≤ 2 levels; use search/command palette |
| **No Status Indicator** | Users don't know item state (draft vs. published) | Show status badge, icon, color on every row |
| **Slow Table Rendering** | 1000+ rows cause lag | Implement server-side pagination, virtual scrolling |
| **Confusing Save Behavior** | User doesn't know if changes saved (especially on auto-save) | Show explicit: "Saving..." → "Saved" feedback |
| **No Bulk Operations** | Editing 50 items requires 50 clicks | Implement checkbox multi-select + bulk actions |
| **Complex Workflows Without Guidance** | User publishes by accident when they meant to draft | Show confirmation dialogs for destructive actions |
| **Inadequate Search** | Users can't find anything without browsing | Global search (Cmd+K), filters, saved searches |
| **Inaccessible to Power Users** | Experts want keyboard shortcuts, not mouse-clicking | Support keyboard navigation, hotkeys, command palette |
| **No Undo/Recovery** | Accidental delete is permanent | Implement soft delete, trash bin, version history |
| **Missing Audit Trail** | Can't see who changed what | Log all changes with timestamp, user, IP |
| **Weak Permission Model** | Editor can delete articles (shouldn't be possible) | Granular RBAC: separate create/edit/publish/delete |
| **No Error Messages** | User sees "Error 422" and is lost | Show specific, actionable error messages |
| **Date/Time Zone Confusion** | Content scheduled for wrong time (EST vs. UTC) | Always show timezone, convert to user's TZ |
| **Text Truncation Without Tooltip** | User can't see full title in table | Use text ellipsis with tooltip on hover |
| **Single Column for Duplicate Data** | Can't tell apart similar items (e.g., two "About" pages) | Show unique identifier (slug, ID, or path) |
| **Modal Overload** | Too many nested modals confuse users | Use modals for confirmation/short forms only; use full pages for complex workflows |
| **No Loading States** | UI feels frozen during async operations | Show spinner, skeleton loader, progress indicator |
| **Disabled Buttons Without Tooltip** | User doesn't know why button is disabled | Show tooltip: "Complete required fields to publish" |

---

### 🎯 Key Risk Mitigations

**Risk: Data Loss Due to Accidental Delete**
- ✅ Mitigation: Soft delete (mark as deleted, keep in DB), trash bin, undo within 30 days
- ✅ Confirmation: "Delete 'Article Title'? This can be undone within 30 days."

**Risk: Permission Escalation (User edits other user's role to Admin)**
- ✅ Mitigation:
  - Owner/Admin only can manage users & roles
  - Audit log tracks all permission changes
  - Session binding (IP + User-Agent detection)
  - MFA required for sensitive actions

**Risk: Session Hijacking**
- ✅ Mitigation:
  - Secure cookies (HttpOnly, Secure, SameSite)
  - Session timeout (30 min inactivity, 8 hour absolute)
  - "Logout all devices" option for users
  - Notify user on unusual IP/device change

**Risk: Unintended Content Publication**
- ✅ Mitigation:
  - Status field (Draft/Scheduled/Published) separate from save
  - Explicit "Publish" button (not just "Save")
  - Confirmation dialog: "This will go live immediately"
  - Schedule feature (publish at specific time)
  - Review/Approval workflow (optional)

**Risk: SEO Metadata Incomplete/Wrong**
- ✅ Mitigation:
  - SEO section marked "⚠️ Incomplete" if missing meta title/description
  - Character counters show limit
  - Preview snippet shows how it looks in Google
  - Bulk SEO feature to auto-generate defaults
  - Validation: warn if meta title > 60 chars

**Risk: Translation Missing for Published Content**
- ✅ Mitigation:
  - Translation status report shows gaps
  - Prevent deleting language if published content exists
  - Warning badge: "Content not translated to French"
  - Fallback logic: show EN version if FR missing (configurable)
  - Migration path: reassign content to fallback language before deleting locale

**Risk: Admin Panel Performance Degrades with Scale**
- ✅ Mitigation:
  - Server-side pagination (not load-all at once)
  - Database indexes on frequently filtered columns
  - Caching (articles, team members, taxonomies)
  - CDN for media
  - API rate limiting to prevent abuse

---

### 📋 Pre-Launch Security Checklist

**Authentication & Session:**
- [ ] HTTPS enforced (no HTTP)
- [ ] Secure cookies: HttpOnly, Secure, SameSite=Lax
- [ ] Session timeout after 30 min inactivity
- [ ] Absolute session limit 8 hours
- [ ] Session invalidation on logout
- [ ] CSRF tokens on state-changing requests

**Authorization:**
- [ ] RBAC enforced on backend (not just frontend)
- [ ] No privilege escalation possible
- [ ] Audit log tracks all permission changes
- [ ] Regular RBAC audit (quarterly)

**Data Protection:**
- [ ] Sensitive data encrypted (passwords via bcrypt, API keys via encryption)
- [ ] PII not logged in audit trail (no email in logs, hash IP)
- [ ] Audit logs immutable & retained 90 days
- [ ] Database backups encrypted, stored off-site
- [ ] No hardcoded secrets (use env variables)

**Input Validation:**
- [ ] All inputs validated server-side
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (escape user input)
- [ ] CSRF prevention (token validation)
- [ ] File upload validation (type, size, scan for malware)

**MFA & Admin Access:**
- [ ] MFA required for all admins
- [ ] MFA seed/backup codes stored securely
- [ ] Admin actions logged with extra scrutiny
- [ ] IP whitelisting for admin subnet (optional)

**Monitoring & Incident Response:**
- [ ] Error tracking (Sentry, Rollbar) set up
- [ ] Suspicious activity alerts (brute force, mass deletion, etc.)
- [ ] Incident response plan documented
- [ ] Security headers configured (CSP, X-Frame-Options, etc.)

---

## Appendices

### A. Keyboard Shortcuts Cheat Sheet (Optional, for v2)

```
Navigation:
  Cmd/Ctrl + K       Open Command Palette (search, quick actions)
  Cmd/Ctrl + Home    Go to Dashboard
  Cmd/Ctrl + /       Show this cheat sheet

Editor (in rich text):
  Cmd/Ctrl + B       Bold
  Cmd/Ctrl + I       Italic
  Cmd/Ctrl + U       Underline
  Cmd/Ctrl + K       Insert Link
  Cmd/Ctrl + [       Decrease heading level
  Cmd/Ctrl + ]       Increase heading level
  Cmd/Ctrl + Z       Undo
  Cmd/Ctrl + Shift + Z   Redo

Forms:
  Tab                Move to next field
  Shift + Tab        Move to previous field
  Enter              Submit form (when in last field)
  Escape             Cancel / Close modal

Table:
  Cmd/Ctrl + A       Select all rows
  Space (on row)     Toggle row selection
  Cmd + Click        Multi-select rows
```

---

### B. Content Type Specifications

#### **Article**
- Fields: Title, Slug, Body (rich text), Featured Image, Category/Topic, Status, Author, Published Date
- Localization: Yes (multi-language)
- SEO: Yes (meta title, description)
- Versioning: Yes (save history)
- Workflow: Draft → Review → Published → Archived
- Bulk Operations: Publish, Unpublish, Archive, Delete, Add Tag

#### **Team Member**
- Fields: Name, Title/Role, Department, Bio, Photo, Email, Phone, Social Links (LinkedIn, Twitter), Expertise Tags
- Localization: Partial (Bio in multiple languages)
- SEO: No
- Versioning: No
- Workflow: Draft → Published (simple)
- Bulk Operations: Assign Department, Delete, Export

#### **Service / Practice Area**
- Fields: Name, Slug, Description, Icon, Featured Image, Status
- Localization: Yes
- SEO: Yes
- Versioning: No
- Workflow: Draft → Published
- Bulk Operations: Publish, Archive

#### **Case Study**
- Fields: Title, Slug, Client Name, Challenge, Solution, Result/Impact, Featured Image, Team Members (multi-select), Services (multi-select), Industry Tag, Status
- Localization: Yes
- SEO: Yes
- Versioning: Yes
- Workflow: Draft → Review → Published
- Bulk Operations: Publish, Archive, Add Tag

#### **Inquiry / Lead**
- Fields: Name, Email, Phone, Company, Message, Form Type, Status, Assigned To, Source, UTM, Device Type, IP Address
- Localization: N/A (unstructured user input)
- SEO: N/A
- Versioning: No (immutable record)
- Workflow: New → In Progress → Done
- Bulk Operations: Export, Assign, Mark Done, Spam

---

### C. API Endpoints (Admin Backend)

**Articles:**
```
GET    /api/v1/admin/articles              List articles (paginated)
GET    /api/v1/admin/articles/:id          Get single article
POST   /api/v1/admin/articles              Create article
PATCH  /api/v1/admin/articles/:id          Update article
DELETE /api/v1/admin/articles/:id          Soft delete article
POST   /api/v1/admin/articles/:id/publish  Publish article
POST   /api/v1/admin/articles/:id/schedule Schedule publication
POST   /api/v1/admin/articles/:id/archive  Archive article
GET    /api/v1/admin/articles/:id/history  Get version history
```

**Validation:**
```
POST   /api/v1/admin/validate/slug         Check slug uniqueness
```

**Users & RBAC:**
```
GET    /api/v1/admin/users                 List users
POST   /api/v1/admin/users                 Create user
PATCH  /api/v1/admin/users/:id             Update user
DELETE /api/v1/admin/users/:id             Delete user
GET    /api/v1/admin/roles                 List roles
PATCH  /api/v1/admin/roles/:id             Update role permissions
```

**Audit Log:**
```
GET    /api/v1/admin/audit-logs            List audit logs (with filters)
```

**Media:**
```
POST   /api/v1/admin/media/upload          Upload file(s)
GET    /api/v1/admin/media                 List media
DELETE /api/v1/admin/media/:id             Delete media
PATCH  /api/v1/admin/media/:id             Update metadata
```

---

### D. Glossary

| Term | Definition |
|------|-----------|
| **Soft Delete** | Mark item as deleted (deleted_at timestamp) but keep in database; item hidden from UI but recoverable |
| **RBAC** | Role-Based Access Control; users assigned roles (Editor, Admin, Viewer), each role has specific permissions |
| **Audit Log** | Immutable record of all changes: who, what, when, IP address, result |
| **Meta Tags** | HTML tags in page `<head>`: title, description, og:image, canonical, robots, hreflang |
| **Canonical** | Tag that tells search engines which URL is the "preferred" version (prevents duplicate content penalty) |
| **Hreflang** | Tag that specifies language alternatives (e.g., English, French, German versions of same page) |
| **Robots Meta** | Directive to search engines: index/noindex (crawl?), follow/nofollow (follow links?) |
| **OG Tags** | Open Graph tags; control how content appears on social media (title, image, description) |
| **Fallback Language** | Default language shown if content not translated to user's language |
| **Draft** | Unpublished item; private, only visible to creator and editors |
| **Scheduled** | Content set to publish at specific future date/time |
| **Published** | Live content; public, visible on website |
| **Archived** | Hidden from users; no longer maintained but kept for history |
| **Status Transition** | Moving item from one state to another (Draft → Published) |
| **Bulk Operation** | Action performed on multiple items at once (e.g., publish 10 articles) |
| **Form Validation** | Check that user input meets requirements before saving (client-side + server-side) |
| **MFA** | Multi-Factor Authentication; requires 2+ forms of ID (password + TOTP app) |
| **Session Timeout** | Auto-logout after period of inactivity (e.g., 30 minutes) |
| **WCAG** | Web Content Accessibility Guidelines; standards for accessible web design (Level A, AA, AAA) |
| **ARIA** | Accessible Rich Internet Applications; HTML attributes that improve screen reader experience |

---

## Summary & Next Steps

**This specification provides:**
1. ✅ Complete IA and navigation structure
2. ✅ UX patterns for CRUD, forms, bulk operations
3. ✅ Content workflow (draft, review, publish, schedule, archive)
4. ✅ Localization & SEO management systems
5. ✅ Security architecture (RBAC, MFA, audit log)
6. ✅ Accessibility requirements (WCAG/ARIA)
7. ✅ Implementation roadmap (MVP → v2)
8. ✅ Design system foundations

**To get started:**
1. **Approve IA & Navigation** (stakeholder alignment)
2. **Create Figma Wireframes** (key screens: list, form, detail)
3. **Design System Tokens** (colors, typography, spacing)
4. **High-Fidelity Mockups** (top 5 screens first)
5. **Prototype & Usability Test** (gather feedback from beta users)
6. **Development Sprint Planning** (assign tasks, estimate time)

**Design Review Cadence:**
- Weekly design sync (product team)
- Bi-weekly usability testing (with mock users)
- Sprint reviews (align dev + design)

---

**Document prepared by:** Staff Product Designer & UX Researcher  
**Last Updated:** January 14, 2026  
**Version:** 1.0  
**Status:** ✅ Ready for Design & Development
