from datetime import datetime
from zoneinfo import ZoneInfo

from flask import render_template, request

from routes.dashboard import dashboard_bp
from services.business_service import get_business_by_slug
from services.food.menu_service import get_menu_by_date


@dashboard_bp.get("/whatsapp/dashboard/business/<slug>/daily-menu")
def dashboard_daily_menu(slug):
    business = get_business_by_slug(slug)

    if not business or not business["active"]:
        return "Negocio no encontrado", 404

    if business["business_type"] != "food":
        return "El módulo de menú solo está disponible para restaurantes", 404

    mexico_tz = ZoneInfo(
        business.get("timezone") or "America/Mexico_City"
    )
    today = datetime.now(mexico_tz).date()

    requested_date = request.args.get("date", "").strip()

    if requested_date:
        try:
            menu_date = datetime.strptime(
                requested_date,
                "%Y-%m-%d",
            ).date()
        except ValueError:
            return "Fecha inválida. Usa el formato AAAA-MM-DD.", 400
    else:
        menu_date = today

    menu = get_menu_by_date(business["id"], menu_date)

    return render_template(
        "daily_menu.html",
        business=business,
        menu=menu,
        menu_date=menu_date,
        today=today,
        active_page="daily_menu",
        page_title="Menú del día",
        page_subtitle="Consulta y administración del menú diario",
    )
