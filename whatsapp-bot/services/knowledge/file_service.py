from pathlib import Path
from uuid import uuid4


KNOWLEDGE_STORAGE_ROOT = Path("/app/data/knowledge")

ALLOWED_EXTENSIONS = {
    ".txt",
}

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024


def save_knowledge_file(
    business_id,
    uploaded_file,
):
    """
    Save one uploaded knowledge file inside its tenant directory.

    Returns metadata describing the stored file.
    """

    if not uploaded_file:
        raise ValueError("No file was provided.")

    original_filename = (
        uploaded_file.filename or ""
    ).strip()

    if not original_filename:
        raise ValueError("The file must have a name.")

    extension = Path(
        original_filename
    ).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError(
            "Unsupported knowledge file type."
        )

    tenant_directory = (
        KNOWLEDGE_STORAGE_ROOT
        / str(business_id)
    )

    tenant_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    stored_filename = (
        f"{uuid4().hex}{extension}"
    )

    destination_path = (
        tenant_directory
        / stored_filename
    )

    temporary_path = Path(
        f"{destination_path}.part"
    )

    uploaded_file.save(
        temporary_path
    )

    file_size = temporary_path.stat().st_size

    if file_size == 0:
        temporary_path.unlink(
            missing_ok=True
        )
        raise ValueError(
            "The uploaded file is empty."
        )

    if file_size > MAX_FILE_SIZE_BYTES:
        temporary_path.unlink(
            missing_ok=True
        )
        raise ValueError(
            "The uploaded file is too large."
        )

    temporary_path.replace(
        destination_path
    )

    return {
        "original_filename": original_filename,
        "stored_filename": stored_filename,
        "storage_path": str(destination_path),
        "extension": extension,
        "file_size": file_size,
    }


def extract_text_file(storage_path):
    """
    Extract plain text from a UTF-8 TXT knowledge file.
    """

    path = Path(storage_path)

    try:
        content = path.read_text(
            encoding="utf-8"
        )
    except UnicodeDecodeError as exc:
        raise ValueError(
            "The TXT file must use UTF-8 encoding."
        ) from exc

    content = content.strip()

    if not content:
        raise ValueError(
            "The TXT file does not contain usable text."
        )

    return content


def delete_knowledge_file(storage_path):
    """
    Remove a stored knowledge file when a transaction fails.
    """

    if not storage_path:
        return

    Path(storage_path).unlink(
        missing_ok=True
    )
