from routes.dashboard import dashboard_bp


def _get_food_business_or_404(slug):
    from flask import abort

    from services.business_service import get_business_by_slug

    business = get_business_by_slug(slug)

    if not business or not business.get("active"):
        abort(404)

    if business.get("business_type") != "food":
        abort(404)

    return business


def _empty_food_catalog_form():
    return {
        "item_name": "",
        "category": "",
        "description": "",
        "included_in_meal": True,
        "has_surcharge": False,
        "surcharge_amount": "",
        "available_individually": False,
        "individual_price": "",
    }


def _food_catalog_form_from_item(item):
    return {
        "item_name": item.get("item_name") or "",
        "category": item.get("category") or "",
        "description": item.get("description") or "",
        "included_in_meal": bool(item.get("included_in_meal")),
        "has_surcharge": bool(item.get("has_surcharge")),
        "surcharge_amount": (
            item.get("surcharge_amount")
            if item.get("surcharge_amount") is not None
            else ""
        ),
        "available_individually": bool(
            item.get("available_individually")
        ),
        "individual_price": (
            item.get("individual_price")
            if item.get("individual_price") is not None
            else ""
        ),
    }


def _food_catalog_form_from_request():
    from flask import request

    return {
        "item_name": request.form.get("item_name", "").strip(),
        "category": request.form.get("category", "").strip(),
        "description": request.form.get("description", "").strip(),
        "included_in_meal": (
            request.form.get("included_in_meal") == "1"
        ),
        "has_surcharge": (
            request.form.get("has_surcharge") == "1"
        ),
        "surcharge_amount": request.form.get(
            "surcharge_amount",
            "",
        ).strip(),
        "available_individually": (
            request.form.get("available_individually") == "1"
        ),
        "individual_price": request.form.get(
            "individual_price",
            "",
        ).strip(),
    }


def _validate_food_catalog_form(form_data):
    from decimal import Decimal, InvalidOperation

    if not form_data["item_name"]:
        return (
            "El nombre del platillo es obligatorio.",
            None,
            None,
        )

    if (
        form_data["has_surcharge"]
        and not form_data["included_in_meal"]
    ):
        return (
            "El costo adicional solo aplica a platillos "
            "incluidos en comida corrida.",
            None,
            None,
        )

    surcharge_amount = None
    individual_price = None

    if form_data["has_surcharge"]:
        if not form_data["surcharge_amount"]:
            return (
                "Indica el costo adicional.",
                None,
                None,
            )

        try:
            surcharge_amount = Decimal(
                form_data["surcharge_amount"]
            )
        except InvalidOperation:
            return (
                "El costo adicional no es válido.",
                None,
                None,
            )

        if surcharge_amount <= 0:
            return (
                "El costo adicional debe ser mayor que cero.",
                None,
                None,
            )

    if form_data["available_individually"]:
        if not form_data["individual_price"]:
            return (
                "Indica el precio individual.",
                None,
                None,
            )

        try:
            individual_price = Decimal(
                form_data["individual_price"]
            )
        except InvalidOperation:
            return (
                "El precio individual no es válido.",
                None,
                None,
            )

        if individual_price <= 0:
            return (
                "El precio individual debe ser mayor que cero.",
                None,
                None,
            )

    if (
        not form_data["included_in_meal"]
        and not form_data["available_individually"]
    ):
        return (
            "El platillo debe poder incluirse en comida corrida "
            "o venderse individualmente.",
            None,
            None,
        )

    return None, surcharge_amount, individual_price


@dashboard_bp.get(
    "/whatsapp/dashboard/business/<slug>/food-catalog"
)
def dashboard_food_catalog(slug):
    from flask import render_template, request

    from services.food.catalog_service import list_catalog_items

    business = _get_food_business_or_404(slug)

    catalog_items = list_catalog_items(
        business["id"],
        include_inactive=True,
    )

    return render_template(
        "food_catalog.html",
        business=business,
        catalog_items=catalog_items,
        active_page="food_catalog",
        page_title="Catálogo de platillos",
        page_subtitle=(
            "Consulta y administra los platillos reutilizables "
            "del negocio."
        ),
        created=request.args.get("created") == "1",
        updated=request.args.get("updated") == "1",
    )


@dashboard_bp.route(
    "/whatsapp/dashboard/business/<slug>/food-catalog/new",
    methods=["GET", "POST"],
)
def dashboard_food_catalog_new(slug):
    from flask import redirect, render_template, request

    from services.food.catalog_service import create_catalog_item

    business = _get_food_business_or_404(slug)
    form_data = _empty_food_catalog_form()
    error = None

    if request.method == "POST":
        form_data = _food_catalog_form_from_request()

        error, surcharge_amount, individual_price = (
            _validate_food_catalog_form(form_data)
        )

        if not error:
            create_catalog_item(
                business_id=business["id"],
                item_name=form_data["item_name"],
                category=form_data["category"] or None,
                description=form_data["description"] or None,
                included_in_meal=form_data["included_in_meal"],
                has_surcharge=form_data["has_surcharge"],
                surcharge_amount=surcharge_amount,
                available_individually=(
                    form_data["available_individually"]
                ),
                individual_price=individual_price,
                currency="MXN",
                active=True,
                display_order=0,
            )

            return redirect(
                f"/whatsapp/dashboard/business/{slug}/food-catalog"
                "?created=1"
            )

    return render_template(
        "food_catalog_form.html",
        business=business,
        form_data=form_data,
        error=error,
        editing=False,
        active_page="food_catalog",
        page_title="Nuevo platillo",
        page_subtitle=(
            "Registra una opción reutilizable para los menús "
            "del negocio."
        ),
    )


@dashboard_bp.route(
    "/whatsapp/dashboard/business/<slug>/food-catalog/"
    "<int:item_id>/edit",
    methods=["GET", "POST"],
)
def dashboard_food_catalog_edit(slug, item_id):
    from flask import abort, redirect, render_template, request

    from services.food.catalog_service import (
        get_catalog_item,
        update_catalog_item,
    )

    business = _get_food_business_or_404(slug)

    item = get_catalog_item(
        business["id"],
        item_id,
    )

    if not item:
        abort(404)

    form_data = _food_catalog_form_from_item(item)
    error = None

    if request.method == "POST":
        form_data = _food_catalog_form_from_request()

        error, surcharge_amount, individual_price = (
            _validate_food_catalog_form(form_data)
        )

        if not error:
            update_catalog_item(
                business_id=business["id"],
                item_id=item_id,
                item_name=form_data["item_name"],
                category=form_data["category"] or None,
                description=form_data["description"] or None,
                included_in_meal=form_data["included_in_meal"],
                has_surcharge=form_data["has_surcharge"],
                surcharge_amount=surcharge_amount,
                available_individually=(
                    form_data["available_individually"]
                ),
                individual_price=individual_price,
                currency=item.get("currency") or "MXN",
                active=bool(item.get("active")),
                display_order=item.get("display_order") or 0,
            )

            return redirect(
                f"/whatsapp/dashboard/business/{slug}/food-catalog"
                "?updated=1"
            )

    return render_template(
        "food_catalog_form.html",
        business=business,
        form_data=form_data,
        error=error,
        editing=True,
        item=item,
        active_page="food_catalog",
        page_title=f"Editar {item['item_name']}",
        page_subtitle=(
            "Modifica la información y las modalidades de venta "
            "del platillo."
        ),
    )
