"""
ChargeSense Notification Center Routes
Handles user notification listing, read-state toggles, and clearing.
"""

from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from services.notification_service import notification_service

notifications_bp = Blueprint('notifications', __name__)


@notifications_bp.route('/notifications')
@login_required
def notifications_view():
    """Renders the notification center page."""
    user_id = current_user.id
    items = notification_service.get_user_notifications(user_id, limit=100)
    unread_count = notification_service.get_unread_count(user_id)

    return render_template(
        'notifications.html',
        notifications=items,
        unread_count=unread_count
    )


@notifications_bp.route('/api/notifications')
@login_required
def api_get_notifications():
    """Returns recent notifications and unread badge count for the top navbar."""
    user_id = current_user.id
    items = notification_service.get_user_notifications(user_id, limit=10)
    unread = notification_service.get_unread_count(user_id)

    return jsonify({
        'success': True,
        'unread_count': unread,
        'notifications': [n.to_dict() for n in items]
    })


@notifications_bp.route('/api/notifications/<int:notif_id>/read', methods=['POST'])
@login_required
def api_mark_read(notif_id):
    """Marks a single notification as read."""
    success = notification_service.mark_as_read(notif_id, current_user.id)
    return jsonify({'success': success})


@notifications_bp.route('/api/notifications/mark-all-read', methods=['POST'])
@login_required
def api_mark_all_read():
    """Marks all user notifications as read."""
    count = notification_service.mark_all_as_read(current_user.id)
    return jsonify({'success': True, 'marked_count': count})


@notifications_bp.route('/api/notifications/clear', methods=['POST'])
@login_required
def api_clear_all():
    """Deletes all user notifications."""
    count = notification_service.clear_all(current_user.id)
    return jsonify({'success': True, 'deleted_count': count})
