from pathlib import Path
from uuid import uuid4

from docx import Document
from pypdf import PdfReader


KNOWLEDGE_STORAGE_ROOT = Path("/app/data/knowledge")

ALLOWED_EXTENSIONS = {
    ".txt",
    ".pdf",
    ".docx",
}

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024


def save_knowledge_file(
    business_id,
    uploaded_file,
):
    """
    Save one uploaded knowledge file inside its tenant directory.
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


def extract_knowledge_text(
    storage_path,
):
    """
    Extract usable text from a supported knowledge document.
    """

    path = Path(storage_path)
    extension = path.suffix.lower()

    if extension == ".txt":
        return _extract_txt(path)

    if extension == ".pdf":
        return _extract_pdf(path)

    if extension == ".docx":
        return _extract_docx(path)

    raise ValueError(
        "Unsupported knowledge file type."
    )


def _extract_txt(path):
    try:
        content = path.read_text(
            encoding="utf-8"
        )
    except UnicodeDecodeError as exc:
        raise ValueError(
            "The TXT file must use UTF-8 encoding."
        ) from exc

    return _validate_extracted_text(
        content,
        "The TXT file does not contain usable text.",
    )


def _extract_pdf(path):
    try:
        reader = PdfReader(
            str(path)
        )

        parts = []

        for page in reader.pages:
            text = page.extract_text()

            if text:
                parts.append(text)

        content = "\n\n".join(parts)

    except Exception as exc:
        raise ValueError(
            "The PDF could not be read."
        ) from exc

    return _validate_extracted_text(
        content,
        "The PDF does not contain extractable text.",
    )


def _extract_docx(path):
    try:
        document = Document(
            str(path)
        )

        parts = []

        for paragraph in document.paragraphs:
            text = paragraph.text.strip()

            if text:
                parts.append(text)

        content = "\n\n".join(parts)

    except Exception as exc:
        raise ValueError(
            "The DOCX file could not be read."
        ) from exc

    return _validate_extracted_text(
        content,
        "The DOCX file does not contain usable text.",
    )


def _validate_extracted_text(
    content,
    empty_message,
):
    content = (
        content or ""
    ).strip()

    if not content:
        raise ValueError(
            empty_message
        )

    return content


def delete_knowledge_file(
    storage_path,
):
    """
    Remove a stored knowledge file when a transaction fails.
    """

    if not storage_path:
        return

    Path(storage_path).unlink(
        missing_ok=True
    )
