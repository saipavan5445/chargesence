"""
ChargeSense Authentication Routes
Manages user registration, login, logout, profile viewing, and session handling.
Supports real Gmail and email addresses with secure password authentication.
"""

import re
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from models import User, UserSettings, Notification

auth_bp = Blueprint('auth', __name__)

# Standard RFC-compliant email regex pattern (accepts all real Gmail & email addresses)
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page and handler. Accepts real Gmail addresses."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        full_name = request.form.get('full_name', '').strip()
        phone_number = request.form.get('phone_number', '').strip()

        # If username not provided, auto-generate from Gmail prefix
        if not username and email and '@' in email:
            username = email.split('@')[0]
            # Ensure at least 3 chars
            if len(username) < 3:
                username = f"{username}_{abs(hash(email)) % 1000}"

        # Real Email Validation
        if not email or not EMAIL_REGEX.match(email):
            flash('Please enter a valid Gmail or email address (e.g., yourname@gmail.com).', 'warning')
            return render_template('register.html')

        if not password:
            flash('Password is required.', 'danger')
            return render_template('register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match. Please verify both password fields.', 'danger')
            return render_template('register.html')

        if len(username) < 3:
            flash('Username must be at least 3 characters long.', 'danger')
            return render_template('register.html')

        # Check existing email
        if User.query.filter_by(email=email).first():
            flash('This Gmail / email address is already registered. Please sign in.', 'danger')
            return render_template('register.html')

        # Check existing username (if conflict, append random suffix)
        if User.query.filter_by(username=username).first():
            username = f"{username}_{abs(hash(email)) % 1000}"

        # Create new user
        new_user = User(
            username=username,
            email=email,
            full_name=full_name or username.capitalize(),
            phone_number=phone_number,
            is_admin=False
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.flush()

        # Create default user settings
        settings = UserSettings(
            user_id=new_user.id,
            phone_number=phone_number,
            default_target_percentage=80.0,
            default_charging_speed='normal',
            theme='light',
            sms_alerts_enabled=True,
            buzzer_alerts_enabled=True
        )
        db.session.add(settings)

        # Welcome notification
        welcome_notif = Notification(
            user_id=new_user.id,
            title='Welcome to ChargeSense!',
            message='Your account is active. Real-time battery monitoring and SMS protection are ready.',
            notification_type='info'
        )
        db.session.add(welcome_notif)

        db.session.commit()

        login_user(new_user)
        flash(f'Account registered successfully! Welcome, {new_user.full_name or new_user.username}.', 'success')
        return redirect(url_for('dashboard.index'))

    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page and handler. Accepts Gmail / Email address and password."""
    if request.method == 'POST':
        # Accept either email or username_or_email field name
        login_input = (
            request.form.get('email') or 
            request.form.get('username_or_email') or 
            request.form.get('login_input') or 
            ''
        ).strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        if not login_input or not password:
            flash('Please enter your Gmail / email address and password.', 'warning')
            return render_template('login.html')

        # Check by email or username (case-insensitive)
        user = User.query.filter(
            (User.email.ilike(login_input)) | (User.username.ilike(login_input))
        ).first()

        # Also support demo aliases (e.g. demo@gmail.com -> demo)
        if not user and login_input in ['demo@gmail.com', 'demo']:
            user = User.query.filter_by(username='demo').first()
        elif not user and login_input in ['admin@gmail.com', 'admin']:
            user = User.query.filter_by(username='admin').first()

        if not user or not user.check_password(password):
            flash('Invalid Gmail / email address or password. Please try again.', 'danger')
            return render_template('login.html')

        login_user(user, remember=remember)
        flash(f'Welcome back, {user.full_name or user.username}!', 'success')

        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):
            return redirect(next_page)
        return redirect(url_for('dashboard.index'))

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Logs out the active user."""
    logout_user()
    flash('You have been logged out securely.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/api/auth/status')
def auth_status():
    """Returns current authentication state for frontend components."""
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': current_user.to_dict()
        })
    return jsonify({'authenticated': False})
