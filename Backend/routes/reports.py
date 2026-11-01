from flask import Blueprint, jsonify, request
from sqlalchemy import String, cast, or_
from sqlalchemy.orm import joinedload
from database import db
from models.report import Report
from utils.validators import validate_report_payload, validate_status_payload
from middleware.auth_middleware import admin_session_required, citizen_session_required

reports_bp = Blueprint("reports_bp", __name__)


def _filtered_query(query):
    category = request.args.get("category", "ALL").strip()
    status = request.args.get("status", "ALL").strip()
    search = request.args.get("search", "").strip()
    if category.upper() != "ALL":
        if category not in Report.VALID_CATEGORIES:
            return None, "Invalid category filter."
        query = query.filter(Report.category == category)
    if status.upper() != "ALL":
        if status not in Report.VALID_STATUSES:
            return None, "Invalid status filter."
        query = query.filter(Report.status == status)
    if len(search) > 200:
        return None, "Search text is too long."
    if search:
        pattern = f"%{search}%"
        query = query.filter(or_(
            Report.title.ilike(pattern), Report.description.ilike(pattern),
            cast(Report.id, String).ilike(pattern)
        ))
    return query, None


def _admin_report_dict(report):
    data = report.to_dict()
    data.update({
        "user_id": report.user_id,
        "full_name": report.user.full_name if report.user else "Legacy/Unknown",
        "user_email": report.user.email if report.user else "Legacy/Unknown",
        "submitted_by": report.user.full_name if report.user else "Legacy/Unknown",
    })
    return data


@reports_bp.route("/reports", methods=["POST"])
@citizen_session_required
def create_report(current_user):
    data = request.get_json(silent=True)
    valid, error = validate_report_payload(data)
    if not valid:
        return jsonify({"success": False, "error": error}), 400
    report = Report(
        title=data["title"].strip(), category=data["category"],
        description=data["description"].strip(), latitude=float(data["latitude"]),
        longitude=float(data["longitude"]), status="Pending", user_id=current_user.id,
    )
    db.session.add(report)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"success": False, "error": "Failed to record complaint."}), 500
    return jsonify({"success": True, "message": "Complaint successfully registered.", "report": report.to_dict()}), 201


@reports_bp.route("/reports", methods=["GET"])
@citizen_session_required
def get_my_reports(current_user):
    query, error = _filtered_query(Report.query.filter_by(user_id=current_user.id))
    if error:
        return jsonify({"success": False, "error": error}), 400
    reports = query.order_by(Report.created_at.desc()).all()
    return jsonify([report.to_dict() for report in reports]), 200


@reports_bp.route("/public/reports", methods=["GET"])
def get_public_reports():
    query, error = _filtered_query(Report.query)
    if error:
        return jsonify({"success": False, "error": error}), 400
    reports = query.order_by(Report.created_at.desc()).all()
    return jsonify([report.to_dict() for report in reports]), 200


@reports_bp.route("/reports/<int:report_id>", methods=["GET"])
@citizen_session_required
def get_single_report(current_user, report_id):
    report = Report.query.filter_by(id=report_id, user_id=current_user.id).first()
    if not report:
        return jsonify({"success": False, "error": "Report not found."}), 404
    return jsonify({"success": True, "report": report.to_dict()}), 200


@reports_bp.route("/admin/reports", methods=["GET"])
@admin_session_required
def get_admin_reports():
    query, error = _filtered_query(Report.query.options(joinedload(Report.user)))
    if error:
        return jsonify({"success": False, "error": error}), 400
    reports = query.order_by(Report.created_at.desc()).all()
    return jsonify([_admin_report_dict(report) for report in reports]), 200


@reports_bp.route("/admin/reports/<int:report_id>/status", methods=["PUT"])
@admin_session_required
def update_admin_report_status(report_id):
    report = db.session.get(Report, report_id)
    if not report:
        return jsonify({"success": False, "error": "Report not found."}), 404
    data = request.get_json(silent=True)
    valid, error = validate_status_payload(data)
    if not valid:
        return jsonify({"success": False, "error": error}), 400
    report.status = data["status"]
    db.session.commit()
    return jsonify({"success": True, "report": _admin_report_dict(report)}), 200


@reports_bp.route("/reports/<int:report_id>", methods=["PUT", "PATCH"])
@citizen_session_required
def update_report(current_user, report_id):
    report = db.session.get(Report, report_id)
    if not report or report.user_id != current_user.id:
        return jsonify({"success": False, "error": "Report not found."}), 404
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"success": False, "error": "A valid JSON object is required."}), 400
    if "title" in data:
        title = data["title"]
        if not isinstance(title, str) or not title.strip() or len(title.strip()) > 150:
            return jsonify({"success": False, "error": "Invalid title."}), 400
        report.title = title.strip()
    if "category" in data:
        if data["category"] not in Report.VALID_CATEGORIES:
            return jsonify({"success": False, "error": "Invalid category."}), 400
        report.category = data["category"]
    if "description" in data:
        description = data["description"]
        if not isinstance(description, str) or not description.strip() or len(description) > 10000:
            return jsonify({"success": False, "error": "Invalid description."}), 400
        report.description = description.strip()
    try:
        if "latitude" in data:
            report.latitude = float(data["latitude"])
        if "longitude" in data:
            report.longitude = float(data["longitude"])
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Coordinates must be numeric."}), 400
    if not (-90 <= report.latitude <= 90 and -180 <= report.longitude <= 180):
        return jsonify({"success": False, "error": "Coordinates are out of range."}), 400
    db.session.commit()
    return jsonify({"success": True, "report": report.to_dict()}), 200


@reports_bp.route("/reports/<int:report_id>/status", methods=["PUT", "PATCH"])
@admin_session_required
def update_report_status(report_id):
    report = db.session.get(Report, report_id)
    if not report:
        return jsonify({"success": False, "error": "Report not found."}), 404
    data = request.get_json(silent=True)
    valid, error = validate_status_payload(data)
    if not valid:
        return jsonify({"success": False, "error": error}), 400
    report.status = data["status"]
    db.session.commit()
    return jsonify({"success": True, "report": _admin_report_dict(report)}), 200


@reports_bp.route("/reports/<int:report_id>", methods=["DELETE"])
@admin_session_required
def delete_report(report_id):
    report = db.session.get(Report, report_id)
    if not report:
        return jsonify({"success": False, "error": "Report not found."}), 404
    db.session.delete(report)
    db.session.commit()
    return jsonify({"success": True, "message": "Report deleted."}), 200


@reports_bp.route("/reports/bulk-delete", methods=["POST", "DELETE"])
@admin_session_required
def bulk_delete_reports():
    data = request.get_json(silent=True)
    ids = data.get("ids") if isinstance(data, dict) else None
    if not isinstance(ids, list) or not ids or any(not str(value).isdigit() for value in ids):
        return jsonify({"success": False, "error": "Provide valid report IDs."}), 400
    deleted = Report.query.filter(Report.id.in_([int(value) for value in ids])).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({"success": True, "deleted_count": deleted}), 200


@reports_bp.route("/stats", methods=["GET"])
def get_dashboard_stats():
    total = Report.query.count()
    pending = Report.query.filter_by(status="Pending").count()
    in_progress = Report.query.filter_by(status="In Progress").count()
    resolved = Report.query.filter_by(status="Resolved").count()
    categories = db.session.query(Report.category, db.func.count(Report.id)).group_by(Report.category).all()
    return jsonify({"total": total, "pending": pending, "in_progress": in_progress,
                    "resolved": resolved, "by_category": {category: count for category, count in categories}}), 200
