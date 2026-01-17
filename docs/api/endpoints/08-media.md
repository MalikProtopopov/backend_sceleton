# Media Library API

> File uploads, asset management, and S3 integration

---

## Overview

The Media Library manages uploaded files including images, documents, and other assets. Features include:
- Direct S3 upload via presigned URLs
- File metadata management
- Folder organization
- Image-only filtering
- Soft delete with optional hard delete

---

## Upload Flow

```
┌─────────────┐      1. Request Upload URL      ┌─────────────┐
│   Frontend  │ ─────────────────────────────────▶│   Backend   │
│             │   POST /files/upload-url          │             │
│             │                                   │             │
│             │◀───────────────────────────────── │             │
│             │   { upload_url, file_url, s3_key }│             │
└──────┬──────┘                                   └─────────────┘
       │
       │ 2. Upload directly to S3
       │    PUT {upload_url}
       │    Body: file binary
       ▼
┌─────────────┐
│     S3      │
└──────┬──────┘
       │
       │ 3. Register file in database
       ▼
┌─────────────┐      POST /files                 ┌─────────────┐
│   Frontend  │ ─────────────────────────────────▶│   Backend   │
│             │   { s3_key, original_filename,   │             │
│             │     content_type, file_size,     │             │
│             │     alt_text, folder }           │             │
│             │◀───────────────────────────────── │             │
│             │   FileAsset object               │             │
└─────────────┘                                   └─────────────┘
```

---

## Data Model

```json
{
  "id": "file-uuid",
  "tenant_id": "tenant-uuid",
  "s3_key": "tenants/tenant-uuid/uploads/2026/01/image.jpg",
  "original_filename": "photo.jpg",
  "content_type": "image/jpeg",
  "file_size": 245678,
  "file_url": "https://cdn.example.com/uploads/2026/01/image.jpg",
  "alt_text": "Team meeting photo",
  "folder": "team",
  "width": 1920,
  "height": 1080,
  "created_at": "2026-01-14T10:00:00Z",
  "updated_at": "2026-01-14T10:00:00Z"
}
```

---

## Admin Endpoints

### GET /api/v1/admin/files

List all files with pagination and filters.

**Required Permission:** `settings:read`

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number |
| `pageSize` | integer | 20 | Items per page |
| `folder` | string | - | Filter by folder name |
| `imagesOnly` | boolean | false | Only return images |

**Example Request:**
```bash
GET /api/v1/admin/files?folder=team&imagesOnly=true
Authorization: Bearer {token}
```

**Success Response (200):**
```json
{
  "items": [
    {
      "id": "file-uuid-1",
      "tenant_id": "tenant-uuid",
      "s3_key": "tenants/tenant-uuid/uploads/2026/01/photo1.jpg",
      "original_filename": "team-photo.jpg",
      "content_type": "image/jpeg",
      "file_size": 245678,
      "file_url": "https://cdn.example.com/uploads/2026/01/photo1.jpg",
      "alt_text": "Team photo",
      "folder": "team",
      "width": 1920,
      "height": 1080,
      "created_at": "2026-01-14T10:00:00Z",
      "updated_at": "2026-01-14T10:00:00Z"
    }
  ],
  "total": 45,
  "page": 1,
  "page_size": 20
}
```

---

### POST /api/v1/admin/files/upload-url

Get presigned URL for direct S3 upload.

**Required Permission:** `settings:update`

**Request Body:**
```json
{
  "filename": "team-photo.jpg",
  "content_type": "image/jpeg",
  "folder": "team"
}
```

**Field Validation:**
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `filename` | string | Yes | Original filename |
| `content_type` | string | Yes | MIME type |
| `folder` | string | No | Folder path |

**Success Response (200):**
```json
{
  "upload_url": "https://s3.amazonaws.com/bucket/path?X-Amz-Signature=...",
  "file_url": "https://cdn.example.com/uploads/2026/01/abc123-team-photo.jpg",
  "s3_key": "tenants/tenant-uuid/uploads/2026/01/abc123-team-photo.jpg",
  "expires_in": 3600
}
```

**Frontend Usage:**
```javascript
// 1. Get upload URL
const { data: uploadData } = await api.post('/admin/files/upload-url', {
  filename: file.name,
  content_type: file.type,
  folder: 'team'
})

// 2. Upload to S3
await fetch(uploadData.upload_url, {
  method: 'PUT',
  body: file,
  headers: {
    'Content-Type': file.type
  }
})

// 3. Register in database
const { data: fileAsset } = await api.post('/admin/files', {
  s3_key: uploadData.s3_key,
  original_filename: file.name,
  content_type: file.type,
  file_size: file.size,
  folder: 'team'
})
```

---

### POST /api/v1/admin/files

Register uploaded file in database.

**Required Permission:** `settings:update`

**Request Body:**
```json
{
  "s3_key": "tenants/tenant-uuid/uploads/2026/01/abc123-team-photo.jpg",
  "original_filename": "team-photo.jpg",
  "content_type": "image/jpeg",
  "file_size": 245678,
  "alt_text": "Team meeting photo",
  "folder": "team",
  "width": 1920,
  "height": 1080
}
```

**Field Validation:**
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `s3_key` | string | Yes | S3 object key |
| `original_filename` | string | Yes | Original filename |
| `content_type` | string | Yes | MIME type |
| `file_size` | integer | Yes | Size in bytes |
| `alt_text` | string | No | Alt text for images |
| `folder` | string | No | Folder path |
| `width` | integer | No | Image width |
| `height` | integer | No | Image height |

**Success Response (201):** Created FileAsset object.

---

### GET /api/v1/admin/files/{file_id}

Get file by ID.

**Required Permission:** `settings:read`

**Success Response (200):** FileAsset object.

---

### PATCH /api/v1/admin/files/{file_id}

Update file metadata.

**Required Permission:** `settings:update`

**Request Body:**
```json
{
  "alt_text": "Updated alt text",
  "folder": "new-folder"
}
```

**Success Response (200):** Updated FileAsset object.

---

### DELETE /api/v1/admin/files/{file_id}

Delete file.

**Required Permission:** `settings:update`

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `hardDelete` | boolean | false | Permanently delete from S3 |

**Behavior:**
- Default (soft delete): Sets `deleted_at`, file remains in S3
- Hard delete: Removes from database AND S3

**Response:** `204 No Content`

---

## Frontend Integration

### Media Library Component

```jsx
const MediaLibrary = ({ onSelect, multiple = false }) => {
  const [files, setFiles] = useState([])
  const [selected, setSelected] = useState([])
  const [filters, setFilters] = useState({
    folder: '',
    imagesOnly: false
  })
  const [uploading, setUploading] = useState(false)
  
  useEffect(() => {
    loadFiles()
  }, [filters])
  
  const loadFiles = async () => {
    const params = new URLSearchParams()
    if (filters.folder) params.set('folder', filters.folder)
    if (filters.imagesOnly) params.set('imagesOnly', 'true')
    
    const { data } = await api.get(`/admin/files?${params}`)
    setFiles(data.items)
  }
  
  const handleUpload = async (fileList) => {
    setUploading(true)
    
    for (const file of fileList) {
      try {
        // Get presigned URL
        const { data: uploadData } = await api.post('/admin/files/upload-url', {
          filename: file.name,
          content_type: file.type,
          folder: filters.folder || 'uploads'
        })
        
        // Upload to S3
        await fetch(uploadData.upload_url, {
          method: 'PUT',
          body: file,
          headers: { 'Content-Type': file.type }
        })
        
        // Get image dimensions
        let width, height
        if (file.type.startsWith('image/')) {
          const dims = await getImageDimensions(file)
          width = dims.width
          height = dims.height
        }
        
        // Register in database
        await api.post('/admin/files', {
          s3_key: uploadData.s3_key,
          original_filename: file.name,
          content_type: file.type,
          file_size: file.size,
          folder: filters.folder || 'uploads',
          width,
          height
        })
      } catch (error) {
        console.error('Upload failed:', error)
      }
    }
    
    setUploading(false)
    loadFiles()
  }
  
  const handleSelect = (file) => {
    if (multiple) {
      setSelected(prev => 
        prev.includes(file.id) 
          ? prev.filter(id => id !== file.id)
          : [...prev, file.id]
      )
    } else {
      onSelect?.(file)
    }
  }
  
  const handleDelete = async (fileId) => {
    if (confirm('Delete this file?')) {
      await api.delete(`/admin/files/${fileId}`)
      loadFiles()
    }
  }
  
  return (
    <div className="media-library">
      <Toolbar>
        <UploadButton onUpload={handleUpload} loading={uploading} />
        <FolderFilter value={filters.folder} onChange={f => setFilters({...filters, folder: f})} />
        <Toggle 
          label="Images only" 
          checked={filters.imagesOnly}
          onChange={v => setFilters({...filters, imagesOnly: v})}
        />
      </Toolbar>
      
      <Grid>
        {files.map(file => (
          <FileCard 
            key={file.id}
            file={file}
            selected={selected.includes(file.id)}
            onClick={() => handleSelect(file)}
            onDelete={() => handleDelete(file.id)}
          />
        ))}
      </Grid>
      
      {multiple && selected.length > 0 && (
        <Footer>
          <Button onClick={() => onSelect?.(files.filter(f => selected.includes(f.id)))}>
            Select {selected.length} files
          </Button>
        </Footer>
      )}
    </div>
  )
}
```

### File Card Component

```jsx
const FileCard = ({ file, selected, onClick, onDelete }) => {
  const isImage = file.content_type.startsWith('image/')
  
  return (
    <Card 
      className={selected ? 'selected' : ''} 
      onClick={onClick}
    >
      {isImage ? (
        <img src={file.file_url} alt={file.alt_text || file.original_filename} />
      ) : (
        <FileIcon type={file.content_type} />
      )}
      
      <Info>
        <Filename>{file.original_filename}</Filename>
        <Size>{formatFileSize(file.file_size)}</Size>
        {isImage && <Dimensions>{file.width}×{file.height}</Dimensions>}
      </Info>
      
      <Actions>
        <CopyButton url={file.file_url} />
        <DeleteButton onClick={(e) => { e.stopPropagation(); onDelete() }} />
      </Actions>
    </Card>
  )
}

// Helper functions
const formatFileSize = (bytes) => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const getImageDimensions = (file) => {
  return new Promise((resolve) => {
    const img = new Image()
    img.onload = () => resolve({ width: img.width, height: img.height })
    img.src = URL.createObjectURL(file)
  })
}
```

### Image Picker for WYSIWYG

```jsx
const ImagePicker = ({ onSelect }) => {
  const [isOpen, setIsOpen] = useState(false)
  
  const handleSelect = (file) => {
    onSelect({
      src: file.file_url,
      alt: file.alt_text || file.original_filename,
      width: file.width,
      height: file.height
    })
    setIsOpen(false)
  }
  
  return (
    <>
      <Button onClick={() => setIsOpen(true)}>Insert Image</Button>
      
      <Modal isOpen={isOpen} onClose={() => setIsOpen(false)}>
        <MediaLibrary 
          onSelect={handleSelect} 
          filters={{ imagesOnly: true }}
        />
      </Modal>
    </>
  )
}
```

### Drag & Drop Upload Zone

```jsx
const DropZone = ({ onUpload }) => {
  const [isDragging, setIsDragging] = useState(false)
  
  const handleDrop = (e) => {
    e.preventDefault()
    setIsDragging(false)
    
    const files = Array.from(e.dataTransfer.files)
    onUpload(files)
  }
  
  return (
    <div
      className={`drop-zone ${isDragging ? 'dragging' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
    >
      <Icon name="upload" />
      <p>Drag files here or click to upload</p>
      <input 
        type="file" 
        multiple 
        onChange={(e) => onUpload(Array.from(e.target.files))}
      />
    </div>
  )
}
```

---

## Supported File Types

| Category | MIME Types | Max Size |
|----------|------------|----------|
| Images | `image/jpeg`, `image/png`, `image/gif`, `image/webp`, `image/svg+xml` | 10 MB |
| Documents | `application/pdf`, `application/msword`, `application/vnd.openxmlformats-officedocument.*` | 20 MB |
| Other | Various | 50 MB |

---

## Folder Structure

Recommended folder organization:
- `articles/` - Article cover images
- `team/` - Employee photos
- `services/` - Service images
- `cases/` - Case study images
- `documents/` - PDF and other documents
- `uploads/` - General uploads

