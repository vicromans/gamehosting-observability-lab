from datetime import date

from services.wellness.program_service import list_programs
from services.wellness.session_service import list_session_types


def build_wellness_ai_context(business_id):
    """
    Build public business context that may safely be exposed
    to the wellness AI assistant.

    Customer appointments, phone numbers, notes, and other
    private customer data are intentionally excluded.
    """

    session_types = list_session_types(
        business_id,
        include_inactive=False,
    )

    programs = list_programs(business_id)

    published_programs = [
        program
        for program in programs
        if program.get("status") == "published"
    ]

    return {
        "business_id": business_id,
        "generated_on": date.today().isoformat(),
        "session_types": [
            {
                "name": session.get("name"),
                "description": session.get("description"),
                "duration_minutes": session.get("duration_minutes"),
                "price": session.get("price"),
                "currency": session.get("currency"),
                "delivery_mode": session.get("delivery_mode"),
            }
            for session in session_types
        ],
        "programs": [
            {
                "title": program.get("title"),
                "program_type": program.get("program_type"),
                "description": program.get("description"),
                "delivery_mode": program.get("delivery_mode"),
                "location_name": program.get("location_name"),
                "location_address": program.get("location_address"),
                "online_platform": program.get("online_platform"),
                "is_free": bool(program.get("is_free")),
                "price": program.get("price"),
                "currency": program.get("currency"),
                "capacity": program.get("capacity"),
                "registration_status": program.get(
                    "registration_status"
                ),
                "registration_deadline": program.get(
                    "registration_deadline"
                ),
                "sessions": [
                    {
                        "session_number": item.get("session_number"),
                        "session_title": item.get("session_title"),
                        "session_date": item.get("session_date"),
                        "start_time": item.get("start_time"),
                        "end_time": item.get("end_time"),
                    }
                    for item in program.get("sessions", [])
                ],
            }
            for program in published_programs
        ],
    }
