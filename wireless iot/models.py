"""
ChargeSense Database Models
Defines tables: users, charging_sessions, battery_readings, notifications,
user_settings, and prediction_results.
"""

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from extensions import db, login_manager


class User(UserMixin, db.Model):
    """User account entity with authentication and role-based permissions."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(100), default='')
    phone_number = db.Column(db.String(25), default='')
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships with cascade deletion
    sessions = db.relationship('ChargingSession', backref='user', cascade='all, delete-orphan', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user', cascade='all, delete-orphan', lazy='dynamic')
    settings = db.relationship('UserSettings', backref='user', uselist=False, cascade='all, delete-orphan')
    predictions = db.relationship('PredictionResult', backref='user', cascade='all, delete-orphan', lazy='dynamic')
    sms_logs = db.relationship('SMSNotification', backref='user', cascade='all, delete-orphan', lazy='dynamic')

    def set_password(self, password):
        """Hashes and stores password using pbkdf2:sha256."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifies password against stored hash."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'is_admin': self.is_admin,
            'created_at': self.created_at.isoformat()
        }

    def __repr__(self):
        return f'<User {self.username}>'


@login_manager.user_loader
def load_user(user_id):
    """Flask-Login user loader callback."""
    return User.query.get(int(user_id))


class ChargingSession(db.Model):
    """Records an individual charging session (simulated or IoT telemetry)."""
    __tablename__ = 'charging_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    start_percentage = db.Column(db.Float, nullable=False)
    end_percentage = db.Column(db.Float, default=0.0)
    target_percentage = db.Column(db.Float, default=80.0)
    charging_speed = db.Column(db.String(20), default='normal')  # slow, normal, fast
    charging_rate = db.Column(db.Float, default=1.0)  # % per minute
    duration_minutes = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='in_progress')  # in_progress, completed, stopped
    sms_sent = db.Column(db.Boolean, default=False)  # Enforces exactly ONE SMS per session
    sms_status = db.Column(db.String(30), default='none')  # none, sent, failed, disabled
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Telemetry readings relationship
    readings = db.relationship('BatteryReading', backref='session', cascade='all, delete-orphan', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'start_percentage': round(self.start_percentage, 1),
            'end_percentage': round(self.end_percentage, 1),
            'target_percentage': round(self.target_percentage, 1),
            'charging_speed': self.charging_speed,
            'charging_rate': round(self.charging_rate, 2),
            'duration_minutes': round(self.duration_minutes, 1),
            'status': self.status,
            'sms_sent': self.sms_sent,
            'sms_status': self.sms_status,
            'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.start_time else None,
            'end_time': self.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.end_time else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }

    def __repr__(self):
        return f'<ChargingSession id={self.id} user_id={self.user_id} status={self.status}>'


class BatteryReading(db.Model):
    """Periodic telemetry point sampled during a charging session."""
    __tablename__ = 'battery_readings'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('charging_sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    percentage = db.Column(db.Float, nullable=False)
    voltage = db.Column(db.Float, default=3.85)  # in Volts
    temperature = db.Column(db.Float, default=29.5)  # in Celsius
    charging_rate = db.Column(db.Float, default=1.0)  # current rate %/min
    status = db.Column(db.String(20), default='charging')  # charging, discharging, idle
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'percentage': round(self.percentage, 1),
            'voltage': round(self.voltage, 2),
            'temperature': round(self.temperature, 1),
            'charging_rate': round(self.charging_rate, 2),
            'status': self.status,
            'timestamp': self.timestamp.strftime('%H:%M:%S')
        }

    def __repr__(self):
        return f'<BatteryReading session={self.session_id} {self.percentage}%>'


class Notification(db.Model):
    """In-app alert for battery events, milestones, and warnings."""
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    title = db.Column(db.String(120), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    notification_type = db.Column(db.String(20), default='info')  # info, success, warning, danger
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'message': self.message,
            'notification_type': self.notification_type,
            'is_read': self.is_read,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

    def __repr__(self):
        return f'<Notification id={self.id} title={self.title} is_read={self.is_read}>'


class UserSettings(db.Model):
    """Personalized user preferences and simulation configuration."""
    __tablename__ = 'user_settings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    default_target_percentage = db.Column(db.Float, default=80.0)
    default_charging_speed = db.Column(db.String(20), default='normal')  # slow, normal, fast
    simulation_speed_multiplier = db.Column(db.Float, default=1.0)
    browser_notifications_enabled = db.Column(db.Boolean, default=True)
    phone_number = db.Column(db.String(25), default='')
    sms_alerts_enabled = db.Column(db.Boolean, default=True)
    buzzer_alerts_enabled = db.Column(db.Boolean, default=True)
    theme = db.Column(db.String(10), default='dark')  # dark, light
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'default_target_percentage': self.default_target_percentage,
            'default_charging_speed': self.default_charging_speed,
            'simulation_speed_multiplier': self.simulation_speed_multiplier,
            'browser_notifications_enabled': self.browser_notifications_enabled,
            'theme': self.theme,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }

    def __repr__(self):
        return f'<UserSettings user_id={self.user_id} theme={self.theme}>'


class PredictionResult(db.Model):
    """Stores predictions made by baseline and machine learning algorithms."""
    __tablename__ = 'prediction_results'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    session_id = db.Column(db.Integer, db.ForeignKey('charging_sessions.id', ondelete='SET NULL'), nullable=True)
    current_percentage = db.Column(db.Float, nullable=False)
    target_percentage = db.Column(db.Float, nullable=False)
    charging_speed = db.Column(db.String(20), default='normal')
    baseline_predicted_minutes = db.Column(db.Float, nullable=False)
    ml_predicted_minutes = db.Column(db.Float, nullable=True)
    actual_minutes = db.Column(db.Float, nullable=True)
    error_minutes = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'current_percentage': round(self.current_percentage, 1),
            'target_percentage': round(self.target_percentage, 1),
            'charging_speed': self.charging_speed,
            'baseline_predicted_minutes': round(self.baseline_predicted_minutes, 1),
            'ml_predicted_minutes': round(self.ml_predicted_minutes, 1) if self.ml_predicted_minutes is not None else None,
            'actual_minutes': round(self.actual_minutes, 1) if self.actual_minutes is not None else None,
            'error_minutes': round(self.error_minutes, 1) if self.error_minutes is not None else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

    def __repr__(self):
        return f'<PredictionResult id={self.id} baseline={self.baseline_predicted_minutes}m>'


class SMSNotification(db.Model):
    """
    Stores SMS dispatch history, delivery status, and Twilio message logs in MySQL/Database.
    Enforces tracking of every SMS event linked to user accounts and charging sessions.
    """
    __tablename__ = 'sms_notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    session_id = db.Column(db.Integer, db.ForeignKey('charging_sessions.id', ondelete='SET NULL'), nullable=True, index=True)
    phone_number = db.Column(db.String(30), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), default='sent')  # 'sent', 'failed', 'delivered', 'simulated', 'disabled'
    gateway = db.Column(db.String(50), default='Twilio SMS API')
    sid = db.Column(db.String(64), nullable=True)  # Twilio Message SID (e.g., SM...)
    error_message = db.Column(db.String(255), nullable=True)
    target_percentage = db.Column(db.Float, nullable=True)
    current_percentage = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'phone_number': self.phone_number,
            'message': self.message,
            'status': self.status,
            'gateway': self.gateway,
            'sid': self.sid,
            'error_message': self.error_message,
            'target_percentage': self.target_percentage,
            'current_percentage': self.current_percentage,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }

    def __repr__(self):
        return f'<SMSNotification id={self.id} to={self.phone_number} status={self.status}>'
