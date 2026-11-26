"""
ChargeSense User Settings Routes
Manages personal preferences, simulation defaults, theme selection,
and profile updates.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import UserSettings
from services.sms_service import sms_service

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/settings')
@login_required
def settings_view():
    """Renders the settings page."""
    settings = current_user.settings
    if not settings:
        settings = UserSettings(user_id=current_user.id)
        db.session.add(settings)
        db.session.commit()

    return render_template('settings.html', settings=settings)


@settings_bp.route('/settings/update', methods=['POST'])
@login_required
def update_settings():
    """Updates profile credentials and simulation configurations."""
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip().lower()
    phone_number = request.form.get('phone_number', '').strip()
    target_pct = request.form.get('default_target_percentage', type=float)
    speed = request.form.get('default_charging_speed', 'normal')
    speed_mult = request.form.get('simulation_speed_multiplier', 1.0, type=float)
    browser_notifs = bool(request.form.get('browser_notifications_enabled'))
    sms_notifs = bool(request.form.get('sms_alerts_enabled'))
    buzzer_enabled = bool(request.form.get('buzzer_alerts_enabled'))
    theme = request.form.get('theme', 'dark')

    # Update User model
    if full_name:
        current_user.full_name = full_name

    if email and email != current_user.email:
        current_user.email = email

    current_user.phone_number = phone_number

    # Update password if provided
    new_password = request.form.get('new_password', '').strip()
    if new_password:
        if len(new_password) < 6:
            flash('New password must be at least 6 characters long.', 'danger')
            return redirect(url_for('settings.settings_view'))
        current_user.set_password(new_password)
        flash('Password updated successfully.', 'info')

    # Update UserSettings
    settings = current_user.settings
    if not settings:
        settings = UserSettings(user_id=current_user.id)
        db.session.add(settings)

    if target_pct is not None:
        settings.default_target_percentage = max(10.0, min(100.0, target_pct))
    settings.default_charging_speed = speed
    settings.simulation_speed_multiplier = max(0.5, min(5.0, speed_mult))
    settings.browser_notifications_enabled = browser_notifs
    settings.phone_number = phone_number
    settings.sms_alerts_enabled = sms_notifs
    settings.buzzer_alerts_enabled = buzzer_enabled
    settings.theme = theme

    db.session.commit()
    flash('Settings and registered phone number saved successfully.', 'success')
    return redirect(url_for('settings.settings_view'))


@settings_bp.route('/api/settings/test-sms', methods=['POST'])
@login_required
def test_sms():
    """Sends an immediate test SMS to the provided or saved phone number."""
    data = request.get_json() or {}
    phone = data.get('phone_number', '').strip() or current_user.phone_number

    if not phone:
        return jsonify({'success': False, 'error': 'Please enter a valid phone number.'}), 400

    result = sms_service.send_test_sms(current_user, phone)
    return jsonify({
        'success': True,
        'message': f"Alert dispatched to {result['phone']} ({result['gateway']}).",
        'data': result
    })


@settings_bp.route('/api/settings/theme', methods=['POST'])
@login_required
def toggle_theme():
    """Quick asynchronous endpoint to toggle theme between dark and light."""
    data = request.get_json() or {}
    theme = data.get('theme', 'dark')
    if theme in ['dark', 'light']:
        if current_user.settings:
            current_user.settings.theme = theme
            db.session.commit()
        return jsonify({'success': True, 'theme': theme})
    return jsonify({'success': False, 'error': 'Invalid theme'}), 400
