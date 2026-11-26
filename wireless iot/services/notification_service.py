"""
ChargeSense Notification Service
Manages creation, retrieval, and status updates for in-app alert notifications.
"""

from datetime import datetime
from extensions import db
from models import Notification


class NotificationService:
    """Handles notification lifecycles and retrieval."""

    @staticmethod
    def create_notification(user_id: int, title: str, message: str, notification_type: str = 'info') -> Notification:
        """Creates and commits a new notification for a user."""
        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            is_read=False,
            created_at=datetime.utcnow()
        )
        db.session.add(notif)
        db.session.commit()
        return notif

    @staticmethod
    def get_user_notifications(user_id: int, unread_only: bool = False, limit: int = 50):
        """Retrieves recent notifications for the specified user."""
        query = Notification.query.filter_by(user_id=user_id)
        if unread_only:
            query = query.filter_by(is_read=False)
        return query.order_by(Notification.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_unread_count(user_id: int) -> int:
        """Returns the number of unread notifications for a user."""
        return Notification.query.filter_by(user_id=user_id, is_read=False).count()

    @staticmethod
    def mark_as_read(notification_id: int, user_id: int) -> bool:
        """Marks a single notification as read if owned by the user."""
        notif = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
        if notif:
            notif.is_read = True
            db.session.commit()
            return True
        return False

    @staticmethod
    def mark_all_as_read(user_id: int) -> int:
        """Marks all unread notifications as read for a user."""
        updated = Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
        db.session.commit()
        return updated

    @staticmethod
    def clear_all(user_id: int) -> int:
        """Deletes all notifications for a user."""
        deleted = Notification.query.filter_by(user_id=user_id).delete()
        db.session.commit()
        return deleted


notification_service = NotificationService()
