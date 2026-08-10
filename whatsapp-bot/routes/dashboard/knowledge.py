from flask import (
    abort,
    redirect,
    render_template,
    request,
)

from routes.dashboard_routes import dashboard_bp
from services.business_service import get_business_by_slug
from services.knowledge import (
    create_document,
    list_documents,
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


@dashboard_bp.route(
    "/whatsapp/dashboard/business/<business_slug>/knowledge/new",
    methods=["GET", "POST"],
)
def knowledge_document_new(business_slug):
    """Create a manual knowledge document."""

    business = get_business_by_slug(business_slug)

    if not business:
        abort(404)

    error = None

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()

        if not title:
            error = "El título es obligatorio."
        elif not content:
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

    return render_template(
        "knowledge_document_new.html",
        business=business,
        active_page="knowledge",
        error=error,
    )
