from flask import abort, render_template

from routes.dashboard_routes import dashboard_bp
from services.business_service import get_business_by_slug
from services.knowledge import list_documents


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
