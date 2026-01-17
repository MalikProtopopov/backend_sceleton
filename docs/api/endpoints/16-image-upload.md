# Image Upload API

> **Version**: 1.0.0  
> **Last Updated**: 2026-01-15

This document describes the image upload functionality for all entities in the admin panel. Images are now uploaded via dedicated multipart/form-data endpoints rather than passing URLs directly.

---

## Overview

### Key Changes from Previous API

1. **Removed URL fields from Create/Update schemas** - You can no longer pass `cover_image_url`, `image_url`, `photo_url`, `author_photo_url`, `avatar_url`, or `logo_url` in POST/PATCH requests
2. **New dedicated endpoints** - Each entity now has separate POST (upload) and DELETE endpoints for image management
3. **Direct file upload** - Images are uploaded directly via multipart/form-data

### Supported Image Formats

| Format | MIME Type | Extension |
|--------|-----------|-----------|
| JPEG | `image/jpeg` | `.jpg`, `.jpeg` |
| PNG | `image/png` | `.png` |
| WebP | `image/webp` | `.webp` |
| GIF | `image/gif` | `.gif` |

### Limits

- **Maximum file size**: 10 MB
- **Files are stored in S3** with the following key structure: `{tenant_id}/{folder}/{entity_id}.{ext}`

---

## Endpoints Summary

| Entity | Upload Endpoint | Delete Endpoint | Image Field |
|--------|----------------|-----------------|-------------|
| Articles | `POST /admin/articles/{id}/cover-image` | `DELETE /admin/articles/{id}/cover-image` | `cover_image_url` |
| Cases | `POST /admin/cases/{id}/cover-image` | `DELETE /admin/cases/{id}/cover-image` | `cover_image_url` |
| Services | `POST /admin/services/{id}/image` | `DELETE /admin/services/{id}/image` | `image_url` |
| Employees | `POST /admin/employees/{id}/photo` | `DELETE /admin/employees/{id}/photo` | `photo_url` |
| Reviews | `POST /admin/reviews/{id}/author-photo` | `DELETE /admin/reviews/{id}/author-photo` | `author_photo_url` |
| Users | `POST /auth/users/{id}/avatar` | `DELETE /auth/users/{id}/avatar` | `avatar_url` |
| Current User | `POST /auth/me/avatar` | `DELETE /auth/me/avatar` | `avatar_url` |
| Tenants | `POST /tenants/{id}/logo` | `DELETE /tenants/{id}/logo` | `logo_url` |

**Total: 16 endpoints** (8 upload + 8 delete)

---

## Common Request/Response Patterns

### Upload Request

All upload endpoints use **multipart/form-data** with a single file field named `file`:

```http
POST /api/v1/admin/articles/{article_id}/cover-image
Authorization: Bearer {access_token}
Content-Type: multipart/form-data

file: [binary image data]
```

### Upload Response

Upload endpoints return the **updated entity** with the new image URL:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "cover_image_url": "https://s3.example.com/tenant-id/articles/550e8400-e29b-41d4-a716-446655440000.jpg",
  "status": "draft",
  "reading_time_minutes": 5,
  "version": 2,
  ...
}
```

### Delete Request

```http
DELETE /api/v1/admin/articles/{article_id}/cover-image
Authorization: Bearer {access_token}
```

### Delete Response

Delete endpoints return **204 No Content** on success.

---

## Error Responses

### 400 Bad Request - Invalid File Type

```json
{
  "type": "https://httpstatuses.com/400",
  "title": "Bad Request",
  "status": 400,
  "detail": "Invalid file type: application/pdf. Allowed types: image/gif, image/jpeg, image/png, image/webp"
}
```

### 400 Bad Request - File Too Large

```json
{
  "type": "https://httpstatuses.com/400",
  "title": "Bad Request",
  "status": 400,
  "detail": "File too large: 15.2MB. Maximum size: 10MB"
}
```

### 404 Not Found - Entity Not Found

```json
{
  "type": "https://httpstatuses.com/404",
  "title": "Not Found",
  "status": 404,
  "detail": "Article with id '550e8400-e29b-41d4-a716-446655440000' not found"
}
```

### 403 Forbidden - Permission Denied

```json
{
  "type": "https://httpstatuses.com/403",
  "title": "Forbidden",
  "status": 403,
  "detail": "Permission 'articles:update' required"
}
```

---

## Endpoint Details

### Articles - Cover Image

#### Upload Cover Image

```http
POST /api/v1/admin/articles/{article_id}/cover-image
```

**Permission Required**: `articles:update`

**Request**:
```
Content-Type: multipart/form-data
file: [image binary]
```

**Response**: `200 OK` with `ArticleResponse`

**Example (JavaScript/fetch)**:
```javascript
const formData = new FormData();
formData.append('file', imageFile);

const response = await fetch(`/api/v1/admin/articles/${articleId}/cover-image`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
  },
  body: formData,
});

const article = await response.json();
console.log(article.cover_image_url);
```

#### Delete Cover Image

```http
DELETE /api/v1/admin/articles/{article_id}/cover-image
```

**Permission Required**: `articles:update`

**Response**: `204 No Content`

---

### Cases - Cover Image

#### Upload Cover Image

```http
POST /api/v1/admin/cases/{case_id}/cover-image
```

**Permission Required**: `cases:update`

**Response**: `200 OK` with `CaseResponse`

#### Delete Cover Image

```http
DELETE /api/v1/admin/cases/{case_id}/cover-image
```

**Permission Required**: `cases:update`

**Response**: `204 No Content`

---

### Services - Image

#### Upload Image

```http
POST /api/v1/admin/services/{service_id}/image
```

**Permission Required**: `services:update`

**Response**: `200 OK` with `ServiceResponse`

#### Delete Image

```http
DELETE /api/v1/admin/services/{service_id}/image
```

**Permission Required**: `services:update`

**Response**: `204 No Content`

---

### Employees - Photo

#### Upload Photo

```http
POST /api/v1/admin/employees/{employee_id}/photo
```

**Permission Required**: `employees:update`

**Response**: `200 OK` with `EmployeeResponse`

#### Delete Photo

```http
DELETE /api/v1/admin/employees/{employee_id}/photo
```

**Permission Required**: `employees:update`

**Response**: `204 No Content`

---

### Reviews - Author Photo

#### Upload Author Photo

```http
POST /api/v1/admin/reviews/{review_id}/author-photo
```

**Permission Required**: `reviews:update`

**Response**: `200 OK` with `ReviewResponse`

#### Delete Author Photo

```http
DELETE /api/v1/admin/reviews/{review_id}/author-photo
```

**Permission Required**: `reviews:update`

**Response**: `204 No Content`

---

### Users - Avatar (Admin)

#### Upload User Avatar

```http
POST /api/v1/auth/users/{user_id}/avatar
```

**Permission Required**: `users:update`

**Response**: `200 OK` with `UserResponse`

#### Delete User Avatar

```http
DELETE /api/v1/auth/users/{user_id}/avatar
```

**Permission Required**: `users:update`

**Response**: `204 No Content`

---

### Current User - My Avatar

#### Upload My Avatar

```http
POST /api/v1/auth/me/avatar
```

**Permission Required**: Authenticated user (no special permission)

**Response**: `200 OK` with `MeResponse`

#### Delete My Avatar

```http
DELETE /api/v1/auth/me/avatar
```

**Permission Required**: Authenticated user (no special permission)

**Response**: `204 No Content`

---

### Tenants - Logo

#### Upload Logo

```http
POST /api/v1/tenants/{tenant_id}/logo
```

**Permission Required**: Tenant admin (platform-level)

**Response**: `200 OK` with `TenantResponse`

#### Delete Logo

```http
DELETE /api/v1/tenants/{tenant_id}/logo
```

**Permission Required**: Tenant admin (platform-level)

**Response**: `204 No Content`

---

## Frontend Integration Guide

### Workflow: Creating an Entity with Image

Since images are uploaded via separate endpoints, the workflow for creating an entity with an image is:

1. **Create the entity** (POST) without image
2. **Upload the image** (POST `/{id}/image`) using the returned entity ID
3. **Display the updated entity** with the image URL

```javascript
// Step 1: Create article
const article = await createArticle({
  status: 'draft',
  locales: [{ locale: 'en', title: 'My Article', slug: 'my-article', content: '...' }],
});

// Step 2: Upload cover image
if (coverImageFile) {
  const formData = new FormData();
  formData.append('file', coverImageFile);
  
  const updatedArticle = await uploadArticleCoverImage(article.id, formData);
  article.cover_image_url = updatedArticle.cover_image_url;
}
```

### Workflow: Updating an Entity's Image

To replace an existing image:

```javascript
// Simply upload a new image - the old one is automatically deleted
const formData = new FormData();
formData.append('file', newImageFile);

await uploadArticleCoverImage(articleId, formData);
```

### Workflow: Removing an Entity's Image

```javascript
await deleteArticleCoverImage(articleId);
```

### React Component Example

```tsx
import { useState } from 'react';

interface ImageUploadProps {
  entityId: string;
  currentImageUrl: string | null;
  uploadEndpoint: string;
  deleteEndpoint: string;
  onImageChange: (url: string | null) => void;
}

function ImageUpload({ 
  entityId, 
  currentImageUrl, 
  uploadEndpoint, 
  deleteEndpoint,
  onImageChange 
}: ImageUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleUpload = async (file: File) => {
    // Validate file type
    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
    if (!allowedTypes.includes(file.type)) {
      setError('Invalid file type. Allowed: JPEG, PNG, WebP, GIF');
      return;
    }

    // Validate file size (10MB)
    if (file.size > 10 * 1024 * 1024) {
      setError('File too large. Maximum size: 10MB');
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(uploadEndpoint.replace('{id}', entityId), {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${getToken()}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Upload failed');
      }

      const entity = await response.json();
      onImageChange(entity.cover_image_url || entity.image_url || entity.photo_url || entity.avatar_url);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async () => {
    setUploading(true);
    setError(null);

    try {
      const response = await fetch(deleteEndpoint.replace('{id}', entityId), {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${getToken()}`,
        },
      });

      if (!response.ok && response.status !== 204) {
        throw new Error('Delete failed');
      }

      onImageChange(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="image-upload">
      {currentImageUrl && (
        <div className="current-image">
          <img src={currentImageUrl} alt="Current" />
          <button onClick={handleDelete} disabled={uploading}>
            Remove
          </button>
        </div>
      )}
      
      <input
        type="file"
        accept="image/jpeg,image/png,image/webp,image/gif"
        onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])}
        disabled={uploading}
      />
      
      {uploading && <div className="loading">Uploading...</div>}
      {error && <div className="error">{error}</div>}
    </div>
  );
}
```

### Image Preview Before Upload

```typescript
function previewImage(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

// Usage
const preview = await previewImage(file);
// Set preview as image src while uploading
```

### Client-Side Validation

```typescript
interface ValidationResult {
  valid: boolean;
  error?: string;
}

function validateImageFile(file: File): ValidationResult {
  const allowedTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
  const maxSize = 10 * 1024 * 1024; // 10MB

  if (!allowedTypes.includes(file.type)) {
    return {
      valid: false,
      error: `Invalid file type: ${file.type}. Allowed: JPEG, PNG, WebP, GIF`,
    };
  }

  if (file.size > maxSize) {
    return {
      valid: false,
      error: `File too large: ${(file.size / (1024 * 1024)).toFixed(1)}MB. Maximum: 10MB`,
    };
  }

  return { valid: true };
}
```

---

## API Service Functions (TypeScript)

```typescript
// api/images.ts

const API_BASE = '/api/v1';

interface UploadResult<T> {
  success: boolean;
  data?: T;
  error?: string;
}

async function uploadImage<T>(
  endpoint: string,
  file: File,
  token: string
): Promise<UploadResult<T>> {
  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      return { success: false, error: error.detail || 'Upload failed' };
    }

    const data = await response.json();
    return { success: true, data };
  } catch (err) {
    return { success: false, error: err.message };
  }
}

async function deleteImage(endpoint: string, token: string): Promise<UploadResult<void>> {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok && response.status !== 204) {
      return { success: false, error: 'Delete failed' };
    }

    return { success: true };
  } catch (err) {
    return { success: false, error: err.message };
  }
}

// Article images
export const uploadArticleCoverImage = (id: string, file: File, token: string) =>
  uploadImage<Article>(`/admin/articles/${id}/cover-image`, file, token);

export const deleteArticleCoverImage = (id: string, token: string) =>
  deleteImage(`/admin/articles/${id}/cover-image`, token);

// Case images
export const uploadCaseCoverImage = (id: string, file: File, token: string) =>
  uploadImage<Case>(`/admin/cases/${id}/cover-image`, file, token);

export const deleteCaseCoverImage = (id: string, token: string) =>
  deleteImage(`/admin/cases/${id}/cover-image`, token);

// Service images
export const uploadServiceImage = (id: string, file: File, token: string) =>
  uploadImage<Service>(`/admin/services/${id}/image`, file, token);

export const deleteServiceImage = (id: string, token: string) =>
  deleteImage(`/admin/services/${id}/image`, token);

// Employee photos
export const uploadEmployeePhoto = (id: string, file: File, token: string) =>
  uploadImage<Employee>(`/admin/employees/${id}/photo`, file, token);

export const deleteEmployeePhoto = (id: string, token: string) =>
  deleteImage(`/admin/employees/${id}/photo`, token);

// Review author photos
export const uploadReviewAuthorPhoto = (id: string, file: File, token: string) =>
  uploadImage<Review>(`/admin/reviews/${id}/author-photo`, file, token);

export const deleteReviewAuthorPhoto = (id: string, token: string) =>
  deleteImage(`/admin/reviews/${id}/author-photo`, token);

// User avatars (admin)
export const uploadUserAvatar = (id: string, file: File, token: string) =>
  uploadImage<User>(`/auth/users/${id}/avatar`, file, token);

export const deleteUserAvatar = (id: string, token: string) =>
  deleteImage(`/auth/users/${id}/avatar`, token);

// My avatar
export const uploadMyAvatar = (file: File, token: string) =>
  uploadImage<MeResponse>('/auth/me/avatar', file, token);

export const deleteMyAvatar = (token: string) =>
  deleteImage('/auth/me/avatar', token);

// Tenant logo
export const uploadTenantLogo = (id: string, file: File, token: string) =>
  uploadImage<Tenant>(`/tenants/${id}/logo`, file, token);

export const deleteTenantLogo = (id: string, token: string) =>
  deleteImage(`/tenants/${id}/logo`, token);
```

---

## Migration Notes

### Breaking Changes

If you were previously sending `cover_image_url`, `image_url`, `photo_url`, `author_photo_url`, `avatar_url`, or `logo_url` in POST/PATCH requests, you must update your code:

**Before (deprecated)**:
```json
POST /api/v1/admin/articles
{
  "status": "draft",
  "cover_image_url": "https://example.com/image.jpg",
  "locales": [...]
}
```

**After (new approach)**:
```javascript
// Step 1: Create without image
const article = await fetch('/api/v1/admin/articles', {
  method: 'POST',
  body: JSON.stringify({
    status: 'draft',
    locales: [...]
  })
});

// Step 2: Upload image separately
const formData = new FormData();
formData.append('file', imageFile);
await fetch(`/api/v1/admin/articles/${article.id}/cover-image`, {
  method: 'POST',
  body: formData
});
```

### Response Schema Changes

The response schemas remain the same - `cover_image_url`, `image_url`, etc. are still present in GET responses and upload responses.

---

## Best Practices

1. **Always validate files client-side** before uploading to provide immediate feedback
2. **Show upload progress** for large images using `XMLHttpRequest` or fetch with `ReadableStream`
3. **Implement optimistic UI updates** by showing a preview immediately
4. **Handle upload failures gracefully** with retry mechanisms
5. **Cache uploaded image URLs** to avoid re-fetching entities after upload

---

## Changelog

### v1.0.0 (2026-01-15)
- Initial release of image upload API
- Added 16 new endpoints for image management
- Removed `*_url` fields from Create/Update schemas
- Added frontend integration guide and TypeScript examples

