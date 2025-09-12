"""
File upload example for Zenith.

Demonstrates handling file uploads with validation.
"""

import os
from pathlib import Path

from pydantic import BaseModel
from starlette.datastructures import UploadFile

from zenith import File, Zenith

# Create app
app = Zenith()

# Upload directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Allowed file types
ALLOWED_IMAGES = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
ALLOWED_DOCUMENTS = {".pdf", ".doc", ".docx", ".txt", ".md"}


class FileInfo(BaseModel):
    """File upload response."""

    filename: str
    size_bytes: int
    content_type: str
    saved_path: str


@app.post("/upload/image")
async def upload_image(file: UploadFile = File()) -> FileInfo:
    """Upload a single image file."""
    # Validate file type
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_IMAGES:
        raise ValueError(f"Invalid image type. Allowed: {', '.join(ALLOWED_IMAGES)}")

    # Validate file size (5MB max)
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise ValueError("File too large. Maximum size: 5MB")

    # Save file
    save_path = UPLOAD_DIR / f"image_{file.filename}"
    with open(save_path, "wb") as f:
        f.write(contents)

    return FileInfo(
        filename=file.filename,
        size_bytes=len(contents),
        content_type=file.content_type,
        saved_path=str(save_path),
    )


@app.post("/upload/document")
async def upload_document(file: UploadFile = File()) -> FileInfo:
    """Upload a document file."""
    # Validate file type
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_DOCUMENTS:
        raise ValueError(
            f"Invalid document type. Allowed: {', '.join(ALLOWED_DOCUMENTS)}"
        )

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
async def upload_multiple(files: list[UploadFile] = File()) -> list[FileInfo]:
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
    username: str, bio: str | None = None, avatar: UploadFile = File()
) -> dict:
    """Upload profile with avatar image (mixed form data)."""
    # Validate avatar
    ext = Path(avatar.filename).suffix.lower()
    if ext not in ALLOWED_IMAGES:
        raise ValueError("Avatar must be an image file")

    # Save avatar
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

    print("📁 File Upload Example")
    print("Upload directory:", UPLOAD_DIR.absolute())
    print("\nEndpoints:")
    print("  POST /upload/image - Upload single image")
    print("  POST /upload/document - Upload document")
    print("  POST /upload/multiple - Upload multiple files")
    print("  POST /upload/profile - Mixed form with file")
    print("  GET /files - List uploaded files")
    print("  DELETE /files/{filename} - Delete file")
    print("\nTest with curl:")
    print('  curl -X POST -F "file=@image.jpg" http://localhost:8006/upload/image')
    uvicorn.run("file_upload_example:app", host="127.0.0.1", port=8006, reload=True)
