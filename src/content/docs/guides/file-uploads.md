---
title: File Uploads
description: Enhanced file upload handling with convenience methods and type detection
---

# File Uploads

Zenith provides enhanced file upload handling with improved UX, automatic validation, and convenient methods for common operations.

## 🆕 Enhanced UploadedFile API

The new `UploadedFile` class provides Starlette-compatible methods plus convenient helpers based on production app feedback.

### Basic File Upload

```python
from zenith import Zenith, File
from zenith.web.files import UploadedFile

app = Zenith()

@app.post("/upload")
async def upload_file(file: UploadedFile = File()) -> dict:
    return {
        "filename": file.filename,
        "original": file.original_filename,
        "size": file.size_bytes,
        "type": file.content_type
    }
```

### File Upload with Validation

```python
@app.post("/upload/image")
async def upload_image(file: UploadedFile = File(
    max_size=5 * 1024 * 1024,  # 5MB
    allowed_types=["image/jpeg", "image/png", "image/gif"]
)) -> dict:
    # File is automatically validated
    return {
        "filename": file.filename,
        "size": file.size_bytes,
        "type": file.content_type
    }
```

## File Type Detection

Convenient methods for checking file types:

```python
@app.post("/upload/smart")
async def upload_smart(file: UploadedFile = File()) -> dict:
    file_type = "other"

    if file.is_image():
        file_type = "image"
    elif file.is_audio():
        file_type = "audio"
    elif file.is_video():
        file_type = "video"
    elif file.is_pdf():
        file_type = "pdf"

    extension = file.get_extension()  # ".jpg", ".mp3", etc.

    return {
        "filename": file.filename,
        "type": file_type,
        "extension": extension,
        "size": file.size_bytes
    }
```

## File Operations

### Move Files

The `move_to()` method automatically creates directories and updates the file path:

```python
import uuid
from pathlib import Path

@app.post("/upload/save")
async def upload_and_save(file: UploadedFile = File()) -> dict:
    # Generate unique filename
    file_id = str(uuid.uuid4())
    extension = file.get_extension()
    new_filename = f"{file_id}{extension}"

    # Move to permanent location (creates directories automatically)
    final_path = await file.move_to(f"/uploads/{new_filename}")

    return {
        "saved_to": str(final_path),
        "original_name": file.original_filename,
        "url": f"/files/{new_filename}"
    }
```

### Copy Files

Keep original and create copies:

```python
@app.post("/upload/process")
async def upload_and_process(file: UploadedFile = File()) -> dict:
    # Save original
    original_path = await file.copy_to(f"/uploads/originals/{file.filename}")

    # Create processed copy for thumbnails, etc.
    if file.is_image():
        thumb_path = await file.copy_to(f"/uploads/thumbnails/{file.filename}")
        # Process thumbnail here...

    return {
        "original": str(original_path),
        "thumbnail": str(thumb_path) if file.is_image() else None
    }
```

## Read File Content

Starlette-compatible `read()` method:

```python
@app.post("/upload/analyze")
async def upload_and_analyze(file: UploadedFile = File()) -> dict:
    # Read file content
    content = await file.read()

    analysis = {
        "size": len(content),
        "first_bytes": content[:10].hex() if content else "",
    }

    if file.is_image():
        # Analyze image
        analysis["type"] = "image"
    elif file.content_type == "text/plain":
        # Analyze text
        analysis["type"] = "text"
        analysis["preview"] = content.decode('utf-8')[:100]

    return analysis
```

## Production Patterns

### Secure File Handling

```python
import uuid
from pathlib import Path

UPLOAD_DIR = Path("uploads")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".pdf", ".doc", ".docx"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

@app.post("/upload/secure")
async def secure_upload(file: UploadedFile = File(
    max_size=MAX_FILE_SIZE,
    allowed_types=[
        "image/jpeg", "image/png", "image/gif",
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]
)) -> dict:
    # Additional extension check
    extension = file.get_extension().lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"File type {extension} not allowed")

    # Generate secure filename
    file_id = str(uuid.uuid4())
    secure_filename = f"{file_id}{extension}"

    # Organize by date and type
    from datetime import datetime
    date_path = datetime.now().strftime("%Y/%m/%d")

    if file.is_image():
        folder = "images"
    elif file.is_pdf():
        folder = "documents"
    else:
        folder = "files"

    final_path = await file.move_to(UPLOAD_DIR / folder / date_path / secure_filename)

    return {
        "file_id": file_id,
        "original_name": file.original_filename,
        "saved_to": str(final_path),
        "url": f"/files/{folder}/{date_path}/{secure_filename}",
        "type": folder
    }
```

### Multiple File Upload

```python
@app.post("/upload/multiple")
async def upload_multiple(files: list[UploadedFile] = File()) -> dict:
    results = []

    for file in files:
        # Process each file
        file_id = str(uuid.uuid4())
        extension = file.get_extension()
        filename = f"{file_id}{extension}"

        final_path = await file.move_to(f"/uploads/{filename}")

        results.append({
            "original": file.original_filename,
            "saved": filename,
            "size": file.size_bytes,
            "type": "image" if file.is_image() else "other",
            "url": f"/files/{filename}"
        })

    return {
        "uploaded": len(results),
        "files": results
    }
```

### Form Data with Files

```python
from pydantic import BaseModel

class ProfileUpdate(BaseModel):
    name: str
    bio: str | None = None
    website: str | None = None

@app.post("/profile/update")
async def update_profile(
    # Form data
    name: str,
    bio: str | None = None,
    website: str | None = None,
    # File upload
    avatar: UploadedFile = File()
) -> dict:
    # Validate avatar
    if not avatar.is_image():
        raise HTTPException(400, "Avatar must be an image")

    # Save avatar
    avatar_id = str(uuid.uuid4())
    extension = avatar.get_extension()
    avatar_filename = f"avatar_{avatar_id}{extension}"

    avatar_path = await avatar.move_to(f"/uploads/avatars/{avatar_filename}")

    return {
        "profile": {
            "name": name,
            "bio": bio,
            "website": website
        },
        "avatar": {
            "filename": avatar_filename,
            "url": f"/files/avatars/{avatar_filename}",
            "size": avatar.size_bytes
        }
    }
```

## Serve Uploaded Files

```python
from starlette.responses import FileResponse

@app.get("/files/{filename}")
async def serve_file(filename: str):
    file_path = UPLOAD_DIR / filename

    if not file_path.exists():
        raise HTTPException(404, "File not found")

    return FileResponse(file_path)

@app.get("/files/{folder}/{date_path:path}/{filename}")
async def serve_organized_file(folder: str, date_path: str, filename: str):
    file_path = UPLOAD_DIR / folder / date_path / filename

    if not file_path.exists():
        raise HTTPException(404, "File not found")

    return FileResponse(file_path)
```

## Error Handling

```python
from zenith.exceptions import HTTPException

@app.post("/upload/robust")
async def robust_upload(file: UploadedFile = File()) -> dict:
    try:
        # Validate file type
        if not (file.is_image() or file.is_pdf()):
            raise HTTPException(400, "Only images and PDFs allowed")

        # Check file size
        if file.size_bytes > 5 * 1024 * 1024:
            raise HTTPException(413, "File too large (max 5MB)")

        # Save file
        file_id = str(uuid.uuid4())
        extension = file.get_extension()
        filename = f"{file_id}{extension}"

        final_path = await file.move_to(f"/uploads/{filename}")

        return {
            "success": True,
            "file_id": file_id,
            "filename": filename,
            "size": file.size_bytes
        }

    except Exception as e:
        # Log error for debugging
        print(f"Upload error: {e}")
        raise HTTPException(500, "Upload failed")
```

## Testing File Uploads

```python
import pytest
from zenith.testing import TestClient

@pytest.mark.asyncio
async def test_file_upload():
    async with TestClient(app) as client:
        # Create test file
        test_content = b"test file content"

        response = await client.post(
            "/upload",
            files={"file": ("test.txt", test_content, "text/plain")}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.txt"
        assert data["size"] == len(test_content)

@pytest.mark.asyncio
async def test_image_upload():
    async with TestClient(app) as client:
        # Mock image file
        image_content = b"fake image data"

        response = await client.post(
            "/upload/image",
            files={"file": ("test.jpg", image_content, "image/jpeg")}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "image"
```

## Migration from Standard UploadFile

If you're currently using Starlette's `UploadFile`, upgrading is easy:

```python
# Old way
from starlette.datastructures import UploadFile

@app.post("/upload")
async def upload_old(file: UploadFile = File()):
    content = await file.read()
    # Manual file handling...

# New way - all existing code works, plus new features
from zenith.web.files import UploadedFile

@app.post("/upload")
async def upload_new(file: UploadedFile = File()):
    # Old methods still work
    content = await file.read()

    # Plus new convenience methods
    if file.is_image():
        final_path = await file.move_to("/uploads/image.jpg")
```

The enhanced file upload API is **backward compatible** while providing much better developer experience!