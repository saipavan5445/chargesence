"""
ChargeSense Main Dashboard Routes & Telemetry API
Handles dashboard view rendering, real-time telemetry polling,
simulation lifecycle controls, and IoT ingestion.
"""

import os
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user, login_user
from extensions import db
from models import User, ChargingSession, BatteryReading, Notification, UserSettings, SMSNotification
from services.battery_simulator import simulator_service
from services.buzzer_service import buzzer_service
from services.sms_service import sms_service
from services.email_service import email_service

dashboard_bp = Blueprint('dashboard', __name__)


def _ensure_active_user():
    """Ensures an authenticated session is active. Auto-authenticates demo account so the website opens immediately without a login barrier."""
    if not current_user.is_authenticated:
        demo_user = User.query.filter_by(username='demo').first()
        if not demo_user:
            demo_user = User.query.first()
        if demo_user:
            login_user(demo_user, remember=True)
    return current_user


@dashboard_bp.route('/')
def index():
    """Renders the main live battery telemetry dashboard directly on root URL."""
    return dashboard_view()


@dashboard_bp.route('/dashboard')
def dashboard_view():
    """Renders the main SaaS-style analytics dashboard directly without requiring login."""
    _ensure_active_user()
    user_id = current_user.id if current_user.is_authenticated else 1

    # Compute aggregate session statistics
    all_sessions = ChargingSession.query.filter_by(user_id=user_id).all()
    total_sessions = len(all_sessions)
    completed_sessions = sum(1 for s in all_sessions if s.status == 'completed')

    # Get recent sessions (descending for table, ascending for chronological charts)
    recent_sessions = ChargingSession.query.filter_by(user_id=user_id)\
        .order_by(ChargingSession.id.desc()).limit(5).all()
    chart_sessions = ChargingSession.query.filter_by(user_id=user_id)\
        .order_by(ChargingSession.id.asc()).all()[-6:]

    # Calculate real Donut Share breakdown based on user's past data
    if all_sessions:
        optimal_cnt = sum(1 for s in all_sessions if 75 <= s.target_percentage <= 85)
        high_cnt = sum(1 for s in all_sessions if s.target_percentage > 85)
        partial_cnt = sum(1 for s in all_sessions if s.target_percentage < 75 or s.status != 'completed')
        total_valid = max(1, optimal_cnt + high_cnt + partial_cnt)
        donut_optimal = round((optimal_cnt / total_valid) * 100)
        donut_high = round((high_cnt / total_valid) * 100)
        donut_partial = max(0, 100 - donut_optimal - donut_high)
    else:
        donut_optimal, donut_high, donut_partial = 75, 15, 10

    # Chart 1: Trajectory data from recent sessions
    if chart_sessions:
        history_labels = [f"Session #{s.id}" for s in chart_sessions]
        history_end_pcts = [s.end_percentage if s.end_percentage > 0 else s.start_percentage for s in chart_sessions]
        history_durations = [s.duration_minutes for s in chart_sessions]
        history_targets = [s.target_percentage for s in chart_sessions]
    else:
        history_labels = ['Session #1', 'Session #2', 'Session #3', 'Session #4', 'Session #5']
        history_end_pcts = [80.0, 75.0, 90.0, 85.0, 80.0]
        history_durations = [45.0, 30.0, 65.0, 40.0, 35.0]
        history_targets = [80.0, 80.0, 90.0, 85.0, 80.0]

    # Chart 2: Recent Battery Readings for live progression curve
    recent_readings = BatteryReading.query.filter_by(user_id=user_id)\
        .order_by(BatteryReading.id.desc()).limit(12).all()
    if recent_readings:
        readings_chron = list(reversed(recent_readings))
        live_labels = [r.timestamp.strftime('%H:%M') for r in readings_chron]
        live_pcts = [r.percentage for r in readings_chron]
    else:
        live_labels = ['-15m', '-12m', '-9m', '-6m', '-3m', 'Now']
        curr_p = simulator_service.get_user_state(user_id)['current_percentage']
        live_pcts = [max(5, curr_p - 15), max(5, curr_p - 12), max(5, curr_p - 8),
                     max(5, curr_p - 5), max(5, curr_p - 2), curr_p]

    dashboard_analytics = {
        'donut': {
            'optimal_pct': donut_optimal,
            'high_pct': donut_high,
            'partial_pct': donut_partial,
            'total_sessions': total_sessions,
            'center_label': f"{donut_optimal}%",
            'center_sub': 'Safe Cutoff Rate'
        },
        'trajectory': {
            'labels': history_labels,
            'end_percentages': history_end_pcts,
            'durations': history_durations,
            'targets': history_targets
        },
        'live_curve': {
            'labels': live_labels,
            'percentages': live_pcts
        }
    }

    # Get active state
    telemetry = simulator_service.get_telemetry(user_id)

    # User settings default target & SMS configuration
    default_target = 80.0
    sms_alerts_enabled = True
    if current_user.is_authenticated and current_user.settings:
        default_target = current_user.settings.default_target_percentage
        sms_alerts_enabled = current_user.settings.sms_alerts_enabled

    # Latest SMS logs from MySQL
    sms_logs = SMSNotification.query.filter_by(user_id=user_id)\
        .order_by(SMSNotification.created_at.desc()).limit(5).all()
    twilio_configured = sms_service.is_twilio_configured()
    email_configured = email_service.is_configured()
    notification_email = os.getenv('NOTIFICATION_EMAIL') or (current_user.email if current_user.is_authenticated and current_user.email else 'saipavan9560@gmail.com')

    return render_template(
        'dashboard.html',
        telemetry=telemetry,
        total_sessions=total_sessions,
        completed_sessions=completed_sessions,
        recent_sessions=recent_sessions,
        default_target=default_target,
        sms_logs=sms_logs,
        sms_alerts_enabled=sms_alerts_enabled,
        twilio_configured=twilio_configured,
        email_configured=email_configured,
        notification_email=notification_email,
        dashboard_analytics=dashboard_analytics
    )


@dashboard_bp.route('/landing')
@dashboard_bp.route('/about')
def landing_view():
    """Optional overview page for project presentation."""
    return render_template('landing.html')


@dashboard_bp.route('/api/telemetry')
@login_required
def get_telemetry():
    """
    REST API endpoint for live battery telemetry.
    Called periodically by frontend JavaScript without page refresh.
    Also advances active simulations by one tick.
    """
    telemetry = simulator_service.tick(current_user)
    return jsonify({
        'success': True,
        'data': telemetry
    })


@dashboard_bp.route('/api/simulation/start', methods=['POST'])
@login_required
def start_simulation():
    """Starts or resumes a simulated charging session."""
    data = request.get_json() or {}
    target = data.get('target_percentage', 80.0)
    speed = data.get('charging_speed', 'normal')

    telemetry = simulator_service.start_simulation(current_user, target, speed)
    return jsonify({
        'success': True,
        'message': f"Charging started ({speed.upper()} mode, target: {target}%)",
        'data': telemetry
    })


@dashboard_bp.route('/api/simulation/stop', methods=['POST'])
@login_required
def stop_simulation():
    """Stops the active charging session."""
    telemetry = simulator_service.stop_simulation(current_user)
    return jsonify({
        'success': True,
        'message': "Charging stopped.",
        'data': telemetry
    })


@dashboard_bp.route('/api/simulation/target', methods=['POST'])
@login_required
def update_target():
    """Immediately updates target battery percentage and enforces cut-off if already reached."""
    data = request.get_json() or {}
    target = data.get('target_percentage')
    if target is not None:
        target = max(10.0, min(100.0, float(target)))
        state = simulator_service.get_user_state(current_user.id)
        state['target_percentage'] = target

        # If current level is already at or above new target, auto-complete and stop charging!
        if state['current_percentage'] >= target:
            state['status'] = 'completed'
            if state.get('active_session_id'):
                session = ChargingSession.query.get(state['active_session_id'])
                if session and session.status == 'in_progress':
                    session.status = 'completed'
                    session.end_time = datetime.utcnow()
                    session.end_percentage = state['current_percentage']
                    db.session.commit()

        return jsonify({
            'success': True,
            'message': f"Target set to {target}%.",
            'data': simulator_service.get_telemetry(current_user.id)
        })
    return jsonify({'success': False, 'error': 'Invalid target percentage'}), 400


@dashboard_bp.route('/api/simulation/discharge', methods=['POST'])
@login_required
def discharge_simulation():
    """Simulates device unplugged and battery discharging."""
    telemetry = simulator_service.trigger_discharge(current_user)
    return jsonify({
        'success': True,
        'message': "Device unplugged. Discharging simulation active.",
        'data': telemetry
    })


@dashboard_bp.route('/api/simulation/reset', methods=['POST'])
@login_required
def reset_simulation():
    """Resets battery percentage to low value for testing."""
    data = request.get_json() or {}
    percentage = data.get('percentage', 25.0)

    telemetry = simulator_service.reset_battery(current_user, percentage)
    return jsonify({
        'success': True,
        'message': f"Battery reset to {percentage}% for demonstration.",
        'data': telemetry
    })


@dashboard_bp.route('/api/simulation/fast_forward', methods=['POST'])
def fast_forward_simulation():
    """Jumps battery percentage to near target (e.g. 78% for 80% target) in turbo speed for instant cut-off test."""
    _ensure_active_user()
    state = simulator_service.get_user_state(current_user.id)
    target = state.get('target_percentage', 80.0)
    jump_pct = max(10.0, target - 2.0)
    simulator_service.reset_battery(current_user, jump_pct)
    state['status'] = 'charging'
    state['charging_speed'] = 'turbo'
    state['telemetry_source'] = 'simulation'
    telemetry = simulator_service.get_telemetry(current_user.id)
    return jsonify({
        'success': True,
        'message': f"Fast-forwarded to {jump_pct}% in Turbo mode! Cutoff alert will trigger in moments.",
        'data': telemetry
    })


@dashboard_bp.route('/api/battery/mode', methods=['POST'])
@login_required
def set_battery_mode():
    """Toggles telemetry between live laptop hardware battery and simulation."""
    data = request.get_json() or {}
    source = data.get('source', 'laptop')  # 'laptop' or 'simulation'

    telemetry = simulator_service.set_telemetry_source(current_user.id, source)
    mode_name = "Physical Laptop Battery (Live)" if source == 'laptop' else "Simulation Mode"
    return jsonify({
        'success': True,
        'message': f"Switched to {mode_name}.",
        'data': telemetry
    })


@dashboard_bp.route('/api/buzzer/test', methods=['POST'])
@login_required
def test_buzzer():
    """Triggers an immediate 2.5-second test of the hardware speaker buzzer."""
    buzzer_service.play_test_beep(duration_sec=2.5)
    return jsonify({
        'success': True,
        'message': 'Hardware buzzer alarm sounding through laptop speakers!'
    })


@dashboard_bp.route('/api/buzzer/stop', methods=['POST'])
@login_required
def stop_buzzer_endpoint():
    """Stops the active hardware buzzer."""
    buzzer_service.stop_buzzer()
    if current_user.is_authenticated:
        state = simulator_service.get_user_state(current_user.id)
        state['buzzer_muted'] = True
    return jsonify({
        'success': True,
        'message': 'Hardware buzzer silenced.'
    })


@dashboard_bp.route('/api/user/phone', methods=['POST'])
@login_required
def update_phone_number():
    """Quickly saves or updates the registered phone number directly from the dashboard."""
    data = request.get_json() or {}
    phone = data.get('phone_number', '').strip()
    if not phone:
        return jsonify({'success': False, 'error': 'Phone number cannot be empty.'}), 400

    current_user.phone_number = phone
    if current_user.settings:
        current_user.settings.phone_number = phone
    else:
        settings = UserSettings(user_id=current_user.id, phone_number=phone)
        db.session.add(settings)
    db.session.commit()

    return jsonify({
        'success': True,
        'phone_number': phone,
        'message': f'Registered phone number updated to {phone}!'
    })


@dashboard_bp.route('/api/user/email', methods=['POST'])
def update_user_email():
    """Updates user notification email address."""
    _ensure_active_user()
    data = request.get_json(silent=True) or {}
    email = data.get('email', '').strip()
    if not email or '@' not in email:
        return jsonify({'success': False, 'error': 'Please provide a valid email address.'}), 400

    user = current_user if current_user.is_authenticated else User.query.filter_by(username='demo').first()
    if user:
        try:
            user.email = email
            db.session.commit()
        except Exception:
            db.session.rollback()

    user_id = user.id if user else 1
    state = simulator_service.get_user_state(user_id)
    state['notification_email'] = email
    os.environ['NOTIFICATION_EMAIL'] = email

    return jsonify({
        'success': True,
        'email': email,
        'message': f'Notification email updated to {email}!'
    })


@dashboard_bp.route('/api/email/test', methods=['POST'])
def test_email_api():
    """Sends a test email to the user's registered address."""
    _ensure_active_user()
    user = current_user if current_user.is_authenticated else User.query.filter_by(username='demo').first()
    data = request.get_json(silent=True) or {}
    to_email = data.get('email') or os.getenv('NOTIFICATION_EMAIL') or (user.email if user else 'saipavan9560@gmail.com')
    res = email_service.send_test_email(user, to_email)
    return jsonify(res)


@dashboard_bp.route('/api/email/toggle', methods=['POST'])
def toggle_email():
    """Toggles email notifications on or off."""
    _ensure_active_user()
    user = current_user if current_user.is_authenticated else User.query.filter_by(username='demo').first()
    data = request.get_json(silent=True) or {}
    settings = user.settings if user else None
    if not settings and user:
        settings = UserSettings(user_id=user.id)
        db.session.add(settings)

    enabled = data.get('enabled', True)
    if settings and hasattr(settings, 'email_alerts_enabled'):
        settings.email_alerts_enabled = bool(enabled)
        db.session.commit()

    return jsonify({
        'success': True,
        'email_alerts_enabled': bool(enabled),
        'message': f"Automatic email notifications {'enabled' if enabled else 'disabled'}."
    })


@dashboard_bp.route('/api/email/smtp-credentials', methods=['POST'])
def save_smtp_credentials():
    """Saves SMTP credentials into .env for live Gmail/SMTP dispatch."""
    _ensure_active_user()
    data = request.get_json(silent=True) or {}
    host = data.get('smtp_host', 'smtp.gmail.com').strip()
    port = data.get('smtp_port', '587').strip()
    user_email = data.get('smtp_user', '').strip()
    password = data.get('smtp_password', '').strip().replace(' ', '')

    basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    env_path = os.path.join(basedir, '.env')

    env_lines = []
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            env_lines = f.readlines()

    updates = {
        'EMAIL_SMTP_HOST': host,
        'EMAIL_SMTP_PORT': port,
        'EMAIL_SMTP_USER': user_email,
        'EMAIL_SMTP_PASSWORD': password
    }
    updated = set()
    new_lines = []
    for line in env_lines:
        replaced = False
        for k, v in updates.items():
            if line.startswith(f"{k}="):
                new_lines.append(f"{k}={v}\n")
                updated.add(k)
                replaced = True
                break
        if not replaced:
            new_lines.append(line)

    for k, v in updates.items():
        if k not in updated:
            new_lines.append(f"{k}={v}\n")

    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    for k, v in updates.items():
        os.environ[k] = v

    email_service.reload_config()

    test_res = email_service.send_test_email(current_user, user_email or current_user.email)

    return jsonify({
        'success': True,
        'message': 'SMTP configuration updated successfully!',
        'is_live': email_service.is_configured(),
        'test_result': test_res
    })


@dashboard_bp.route('/api/alerts/test-full', methods=['POST'])
def test_full_alert():
    """Simultaneously triggers the physical hardware buzzer and sends test email & mobile notification."""
    _ensure_active_user()
    data = request.get_json(silent=True) or {}
    phone = data.get('phone_number') or current_user.phone_number or (current_user.settings.phone_number if current_user.settings else '')

    # 1. Trigger hardware buzzer
    buzzer_service.play_test_beep(duration_sec=2.5)

    # 2. Dispatch SMS / Alert
    sms_res = sms_service.send_test_sms(current_user, phone)

    # 3. Dispatch Email Alert
    email_res = email_service.send_test_email(current_user)

    return jsonify({
        'success': True,
        'buzzer_triggered': True,
        'sms_result': sms_res,
        'email_result': email_res,
        'message': f'Hardware buzzer alarm tested and email notification dispatched to {current_user.email}!'
    })


@dashboard_bp.route('/api/sms/toggle', methods=['POST'])
@login_required
def toggle_sms():
    """Toggles automatic SMS notifications on or off for the authenticated user."""
    data = request.get_json() or {}
    settings = current_user.settings
    if not settings:
        settings = UserSettings(user_id=current_user.id)
        db.session.add(settings)

    if 'enabled' in data:
        settings.sms_alerts_enabled = bool(data['enabled'])
    else:
        settings.sms_alerts_enabled = not settings.sms_alerts_enabled

    db.session.commit()
    status_str = "enabled" if settings.sms_alerts_enabled else "disabled"
    return jsonify({
        'success': True,
        'sms_alerts_enabled': settings.sms_alerts_enabled,
        'message': f"Automatic SMS notifications {status_str}."
    })


@dashboard_bp.route('/api/sms/logs')
@login_required
def get_sms_logs():
    """Retrieves recent SMS dispatch logs from MySQL for the user."""
    logs = SMSNotification.query.filter_by(user_id=current_user.id)\
        .order_by(SMSNotification.created_at.desc()).limit(10).all()
    return jsonify({
        'success': True,
        'logs': [log.to_dict() for log in logs]
    })


@dashboard_bp.route('/api/sms/test', methods=['POST'])
@login_required
def test_sms_api():
    """Directly tests Twilio SMS dispatch to registered number."""
    data = request.get_json() or {}
    phone = data.get('phone_number') or current_user.phone_number or (current_user.settings.phone_number if current_user.settings else '')
    res = sms_service.send_test_sms(current_user, phone)
    return jsonify(res)


@dashboard_bp.route('/api/sms/twilio-credentials', methods=['POST'])
@login_required
def save_twilio_credentials():
    """Saves real Twilio credentials into .env and tests connection."""
    import os
    data = request.get_json() or {}
    sid = data.get('account_sid', '').strip()
    token = data.get('auth_token', '').strip()
    from_number = data.get('phone_number', '').strip()
    callmebot_key = data.get('callmebot_key', '').strip()

    basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    env_path = os.path.join(basedir, '.env')

    env_lines = []
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            env_lines = f.readlines()

    updated = set()
    new_lines = []
    for line in env_lines:
        if line.startswith('TWILIO_ACCOUNT_SID='):
            new_lines.append(f"TWILIO_ACCOUNT_SID={sid}\n")
            updated.add('TWILIO_ACCOUNT_SID')
        elif line.startswith('TWILIO_AUTH_TOKEN='):
            new_lines.append(f"TWILIO_AUTH_TOKEN={token}\n")
            updated.add('TWILIO_AUTH_TOKEN')
        elif line.startswith('TWILIO_PHONE_NUMBER='):
            new_lines.append(f"TWILIO_PHONE_NUMBER={from_number}\n")
            updated.add('TWILIO_PHONE_NUMBER')
        elif line.startswith('CALLMEBOT_API_KEY='):
            new_lines.append(f"CALLMEBOT_API_KEY={callmebot_key}\n")
            updated.add('CALLMEBOT_API_KEY')
        else:
            new_lines.append(line)

    if 'TWILIO_ACCOUNT_SID' not in updated:
        new_lines.append(f"TWILIO_ACCOUNT_SID={sid}\n")
    if 'TWILIO_AUTH_TOKEN' not in updated:
        new_lines.append(f"TWILIO_AUTH_TOKEN={token}\n")
    if 'TWILIO_PHONE_NUMBER' not in updated:
        new_lines.append(f"TWILIO_PHONE_NUMBER={from_number}\n")
    if callmebot_key and 'CALLMEBOT_API_KEY' not in updated:
        new_lines.append(f"CALLMEBOT_API_KEY={callmebot_key}\n")

    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    os.environ['TWILIO_ACCOUNT_SID'] = sid
    os.environ['TWILIO_AUTH_TOKEN'] = token
    os.environ['TWILIO_PHONE_NUMBER'] = from_number
    if callmebot_key:
        os.environ['CALLMEBOT_API_KEY'] = callmebot_key

    sms_service.reload_config()

    target_phone = current_user.phone_number or (current_user.settings.phone_number if current_user.settings else '')
    test_result = None
    if target_phone:
        test_result = sms_service.send_test_sms(current_user, target_phone)

    return jsonify({
        'success': True,
        'message': 'Twilio credentials updated and tested!',
        'is_live': sms_service.is_twilio_configured(),
        'test_result': test_result
    })


@dashboard_bp.route('/api/iot/telemetry', methods=['POST'])
def iot_telemetry():
    """
    Future IoT Integration endpoint.
    Allows microcontrollers (e.g. ESP32, Arduino with INA219 sensor)
    to transmit hardware battery voltage, current, and SoC percentage.
    """
    data = request.get_json() or {}
    device_key = request.headers.get('X-Device-API-Key') or data.get('api_key')

    # In production, validate device_key to user mapping
    percentage = data.get('percentage')
    voltage = data.get('voltage', 3.85)
    temperature = data.get('temperature', 30.0)
    charging = data.get('charging', True)

    if percentage is None:
        return jsonify({'error': 'Missing required field: percentage'}), 400

    return jsonify({
        'status': 'received',
        'message': 'IoT hardware telemetry logged successfully',
        'timestamp': datetime.utcnow().isoformat(),
        'echo': {
            'percentage': percentage,
            'voltage': voltage,
            'temperature': temperature,
            'charging': charging
        }
    }), 200
