import os
import cloudinary
import cloudinary.uploader
from fastapi import HTTPException, status, UploadFile
from dotenv import load_dotenv

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)

ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}
MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


def upload_school_document(
    file: UploadFile,
    school_name: str,
    doc_type: str,
) -> str:
    """
    Uploads a school document to Cloudinary.
    Returns the secure URL of the uploaded file.

    Files are stored in: school_docs/{school_name}/{doc_type}
    e.g. school_docs/delhi_public_school/registration_certificate
    """
    if not file or not file.filename:
        return None

    # validate file extension
    ext = file.filename.split(".")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid file type for {doc_type}. Allowed: PDF, JPG, PNG",
        )

    # read file bytes
    file_bytes = file.file.read()

    # validate file size
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{doc_type} exceeds maximum size of {MAX_FILE_SIZE_MB}MB",
        )

    # sanitize school name for folder path
    safe_school_name = school_name.lower().strip().replace(" ", "_")

    # build a clean public_id for the file in Cloudinary
    # e.g. school_docs/delhi_public_school/registration_certificate
    public_id = f"school_docs/{safe_school_name}/{doc_type}"

    try:
        # upload to Cloudinary
        # resource_type="auto" handles both PDFs and images
        result = cloudinary.uploader.upload(
            file_bytes,
            public_id=public_id,
            resource_type="auto",
            overwrite=True,
            folder=None,
        )
        return result["secure_url"]  # link stored in db

    except cloudinary.exceptions.Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload {doc_type} to storage: {str(e)}",
        )
