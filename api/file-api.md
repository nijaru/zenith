# File Upload API

Zenith provides a comprehensive file upload API that makes handling file uploads secure, efficient, and developer-friendly. The API includes validation, automatic storage, type detection, and convenient helper methods.

## Quick Start

```python
from zenith import Zenith, File, IMAGE_TYPES, MB

app = Zenith()

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(
        max_size="10MB",
        allowed_types=IMAGE_TYPES
    )
):
    return {"filename": file.filename, "size": file.size}
```

## File Dependency

The `File` dependency provides automatic validation and convenient file handling.

### Basic Usage

```python
from zenith import File, UploadFile

@app.post("/upload")
async def upload_file(file: UploadFile = File()):
    # File is automatically validated
    return {"filename": file.filename}
```

### Validation Parameters

```python
@app.post("/upload")
async def upload_file(
    file: UploadFile = File(
        max_size="5MB",                    # Size limit (supports KB, MB, GB)
        allowed_types=IMAGE_TYPES,         # MIME type validation
        allowed_extensions=[".jpg", ".png"] # Extension validation
    )
):
    return {"filename": file.filename}
```

### Size Constants

Zenith provides convenient size constants:

```python
from zenith import KB, MB, GB

file = File(max_size=5*MB)        # 5 megabytes
file = File(max_size=512*KB)      # 512 kilobytes
file = File(max_size=2*GB)        # 2 gigabytes
```

### File Type Constants

Pre-defined MIME type collections for common validation scenarios:

```python
from zenith import IMAGE_TYPES, DOCUMENT_TYPES, AUDIO_TYPES, VIDEO_TYPES, ARCHIVE_TYPES

# Image files
@app.post("/upload/image")
async def upload_image(file: UploadFile = File(allowed_types=IMAGE_TYPES)):
    pass

# Document files
@app.post("/upload/doc")
async def upload_document(file: UploadFile = File(allowed_types=DOCUMENT_TYPES)):
    pass

# Multiple types
@app.post("/upload/media")
async def upload_media(file: UploadFile = File(allowed_types=IMAGE_TYPES + VIDEO_TYPES)):
    pass
```

#### Available Type Constants

| Constant | MIME Types |
|----------|------------|
| `IMAGE_TYPES` | `image/jpeg`, `image/png`, `image/gif`, `image/webp`, `image/bmp`, `image/tiff`, `image/svg+xml` |
| `DOCUMENT_TYPES` | `application/pdf`, `text/plain`, `text/markdown`, MS Office formats |
| `AUDIO_TYPES` | `audio/mpeg`, `audio/mp3`, `audio/wav`, `audio/ogg`, `audio/aac`, `audio/flac` |
| `VIDEO_TYPES` | `video/mp4`, `video/mpeg`, `video/quicktime`, `video/webm`, `video/ogg` |
| `ARCHIVE_TYPES` | `application/zip`, `application/x-rar-compressed`, `application/x-tar`, `application/gzip` |

## Enhanced UploadedFile API

The `UploadedFile` class provides enhanced functionality over standard file uploads.

### File Information

```python
from zenith import UploadedFile

# File properties
file.filename              # Safe generated filename
file.original_filename     # Original uploaded filename
file.content_type         # MIME type
file.size_bytes          # File size in bytes
file.file_path           # Path where file is stored
file.url                 # Optional URL to access file
```

### Type Detection Methods

```python
# Quick type checks
if file.is_image():
    process_image(file)
elif file.is_audio():
    process_audio(file)
elif file.is_video():
    process_video(file)
elif file.is_pdf():
    process_pdf(file)

# Extension helper
extension = file.get_extension()  # Returns ".jpg", ".pdf", etc.
```

### File Operations

```python
# Read file content
content = await file.read()

# Copy file to new location
backup_path = await file.copy_to("/backups/important.pdf")

# Move file to new location
final_path = await file.move_to("/final/location.pdf")
```

## File Upload Configuration

### FileUploadConfig

Configure global upload behavior:

```python
from zenith.web.files import FileUploadConfig, FileUploader
from pathlib import Path

config = FileUploadConfig(
    max_file_size_bytes=50 * 1024 * 1024,     # 50MB
    allowed_extensions=[".jpg", ".png", ".pdf"],
    allowed_mime_types=IMAGE_TYPES + ["application/pdf"],
    upload_dir=Path("/var/uploads"),          # Custom upload directory
    preserve_filename=True,                   # Keep original names
    create_subdirs=True                       # Create date-based subdirs
)

uploader = FileUploader(config)
```

### Custom Upload Directory

```python
from pathlib import Path

# Custom directory structure
config = FileUploadConfig(
    upload_dir=Path("/app/user-uploads"),
    create_subdirs=True,  # Creates /app/user-uploads/2024/03/15/
    preserve_filename=False  # Generate UUID filenames
)
```

## Multiple File Uploads

```python
@app.post("/upload/multiple")
async def upload_multiple(
    files: list[UploadFile] = File(
        max_size="10MB",
        allowed_types=IMAGE_TYPES + DOCUMENT_TYPES
    )
):
    results = []
    for file in files:
        # Process each file
        content = await file.read()
        results.append({
            "filename": file.filename,
            "size": len(content),
            "type": file.content_type
        })
    return results
```

## Advanced Usage Examples

### Profile Upload with Mixed Form Data

```python
from pydantic import BaseModel

class ProfileUpdate(BaseModel):
    username: str
    bio: str | None = None

@app.post("/profile/update")
async def update_profile(
    profile: ProfileUpdate,
    avatar: UploadFile = File(
        max_size="2MB",
        allowed_types=IMAGE_TYPES,
        field_name="avatar"
    )
):
    # Save avatar with username-based filename
    avatar_path = await avatar.move_to(f"/avatars/{profile.username}.jpg")

    return {
        "username": profile.username,
        "bio": profile.bio,
        "avatar_url": f"/static/avatars/{profile.username}.jpg"
    }
```

### File Processing Pipeline

```python
@app.post("/upload/process")
async def upload_and_process(
    file: UploadedFile = File(
        max_size="100MB",
        allowed_types=VIDEO_TYPES + AUDIO_TYPES
    )
):
    # Determine processing based on file type
    if file.is_video():
        # Video processing
        thumbnail = await generate_thumbnail(file.file_path)
        duration = await get_video_duration(file.file_path)

        return {
            "type": "video",
            "filename": file.filename,
            "duration": duration,
            "thumbnail_url": thumbnail
        }

    elif file.is_audio():
        # Audio processing
        metadata = await extract_audio_metadata(file.file_path)
        waveform = await generate_waveform(file.file_path)

        return {
            "type": "audio",
            "filename": file.filename,
            "metadata": metadata,
            "waveform_url": waveform
        }
```

### Secure File Storage

```python
import secrets
from pathlib import Path

@app.post("/secure-upload")
async def secure_upload(
    file: UploadedFile = File(
        max_size="10MB",
        allowed_types=DOCUMENT_TYPES
    )
):
    # Generate secure filename
    secure_id = secrets.token_urlsafe(32)
    extension = file.get_extension()
    secure_filename = f"{secure_id}{extension}"

    # Store in secure location
    secure_path = await file.move_to(f"/secure-storage/{secure_filename}")

    # Return access token instead of direct path
    access_token = secrets.token_urlsafe(64)

    # Store mapping in database
    await store_file_mapping(secure_filename, access_token, file.original_filename)

    return {
        "access_token": access_token,
        "original_filename": file.original_filename,
        "size": file.size_bytes
    }
```

### File Validation with Custom Logic

```python
from zenith.web.files import FileUploadError

@app.post("/upload/validated")
async def upload_with_validation(
    file: UploadedFile = File(max_size="5MB", allowed_types=IMAGE_TYPES)
):
    # Additional custom validation
    if file.size_bytes < 1024:  # Minimum 1KB
        raise FileUploadError("File too small - minimum 1KB required")

    # Check image dimensions (example)
    if file.is_image():
        width, height = await get_image_dimensions(file.file_path)
        if width < 100 or height < 100:
            raise FileUploadError("Image too small - minimum 100x100 pixels")

    return {
        "filename": file.filename,
        "size": file.size_bytes,
        "valid": True
    }
```

## Error Handling

File upload errors are automatically converted to proper HTTP responses:

```python
from zenith.web.files import FileUploadError

try:
    # File operations
    pass
except FileUploadError as e:
    # Automatically returns 400 Bad Request with error message
    raise e
```

### Custom Error Responses

```python
from zenith import HTTPException

@app.post("/upload")
async def upload_file(file: UploadFile = File(max_size="1MB")):
    try:
        content = await file.read()
        # Process file...
        return {"status": "success"}
    except FileUploadError as e:
        # Custom error response
        raise HTTPException(
            status_code=413,  # Payload Too Large
            detail=f"Upload failed: {str(e)}"
        )
```

## File Serving

After uploading, serve files securely:

```python
from starlette.responses import FileResponse

@app.get("/files/{filename}")
async def get_file(filename: str):
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream"
    )
```

## Testing File Uploads

Test file uploads in your test suite:

```python
from zenith.testing import TestClient
import io

async def test_file_upload():
    async with TestClient(app) as client:
        # Create test file
        test_file = io.BytesIO(b"test file content")

        response = await client.post(
            "/upload",
            files={"file": ("test.txt", test_file, "text/plain")}
        )

        assert response.status_code == 200
        assert response.json()["filename"] == "test.txt"
```

## Best Practices

### Security

1. **Always validate file types** - Use `allowed_types` and `allowed_extensions`
2. **Set reasonable size limits** - Prevent DoS attacks with large files
3. **Generate secure filenames** - Don't trust user-provided filenames
4. **Store files outside web root** - Prevent direct access to uploaded files
5. **Scan for malware** - In production, integrate virus scanning

### Performance

1. **Stream large files** - Don't load entire file into memory
2. **Use async operations** - All file operations are async
3. **Implement file cleanup** - Remove old/unused files regularly
4. **Consider cloud storage** - For scalability, use S3, GCS, etc.

### Storage

```python
# Good: Stream processing for large files
async def process_large_file(file: UploadedFile):
    async with aiofiles.open(file.file_path, 'rb') as f:
        async for chunk in f:
            await process_chunk(chunk)

# Avoid: Loading entire file into memory
content = await file.read()  # Only for small files
```

## Migration from Other Frameworks

### From FastAPI

```python
# FastAPI
from fastapi import UploadFile, File

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    return {"filename": file.filename}

# Zenith (enhanced)
from zenith import UploadFile, File, IMAGE_TYPES

@app.post("/upload")
async def upload(file: UploadFile = File(max_size="10MB", allowed_types=IMAGE_TYPES)):
    return {"filename": file.filename}
```

### From Flask

```python
# Flask
from flask import request
from werkzeug.utils import secure_filename

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    filename = secure_filename(file.filename)
    file.save(filename)
    return {"filename": filename}

# Zenith
from zenith import File, UploadFile

@app.post("/upload")
async def upload(file: UploadFile = File()):
    # Automatic security and validation
    return {"filename": file.filename}
```

The Zenith File API provides automatic security, validation, and enhanced functionality that eliminates common file upload vulnerabilities and developer pain points.