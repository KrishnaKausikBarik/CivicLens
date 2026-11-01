import re
import math
from models.report import Report

def validate_report_payload(data):
    """
    Validates citizen report submission payload.
    Returns: (is_valid: bool, error_message: str | None)
    """
    if not isinstance(data, dict):
        return False, "Request body must be a valid JSON object."

    title = data.get("title")
    if not title or not isinstance(title, str) or not title.strip():
        return False, "Field 'title' is required and cannot be empty."
    if len(title.strip()) > 150:
        return False, "Field 'title' exceeds maximum length of 150 characters."

    category = data.get("category")
    if not category or category not in Report.VALID_CATEGORIES:
        return False, f"Invalid category. Allowed options: {', '.join(Report.VALID_CATEGORIES)}"

    description = data.get("description")
    if not description or not isinstance(description, str) or not description.strip():
        return False, "Field 'description' is required and cannot be empty."
    if len(description) > 10000:
        return False, "Field 'description' exceeds maximum length of 10000 characters."

    lat = data.get("latitude")
    lng = data.get("longitude")
    if lat is None or lng is None:
        return False, "Both 'latitude' and 'longitude' coordinates are required."

    try:
        lat_float = float(lat)
        lng_float = float(lng)
        if not math.isfinite(lat_float) or not math.isfinite(lng_float):
            return False, "Coordinates must be finite numerical values."
        if not (-90.0 <= lat_float <= 90.0):
            return False, "Latitude must be within [-90.0, 90.0]."
        if not (-180.0 <= lng_float <= 180.0):
            return False, "Longitude must be within [-180.0, 180.0]."
    except (ValueError, TypeError):
        return False, "Coordinates must be valid numerical values."

    return True, None

def validate_status_payload(data):
    """Validates complaint status updates."""
    if not isinstance(data, dict):
        return False, "Request body must be a valid JSON object."

    status = data.get("status")
    if not status or status not in Report.VALID_STATUSES:
        return False, f"Invalid status. Allowed: {', '.join(Report.VALID_STATUSES)}"

    return True, None

def validate_email(email):
    """Basic format check for email addresses."""
    if not email or not isinstance(email, str):
        return False
    return bool(re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email.strip()))
