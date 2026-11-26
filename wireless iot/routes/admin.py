"""
ChargeSense Administrator Module Routes
Provides authorized administrator control over user accounts,
system-wide simulation telemetry, and database records.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, current_user
from extensions import db
from models import User, ChargingSession, BatteryReading, PredictionResult, Notification

admin_bp = Blueprint('admin', __name__)


def admin_required():
    """Helper to verify current user has administrator authorization."""
    if not current_user.is_authenticated or not current_user.is_admin:
        abort(403)


@admin_bp.route('/admin')
@login_required
def admin_view():
    """Renders the administrative management dashboard."""
    admin_required()

    users = User.query.order_by(User.created_at.desc()).all()
    total_users = len(users)
    total_sessions = ChargingSession.query.count()
    completed_sessions = ChargingSession.query.filter_by(status='completed').count()
    total_readings = BatteryReading.query.count()
    total_predictions = PredictionResult.query.count()

    return render_template(
        'admin.html',
        users=users,
        total_users=total_users,
        total_sessions=total_sessions,
        completed_sessions=completed_sessions,
        total_readings=total_readings,
        total_predictions=total_predictions
    )


@admin_bp.route('/admin/users/<int:user_id>/toggle-admin', methods=['POST'])
@login_required
def toggle_admin(user_id):
    """Toggles administrator role for a user account."""
    admin_required()
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash("You cannot remove your own administrator status.", "warning")
        return redirect(url_for('admin.admin_view'))

    user.is_admin = not user.is_admin
    db.session.commit()
    status = "promoted to Admin" if user.is_admin else "demoted to Standard User"
    flash(f"User '{user.username}' has been {status}.", "success")
    return redirect(url_for('admin.admin_view'))


@admin_bp.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    """Deletes a user account and associated cascade data."""
    admin_required()
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash("You cannot delete your own active administrator account.", "danger")
        return redirect(url_for('admin.admin_view'))

    username = user.username
    db.session.delete(user)
    db.session.commit()
    flash(f"User '{username}' and associated sessions have been deleted.", "info")
    return redirect(url_for('admin.admin_view'))


@admin_bp.route('/api/admin/system-stats')
@login_required
def system_stats_api():
    """Returns JSON system usage metrics for administrative monitoring."""
    admin_required()
    return jsonify({
        'total_users': User.query.count(),
        'total_sessions': ChargingSession.query.count(),
        'completed_sessions': ChargingSession.query.filter_by(status='completed').count(),
        'in_progress_sessions': ChargingSession.query.filter_by(status='in_progress').count(),
        'total_telemetry_points': BatteryReading.query.count(),
        'total_predictions': PredictionResult.query.count()
    })
