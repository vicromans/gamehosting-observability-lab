from flask import (
    abort,
    redirect,
    render_template,
    request,
)

from routes.dashboard_routes import dashboard_bp
from services.business_service import get_business_by_slug
from services.knowledge import (
    archive_document,
    create_document,
    get_document,
    list_documents,
    update_document_status,
)
from services.knowledge.file_service import (
    delete_knowledge_file,
    extract_knowledge_text,
    save_knowledge_file,
)


@dashboard_bp.get(
    "/whatsapp/dashboard/business/<business_slug>/knowledge"
)
def knowledge_library(business_slug):
    """Display the knowledge library for one business."""

    business = get_business_by_slug(business_slug)

    if not business:
        abort(404)

    documents = list_documents(
        business_id=business["id"],
        include_archived=False,
    )

    return render_template(
        "knowledge_library.html",
        business=business,
        documents=documents,
        active_page="knowledge",
    )



@dashboard_bp.get(
    "/whatsapp/dashboard/business/<business_slug>/knowledge/<int:document_id>"
)
def knowledge_document_detail(business_slug, document_id):
    """Display one knowledge document within its tenant boundary."""

    business = get_business_by_slug(business_slug)

    if not business:
        abort(404)

    document = get_document(
        document_id=document_id,
        business_id=business["id"],
    )

    if not document:
        abort(404)

    return render_template(
        "knowledge_document_detail.html",
        business=business,
        document=document,
        active_page="knowledge",
    )




@dashboard_bp.post(
    "/whatsapp/dashboard/business/<business_slug>/knowledge/<int:document_id>/approve"
)
def knowledge_document_approve(business_slug, document_id):
    """Approve one knowledge document within its tenant boundary."""

    business = get_business_by_slug(business_slug)

    if not business:
        abort(404)

    document = get_document(
        document_id=document_id,
        business_id=business["id"],
    )

    if not document:
        abort(404)

    updated = update_document_status(
        document_id=document_id,
        business_id=business["id"],
        status="approved",
    )

    if not updated:
        abort(404)

    return redirect(
        f"/whatsapp/dashboard/business/"
        f"{business_slug}/knowledge/{document_id}"
    )


@dashboard_bp.post(
    "/whatsapp/dashboard/business/<business_slug>/knowledge/<int:document_id>/archive"
)
def knowledge_document_archive(business_slug, document_id):
    """Archive one knowledge document within its tenant boundary."""

    business = get_business_by_slug(business_slug)

    if not business:
        abort(404)

    document = get_document(
        document_id=document_id,
        business_id=business["id"],
    )

    if not document:
        abort(404)

    archived = archive_document(
        document_id=document_id,
        business_id=business["id"],
    )

    if not archived:
        abort(404)

    return redirect(
        f"/whatsapp/dashboard/business/"
        f"{business_slug}/knowledge"
    )



@dashboard_bp.route(
    "/whatsapp/dashboard/business/<business_slug>/knowledge/new",
    methods=["GET", "POST"],
)
def knowledge_document_new(business_slug):
    """Create manual or uploaded knowledge."""

    business = get_business_by_slug(business_slug)

    if not business:
        abort(404)

    error = None

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        source_type = (
            request.form.get("source_type", "manual")
            .strip()
            .lower()
        )

        if not title:
            error = "El título es obligatorio."

        elif source_type == "manual":
            content = request.form.get("content", "").strip()

            if not content:
                error = "El contenido es obligatorio."
            else:
                document_id = create_document(
                    business_id=business["id"],
                    title=title,
                    document_type="text",
                    source_type="manual",
                    notes=content,
                )

                return redirect(
                    f"/whatsapp/dashboard/business/"
                    f"{business_slug}/knowledge"
                    f"?created={document_id}"
                )

        elif source_type == "upload":
            uploaded_file = request.files.get("knowledge_file")

            if not uploaded_file or not uploaded_file.filename:
                error = "Selecciona un archivo TXT, PDF o DOCX."
            else:
                stored_file = None

                try:
                    stored_file = save_knowledge_file(
                        business_id=business["id"],
                        uploaded_file=uploaded_file,
                    )

                    content = extract_knowledge_text(
                        stored_file["storage_path"]
                    )

                    document_id = create_document(
                        business_id=business["id"],
                        title=title,
                        original_filename=(
                            stored_file["original_filename"]
                        ),
                        document_type="text",
                        storage_path=(
                            stored_file["storage_path"]
                        ),
                        source_type="upload",
                        notes=content,
                    )

                except ValueError as exc:
                    if stored_file:
                        delete_knowledge_file(
                            stored_file["storage_path"]
                        )

                    error = str(exc)

                except Exception:
                    if stored_file:
                        delete_knowledge_file(
                            stored_file["storage_path"]
                        )

                    raise

                else:
                    return redirect(
                        f"/whatsapp/dashboard/business/"
                        f"{business_slug}/knowledge"
                        f"?created={document_id}"
                    )

        else:
            error = "El tipo de fuente no es válido."

    return render_template(
        "knowledge_document_new.html",
        business=business,
        active_page="knowledge",
        error=error,
    )
