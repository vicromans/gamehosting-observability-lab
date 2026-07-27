from datetime import datetime
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from flask import redirect, render_template, request

from routes.dashboard import dashboard_bp
from services.business_service import get_business_by_slug
from services.food.catalog_service import list_catalog_items
from services.food.menu_service import (
    add_catalog_items_to_menu,
    get_menu_by_date,
    remove_menu_item,
)


def _get_food_business(slug):
    business = get_business_by_slug(slug)

    if not business or not business["active"]:
        return None, ("Negocio no encontrado", 404)

    if business["business_type"] != "food":
        return None, (
            "El módulo de menú solo está disponible para restaurantes",
            404,
        )

    return business, None


def _parse_menu_date(raw_date, default_date=None):
    raw_date = (raw_date or "").strip()

    if not raw_date:
        return default_date

    try:
        return datetime.strptime(raw_date, "%Y-%m-%d").date()
    except ValueError:
        return None


@dashboard_bp.get(
    "/whatsapp/dashboard/business/<slug>/daily-menu"
)
def dashboard_daily_menu(slug):
    business, error_response = _get_food_business(slug)

    if error_response:
        return error_response

    mexico_tz = ZoneInfo(
        business.get("timezone") or "America/Mexico_City"
    )
    today = datetime.now(mexico_tz).date()

    menu_date = _parse_menu_date(
        request.args.get("date"),
        default_date=today,
    )

    if menu_date is None:
        return "Fecha inválida. Usa el formato AAAA-MM-DD.", 400

    menu = get_menu_by_date(business["id"], menu_date)

    catalog_items = list_catalog_items(
        business["id"],
        include_inactive=False,
    )

    existing_catalog_keys = set()

    if menu:
        existing_catalog_keys = {
            (
                (item.get("item_name") or "").strip().casefold(),
                (item.get("category") or "").strip().casefold(),
            )
            for item in menu.get("items", [])
        }

    for catalog_item in catalog_items:
        catalog_key = (
            (catalog_item.get("item_name") or "").strip().casefold(),
            (catalog_item.get("category") or "").strip().casefold(),
        )
        catalog_item["already_added"] = (
            catalog_key in existing_catalog_keys
        )

    try:
        added_count = int(request.args.get("added", "0"))
    except ValueError:
        added_count = 0

    removed = request.args.get("removed") == "1"

    return render_template(
        "daily_menu.html",
        business=business,
        menu=menu,
        menu_date=menu_date,
        today=today,
        catalog_items=catalog_items,
        added_count=added_count,
        removed=removed,
        active_page="daily_menu",
        page_title="Menú del día",
        page_subtitle="Consulta y administración del menú diario",
    )


@dashboard_bp.post(
    "/whatsapp/dashboard/business/<slug>/daily-menu/add-items"
)
def dashboard_daily_menu_add_items(slug):
    business, error_response = _get_food_business(slug)

    if error_response:
        return error_response

    menu_date = _parse_menu_date(request.form.get("menu_date"))

    if menu_date is None:
        return "Fecha inválida. Usa el formato AAAA-MM-DD.", 400

    catalog_item_ids = request.form.getlist("catalog_item_ids")

    added_count = add_catalog_items_to_menu(
        business_id=business["id"],
        menu_date=menu_date,
        catalog_item_ids=catalog_item_ids,
    )

    query_string = urlencode(
        {
            "date": menu_date.isoformat(),
            "added": added_count,
        }
    )

    return redirect(
        f"/whatsapp/dashboard/business/{slug}/daily-menu"
        f"?{query_string}"
    )


@dashboard_bp.post(
    "/whatsapp/dashboard/business/<slug>/daily-menu/remove-item"
)
def dashboard_daily_menu_remove_item(slug):
    business, error_response = _get_food_business(slug)

    if error_response:
        return error_response

    menu_date = _parse_menu_date(request.form.get("menu_date"))

    if menu_date is None:
        return "Fecha inválida. Usa el formato AAAA-MM-DD.", 400

    try:
        menu_item_id = int(request.form.get("menu_item_id", ""))
    except (TypeError, ValueError):
        return "Platillo inválido.", 400

    menu = get_menu_by_date(business["id"], menu_date)

    if not menu:
        return "Menú no encontrado.", 404

    valid_item_ids = {
        int(item["id"])
        for item in menu.get("items", [])
    }

    if menu_item_id not in valid_item_ids:
        return "El platillo no pertenece a este menú.", 404

    removed = remove_menu_item(menu_item_id)

    query_string = urlencode(
        {
            "date": menu_date.isoformat(),
            "removed": 1 if removed else 0,
        }
    )

    return redirect(
        f"/whatsapp/dashboard/business/{slug}/daily-menu"
        f"?{query_string}"
    )
