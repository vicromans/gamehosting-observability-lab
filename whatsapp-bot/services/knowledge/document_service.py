from database.connection import get_db_connection


VALID_DOCUMENT_STATUSES = {
    "pending",
    "approved",
    "conflict",
    "archived",
}


def create_document(
    business_id,
    title,
    original_filename=None,
    document_type=None,
    storage_path=None,
    source_type="upload",
    notes=None,
):
    """Create one knowledge document for a business."""

    title = (title or "").strip()
    source_type = (source_type or "").strip()

    if not title:
        raise ValueError("Document title is required.")

    if not source_type:
        raise ValueError("Document source type is required.")

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO knowledge_documents (
                    business_id,
                    title,
                    original_filename,
                    document_type,
                    storage_path,
                    source_type,
                    notes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    business_id,
                    title,
                    original_filename,
                    document_type,
                    storage_path,
                    source_type,
                    notes,
                ),
            )

            document_id = cursor.lastrowid

        connection.commit()
        return document_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def list_documents(business_id, include_archived=False):
    """Return knowledge documents belonging to one business."""

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            if include_archived:
                cursor.execute(
                    """
                    SELECT *
                    FROM knowledge_documents
                    WHERE business_id = %s
                    ORDER BY created_at DESC, id DESC
                    """,
                    (business_id,),
                )
            else:
                cursor.execute(
                    """
                    SELECT *
                    FROM knowledge_documents
                    WHERE business_id = %s
                      AND status <> 'archived'
                    ORDER BY created_at DESC, id DESC
                    """,
                    (business_id,),
                )

            return cursor.fetchall()

    finally:
        connection.close()


def get_document(document_id, business_id):
    """Return one document only when it belongs to the business."""

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM knowledge_documents
                WHERE id = %s
                  AND business_id = %s
                LIMIT 1
                """,
                (
                    document_id,
                    business_id,
                ),
            )

            return cursor.fetchone()

    finally:
        connection.close()


def update_document_status(document_id, business_id, status):
    """Update document status within its tenant boundary."""

    status = (status or "").strip().lower()

    if status not in VALID_DOCUMENT_STATUSES:
        raise ValueError("Invalid knowledge document status.")

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE knowledge_documents
                SET status = %s
                WHERE id = %s
                  AND business_id = %s
                """,
                (
                    status,
                    document_id,
                    business_id,
                ),
            )

            updated = cursor.rowcount

        connection.commit()
        return updated > 0

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def archive_document(document_id, business_id):
    """Archive a knowledge document without deleting it."""

    return update_document_status(
        document_id=document_id,
        business_id=business_id,
        status="archived",
    )


def list_approved_documents(business_id):
    """
    Return approved knowledge documents for one business.

    Only explicitly approved documents are eligible to be exposed
    to AI consumers.
    """
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    business_id,
                    title,
                    original_filename,
                    document_type,
                    storage_path,
                    source_type,
                    status,
                    notes,
                    created_at,
                    updated_at
                FROM knowledge_documents
                WHERE business_id = %s
                  AND status = 'approved'
                ORDER BY updated_at DESC, id DESC
                """,
                (business_id,),
            )

            return cursor.fetchall()

    finally:
        connection.close()
