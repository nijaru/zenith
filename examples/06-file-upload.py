"""
Enhanced file upload example for Zenith.

Demonstrates modern file upload handling with improved UX,
showing both the enhanced UploadedFile API and traditional patterns.
This addresses common pain points found in production applications.
"""

import os
import uuid
from pathlib import Path

from pydantic import BaseModel
from starlette.datastructures import UploadFile

from zenith import (
    AUDIO_TYPES,
    DOCUMENT_TYPES,
    IMAGE_TYPES,
    File,
    UploadedFile,
    Zenith,
)

# Create app
app = Zenith()

# Upload directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Allowed file types
ALLOWED_IMAGES = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
ALLOWED_DOCUMENTS = {".pdf", ".doc", ".docx", ".txt", ".md"}


class FileInfo(BaseModel):
    """Enhanced file upload response."""

    filename: str
    original_filename: str
    size_bytes: int
    content_type: str
    saved_path: str
    file_type: str  # image, audio, video, document, other
    url: str | None = None


def get_file_type(file: UploadedFile | UploadFile) -> str:
    """Determine the general file type from content type or extension."""
    if hasattr(file, "is_image") and file.is_image():
        return "image"
    elif hasattr(file, "is_audio") and file.is_audio():
        return "audio"
    elif hasattr(file, "is_video") and file.is_video():
        return "video"
    elif hasattr(file, "is_pdf") and file.is_pdf():
        return "document"
    elif hasattr(file, "content_type") and file.content_type:
        if file.content_type.startswith("image/"):
            return "image"
        elif file.content_type.startswith("audio/"):
            return "audio"
        elif file.content_type.startswith("video/"):
            return "video"
        elif "pdf" in file.content_type:
            return "document"
    return "other"


@app.post("/upload/modern", response_model=FileInfo)
async def upload_modern(
    file: UploadedFile = File(
        max_size="10MB",
        allowed_types=IMAGE_TYPES + AUDIO_TYPES + ["application/pdf"],
        allowed_extensions=[".jpg", ".png", ".mp3", ".wav", ".pdf"],
    ),
) -> FileInfo:
    """
    Modern file upload using enhanced UploadedFile API.

    This demonstrates the improved UX with automatic validation
    and convenient file handling methods.
    """
    # Generate UUID-based filename to avoid conflicts
    file_id = str(uuid.uuid4())
    extension = file.get_extension()
    safe_filename = f"{file_id}{extension}"

    # Use convenient move_to method (much cleaner than manual file handling)
    final_path = await file.move_to(UPLOAD_DIR / safe_filename)

    return FileInfo(
        filename=safe_filename,
        original_filename=file.original_filename,
        size_bytes=file.size_bytes,
        content_type=file.content_type,
        saved_path=str(final_path),
        file_type=get_file_type(file),
        url=f"/files/{safe_filename}",
    )


@app.post("/upload/image")
async def upload_image(
    file: UploadFile = File(max_size="5MB", allowed_types=IMAGE_TYPES),
) -> FileInfo:
    """Upload a single image file with automatic validation."""

    contents = await file.read()

    # Save file
    save_path = UPLOAD_DIR / f"image_{file.filename}"
    with open(save_path, "wb") as f:
        f.write(contents)

    return FileInfo(
        filename=file.filename,
        original_filename=file.filename,
        size_bytes=len(contents),
        content_type=file.content_type,
        saved_path=str(save_path),
        file_type=get_file_type(file),
    )


@app.post("/upload/document")
async def upload_document(
    file: UploadFile = File(max_size="20MB", allowed_types=DOCUMENT_TYPES),
) -> FileInfo:
    """Upload a document file with automatic validation."""

    # Read and save
    contents = await file.read()
    save_path = UPLOAD_DIR / f"doc_{file.filename}"
    with open(save_path, "wb") as f:
        f.write(contents)

    return FileInfo(
        filename=file.filename,
        size_bytes=len(contents),
        content_type=file.content_type,
        saved_path=str(save_path),
    )


@app.post("/upload/multiple")
async def upload_multiple(
    files: list[UploadFile] = File(
        max_size="10MB", allowed_types=IMAGE_TYPES + DOCUMENT_TYPES
    ),
) -> list[FileInfo]:
    """Upload multiple files at once."""
    results = []

    for file in files:
        # Save each file
        contents = await file.read()
        save_path = UPLOAD_DIR / f"multi_{file.filename}"
        with open(save_path, "wb") as f:
            f.write(contents)

        results.append(
            FileInfo(
                filename=file.filename,
                size_bytes=len(contents),
                content_type=file.content_type,
                saved_path=str(save_path),
            )
        )

    return results


@app.post("/upload/profile")
async def upload_profile(
    username: str,
    bio: str | None = None,
    avatar: UploadFile = File(max_size="2MB", allowed_types=IMAGE_TYPES),
) -> dict:
    """Upload profile with avatar image (mixed form data)."""

    # Save avatar
    ext = Path(avatar.filename).suffix.lower()
    contents = await avatar.read()
    avatar_path = UPLOAD_DIR / f"avatar_{username}{ext}"
    with open(avatar_path, "wb") as f:
        f.write(contents)

    return {
        "username": username,
        "bio": bio or "No bio provided",
        "avatar": str(avatar_path),
        "avatar_size_bytes": len(contents),
    }


@app.get("/files")
async def list_files() -> list[dict]:
    """List all uploaded files."""
    files = []
    for filepath in UPLOAD_DIR.iterdir():
        if filepath.is_file():
            stat = filepath.stat()
            files.append(
                {
                    "name": filepath.name,
                    "size_bytes": stat.st_size,
                    "modified": stat.st_mtime,
                }
            )
    return files


@app.delete("/files/{filename}")
async def delete_file(filename: str) -> dict:
    """Delete an uploaded file."""
    filepath = UPLOAD_DIR / filename
    if not filepath.exists():
        raise ValueError(f"File {filename} not found")

    os.remove(filepath)
    return {"message": f"File {filename} deleted"}


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "upload_dir": str(UPLOAD_DIR)}


if __name__ == "__main__":
    import uvicorn

    print("📁 Enhanced File Upload Example")
    print("Upload directory:", UPLOAD_DIR.absolute())
    print("\nEndpoints:")
    print("  POST /upload/modern - Modern enhanced upload (recommended)")
    print("  POST /upload/image - Upload single image (traditional)")
    print("  POST /upload/document - Upload document")
    print("  POST /upload/multiple - Upload multiple files")
    print("  POST /upload/profile - Mixed form with file")
    print("  GET /files - List uploaded files")
    print("  DELETE /files/{filename} - Delete file")
    print("\nTest with curl:")
    print("  # Modern enhanced API:")
    print('  curl -X POST -F "file=@song.mp3" http://localhost:8006/upload/modern')
    print('  curl -X POST -F "file=@document.pdf" http://localhost:8006/upload/modern')
    print()
    print("  # Traditional API:")
    print('  curl -X POST -F "file=@image.jpg" http://localhost:8006/upload/image')
    uvicorn.run(app, host="127.0.0.1", port=8006, reload=True)
