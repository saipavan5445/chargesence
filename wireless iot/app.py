"""
ChargeSense Application Factory & Entry Point
Main entry point for the ChargeSense Intelligent Charging Prediction System.
"""

import os
import sys

# Ensure chargesense root directory is in Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from datetime import datetime, timedelta
import random
from flask import Flask, render_template
from config import config_by_name
from extensions import db, login_manager
from models import User, ChargingSession, BatteryReading, Notification, UserSettings, PredictionResult


def create_app(config_name=None):
    """Factory to create and configure the Flask application."""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name['default']))

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Register Blueprints
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.prediction import prediction_bp
    from routes.analytics import analytics_bp
    from routes.history import history_bp
    from routes.notifications import notifications_bp
    from routes.settings import settings_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(prediction_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(admin_bp)

    # Global context processors for Jinja templates
    @app.context_processor
    def inject_global_data():
        return {
            'current_year': datetime.utcnow().year,
            'app_name': 'ChargeSense'
        }

    # Auto-login demo user so visitors immediately enter the live dashboard without a login screen
    @app.before_request
    def auto_login_demo_user():
        from flask_login import current_user, login_user
        from flask import request
        if not current_user.is_authenticated:
            # Let visitors explicitly navigate to /login and /register if they want to switch accounts
            if request.endpoint in ('auth.login', 'auth.register', 'static'):
                return
            demo_user = User.query.filter_by(username='demo').first()
            if not demo_user:
                demo_user = User.query.first()
            if demo_user:
                login_user(demo_user, remember=True)

    # Custom Error Handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('base.html', error_code=403, error_title="Access Forbidden",
                               error_msg="You do not have administrative privileges to access this resource."), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('base.html', error_code=404, error_title="Page Not Found",
                               error_msg="The requested page could not be located on the ChargeSense server."), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('base.html', error_code=500, error_title="Internal Server Error",
                               error_msg="An unexpected error occurred while processing the telemetry pipeline."), 500

    # Auto-initialize database tables and demonstration seed data
    with app.app_context():
        try:
            db.create_all()
            _migrate_sqlite_schema()
            _seed_initial_data()
        except Exception as e:
            app.logger.warning(f"Database initialization notice: {e}")

    return app


def _migrate_sqlite_schema():
    """Ensures newly added columns exist in SQLite/MySQL databases without data loss."""
    from sqlalchemy import text
    migrations = [
        ("users", "phone_number", "VARCHAR(25) DEFAULT ''"),
        ("charging_sessions", "sms_sent", "BOOLEAN DEFAULT 0"),
        ("charging_sessions", "sms_status", "VARCHAR(30) DEFAULT 'none'"),
        ("user_settings", "phone_number", "VARCHAR(25) DEFAULT ''"),
        ("user_settings", "sms_alerts_enabled", "BOOLEAN DEFAULT 1"),
        ("user_settings", "buzzer_alerts_enabled", "BOOLEAN DEFAULT 1"),
    ]
    try:
        with db.engine.connect() as conn:
            for table, column, col_type in migrations:
                try:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
                    conn.commit()
                except Exception:
                    pass
    except Exception:
        pass


def _seed_initial_data():
    """Seeds initial demonstration accounts and historical charging sessions."""
    # 1. Seed Admin user
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@chargesense.ai',
            full_name='System Administrator',
            is_admin=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.flush()

        admin_settings = UserSettings(user_id=admin.id, theme='dark')
        db.session.add(admin_settings)

    # 2. Seed Demo student user
    demo_user = User.query.filter_by(username='demo').first()
    if not demo_user:
        demo_user = User(
            username='demo',
            email='saipavan9560@gmail.com',
            full_name='ChargeSense',
            phone_number='6300286628',
            is_admin=False
        )
        demo_user.set_password('demo123')
        db.session.add(demo_user)
        db.session.flush()

        demo_settings = UserSettings(
            user_id=demo_user.id,
            phone_number='6300286628',
            default_target_percentage=80.0,
            theme='light',
            sms_alerts_enabled=True,
            buzzer_alerts_enabled=True
        )
        db.session.add(demo_settings)
    else:
        demo_user.full_name = 'ChargeSense'
        # Ensure email and phone are set for presentation
        if not demo_user.email or demo_user.email == 'demo@chargesense.ai':
            demo_user.email = 'demo@gmail.com'
        if not demo_user.phone_number:
            demo_user.phone_number = '6300286628'
        if demo_user.settings and not demo_user.settings.phone_number:
            demo_user.settings.phone_number = '6300286628'
        db.session.commit()

        # Seed realistic historical charging sessions for demo user
        base_time = datetime.utcnow() - timedelta(days=5)
        sample_scenarios = [
            (20.0, 80.0, 80.0, 'normal', 1.0, 60.0, 'completed'),
            (15.0, 65.0, 80.0, 'fast', 2.0, 25.0, 'stopped'),
            (30.0, 100.0, 100.0, 'normal', 1.0, 72.0, 'completed'),
            (45.0, 90.0, 90.0, 'slow', 0.5, 94.0, 'completed'),
            (10.0, 85.0, 85.0, 'fast', 2.0, 39.0, 'completed'),
        ]

        for idx, (s_pct, e_pct, t_pct, speed, rate, dur, status) in enumerate(sample_scenarios):
            s_time = base_time + timedelta(days=idx, hours=random.randint(9, 18))
            e_time = s_time + timedelta(minutes=dur)
            session = ChargingSession(
                user_id=demo_user.id,
                start_percentage=s_pct,
                end_percentage=e_pct,
                target_percentage=t_pct,
                charging_speed=speed,
                charging_rate=rate,
                duration_minutes=dur,
                status=status,
                start_time=s_time,
                end_time=e_time,
                created_at=s_time
            )
            db.session.add(session)
            db.session.flush()

            # Add battery readings for this session
            num_readings = 5
            for r_idx in range(num_readings):
                fraction = r_idx / (num_readings - 1)
                r_pct = round(s_pct + fraction * (e_pct - s_pct), 1)
                r_time = s_time + timedelta(minutes=(fraction * dur))
                reading = BatteryReading(
                    session_id=session.id,
                    user_id=demo_user.id,
                    percentage=r_pct,
                    voltage=round(3.65 + 0.5 * (r_pct / 100), 2),
                    temperature=round(29.0 + random.uniform(0.5, 3.5), 1),
                    charging_rate=rate,
                    status='charging',
                    timestamp=r_time
                )
                db.session.add(reading)

            # Add prediction result
            pred = PredictionResult(
                user_id=demo_user.id,
                session_id=session.id,
                current_percentage=s_pct,
                target_percentage=t_pct,
                charging_speed=speed,
                baseline_predicted_minutes=round((t_pct - s_pct) / rate, 1),
                ml_predicted_minutes=dur,
                actual_minutes=dur,
                error_minutes=round(abs(dur - ((t_pct - s_pct) / rate)), 1),
                created_at=s_time
            )
            db.session.add(pred)

        # Seed sample notifications
        notif1 = Notification(
            user_id=demo_user.id,
            title='Demo Session Initialized',
            message='Historical charging sessions and machine learning metrics have been populated.',
            notification_type='info',
            is_read=True
        )
        notif2 = Notification(
            user_id=demo_user.id,
            title='Target Reached in Session #5',
            message='Battery reached target threshold of 85.0% in 39 minutes.',
            notification_type='success',
            is_read=False
        )
        db.session.add(notif1)
        db.session.add(notif2)

    db.session.commit()


# Main entry point for `python app.py`
app = create_app()

if __name__ == '__main__':
    host = os.getenv('HOST', '127.0.0.1')
    port = int(os.getenv('PORT', 5000))
    debug = bool(int(os.getenv('FLASK_DEBUG', 1)))
    print(f"ChargeSense server starting at http://{host}:{port}/")
    app.run(host=host, port=port, debug=debug)
