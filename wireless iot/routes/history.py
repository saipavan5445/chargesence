"""
ChargeSense Charging History Routes
Handles session log presentation, filtering, pagination,
telemetry drill-down modal API, and CSV export.
"""

import csv
import io
from flask import Blueprint, render_template, request, jsonify, Response
from flask_login import login_required, current_user
from extensions import db
from models import ChargingSession, BatteryReading

history_bp = Blueprint('history', __name__)


@history_bp.route('/history')
@login_required
def history_view():
    """Renders user charging history table with search, filters, pagination, and KPI analytics."""
    user_id = current_user.id

    page = request.args.get('page', 1, type=int)
    per_page = 10
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', 'all')
    speed_filter = request.args.get('speed', 'all')

    query = ChargingSession.query.filter_by(user_id=user_id)

    # Compute aggregate KPI summary statistics across all sessions
    total_sessions_count = query.count()
    safe_cutoffs_count = ChargingSession.query.filter_by(user_id=user_id).filter(
        ChargingSession.end_percentage >= 78,
        ChargingSession.end_percentage <= 85
    ).count()
    total_charge_minutes = db.session.query(
        db.func.sum(ChargingSession.duration_minutes)
    ).filter(ChargingSession.user_id == user_id).scalar() or 0
    sms_count = ChargingSession.query.filter_by(user_id=user_id, sms_sent=True).count()
    safe_target_rate = round((safe_cutoffs_count / max(1, total_sessions_count)) * 100, 1)

    kpi_stats = {
        'total_sessions': total_sessions_count,
        'safe_cutoffs': safe_cutoffs_count,
        'safe_rate': safe_target_rate,
        'total_duration': int(total_charge_minutes),
        'sms_sent_count': sms_count
    }

    if status_filter != 'all':
        query = query.filter_by(status=status_filter)

    if speed_filter != 'all':
        query = query.filter_by(charging_speed=speed_filter)

    if search:
        if search.isdigit():
            query = query.filter(ChargingSession.id == int(search))
        else:
            query = query.filter(ChargingSession.charging_speed.ilike(f"%{search}%"))

    # Order newest first
    query = query.order_by(ChargingSession.created_at.desc())

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    sessions = pagination.items

    return render_template(
        'history.html',
        sessions=sessions,
        pagination=pagination,
        search=search,
        status_filter=status_filter,
        speed_filter=speed_filter,
        kpi_stats=kpi_stats
    )


@history_bp.route('/api/history/<int:session_id>/readings')
@login_required
def session_readings(session_id):
    """Returns telemetry points for session inspection modal."""
    session = ChargingSession.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
    readings = session.readings.order_by(BatteryReading.timestamp.asc()).all()

    return jsonify({
        'success': True,
        'session': session.to_dict(),
        'readings': [r.to_dict() for r in readings]
    })


@history_bp.route('/history/export')
@login_required
def export_csv():
    """Exports user charging sessions to a CSV file."""
    sessions = ChargingSession.query.filter_by(user_id=current_user.id)\
        .order_by(ChargingSession.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        'Session ID', 'Start Battery %', 'End Battery %', 'Target %',
        'Speed Scenario', 'Duration (Minutes)', 'Status', 'Start Time', 'End Time'
    ])

    for s in sessions:
        writer.writerow([
            s.id, s.start_percentage, s.end_percentage, s.target_percentage,
            s.charging_speed, s.duration_minutes, s.status,
            s.start_time.strftime('%Y-%m-%d %H:%M:%S') if s.start_time else '',
            s.end_time.strftime('%Y-%m-%d %H:%M:%S') if s.end_time else ''
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment;filename=chargesense_history.csv"}
    )
