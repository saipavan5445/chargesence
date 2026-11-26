"""
ChargeSense Email Notification Service
Sends automated email alerts when the battery reaches the user's charging target.
Uses Python's built-in smtplib + Gmail App Password (or any SMTP server).
No external packages required — works out of the box.

Features:
1. Sends a rich HTML email when target SoC is reached
2. Enforces strictly ONE email per charging session
3. User can enable/disable email alerts in Settings
4. Falls back to in-app notification if no email configured
"""

import os
import smtplib
import ssl
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from extensions import db
from models import Notification, ChargingSession


class EmailService:
    """Sends SMTP email alerts for battery events."""

    def __init__(self):
        self.reload_config()

    def reload_config(self):
        """Loads SMTP credentials from environment variables."""
        self.smtp_host = os.getenv('EMAIL_SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('EMAIL_SMTP_PORT', '465'))
        self.smtp_user = os.getenv('EMAIL_SMTP_USER', 'saipavan9560@gmail.com').strip()
        self.smtp_password = os.getenv('EMAIL_SMTP_PASSWORD', 'mobxhfzfsmjexwxl').strip()
        self.sender_name = os.getenv('EMAIL_SENDER_NAME', 'ChargeSense Alert')

    def is_configured(self) -> bool:
        """Returns True if SMTP credentials are set in .env."""
        self.reload_config()
        return bool(self.smtp_user and self.smtp_password)

    def _send_in_thread(self, to_email: str, subject: str, html_body: str, text_body: str):
        """Sends email asynchronously so it never blocks the web request."""
        def _worker():
            try:
                self.reload_config()
                msg = MIMEMultipart('alternative')
                msg['Subject'] = subject
                msg['From'] = f"{self.sender_name} <{self.smtp_user}>"
                msg['To'] = to_email

                msg.attach(MIMEText(text_body, 'plain'))
                msg.attach(MIMEText(html_body, 'html'))

                ctx = ssl.create_default_context()
                # 1. Primary: Direct SSL on port 465 (works reliably on Gmail without TLS drop)
                try:
                    with smtplib.SMTP_SSL(self.smtp_host, 465, context=ctx) as server:
                        server.login(self.smtp_user, self.smtp_password)
                        server.sendmail(self.smtp_user, [e.strip() for e in to_email.split(',')], msg.as_string())
                        print(f"[ChargeSense Email] ✓ Live email dispatched via SSL 465 to {to_email}: {subject}")
                        return
                except Exception as e_ssl:
                    print(f"[ChargeSense Email] SSL 465 notice ({e_ssl}), trying STARTTLS 587...")

                # 2. Fallback: STARTTLS on port 587
                try:
                    with smtplib.SMTP(self.smtp_host, 587) as server:
                        server.ehlo()
                        server.starttls(context=ctx)
                        server.login(self.smtp_user, self.smtp_password)
                        server.sendmail(self.smtp_user, [e.strip() for e in to_email.split(',')], msg.as_string())
                        print(f"[ChargeSense Email] ✓ Live email dispatched via STARTTLS 587 to {to_email}: {subject}")
                except Exception as e_tls:
                    print(f"[ChargeSense Email] ✗ Both SSL and STARTTLS failed: {e_tls}")

            except Exception as e:
                print(f"[ChargeSense Email] ✗ Failed to send email to {to_email}: {e}")

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    def send_target_reached_alert(self, user, target_pct: float, current_pct: float, session_id: int = None) -> dict:
        """
        Sends an email alert when battery reaches target.
        Enforces:
        - User must have email_alerts_enabled
        - Strictly ONE email per charging session
        """
        self.reload_config()

        # 1. Check user email alert enabled
        if user.settings and not getattr(user.settings, 'email_alerts_enabled', True):
            print(f"[ChargeSense Email] Skipped: User '{user.username}' has email alerts disabled.")
            return {'success': False, 'status': 'disabled', 'skipped': True}

        # 2. Enforce one email per session
        if session_id:
            try:
                session = ChargingSession.query.get(session_id)
                if session and session.sms_sent:  # reuse sms_sent flag for email too
                    print(f"[ChargeSense Email] Skipped: Session #{session_id} already sent alert.")
                    return {'success': False, 'status': 'already_sent', 'skipped': True}
            except Exception as e:
                print(f"[ChargeSense Email DB] Warning: {e}")

        # 3. Determine recipient email
        to_email = (
            os.getenv('NOTIFICATION_EMAIL') or
            getattr(user, 'notification_email', '') or
            getattr(user, 'email', '') or
            'saipavan9560@gmail.com'
        ).strip()
        if not to_email:
            return {'success': False, 'status': 'no_email', 'error': 'No email address configured.'}

        # 4. Build message
        now_str = datetime.now().strftime('%d %b %Y, %I:%M %p')
        subject = f"⚡ ChargeSense Alert — Your battery target ({round(target_pct, 1)}%) has been reached. Please unplug your charger!"
        text_body = (
            f"ChargeSense Battery Alert\n\n"
            f"Your battery has reached {round(target_pct, 1)}%. Please unplug your charger.\n\n"
            f"Current Level: {round(current_pct, 1)}%\n"
            f"Target Set: {round(target_pct, 1)}%\n"
            f"Session ID: #{session_id}\n"
            f"Time: {now_str}\n\n"
            f"Please unplug your charger now to protect battery health.\n\n"
            f"— ChargeSense Intelligent Charging Prediction System"
        )
        html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8">
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #F2EDE5; margin: 0; padding: 0; }}
  .wrapper {{ max-width: 560px; margin: 32px auto; background: #fff; border-radius: 16px; overflow: hidden; box-shadow: 0 8px 32px rgba(44,44,43,0.12); }}
  .header {{ background: linear-gradient(135deg, #3B5B56 0%, #2B4440 100%); padding: 32px 36px; text-align: center; }}
  .header .icon {{ font-size: 2.4rem; margin-bottom: 8px; }}
  .header h1 {{ color: #fff; font-size: 1.5rem; margin: 0; letter-spacing: -0.02em; }}
  .header p {{ color: rgba(255,255,255,0.75); font-size: 0.85rem; margin: 6px 0 0; }}
  .body {{ padding: 32px 36px; }}
  .target-badge {{ display: inline-block; background: #D4943A; color: #1F332F; font-size: 2.2rem; font-weight: 800; padding: 10px 28px; border-radius: 50px; margin: 16px 0; letter-spacing: -0.03em; }}
  .info-row {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #EAE4DB; font-size: 0.88rem; }}
  .info-label {{ color: #8E8E89; font-weight: 600; text-transform: uppercase; font-size: 0.72rem; letter-spacing: 0.06em; }}
  .info-val {{ color: #2C2C2B; font-weight: 700; font-family: 'Courier New', monospace; }}
  .action-btn {{ display: block; width: 100%; text-align: center; background: #3B5B56; color: #fff !important; padding: 14px 0; border-radius: 10px; text-decoration: none; font-weight: 700; font-size: 1rem; margin-top: 24px; letter-spacing: 0.02em; }}
  .footer {{ background: #F2EDE5; padding: 18px 36px; text-align: center; font-size: 0.75rem; color: #8E8E89; }}
  .alert-box {{ background: #FFF3CD; border-left: 4px solid #D4943A; border-radius: 8px; padding: 14px 18px; margin: 20px 0; font-size: 0.88rem; color: #5A5A57; }}
</style>
</head>
<body>
<div class="wrapper">
  <div class="header">
    <div class="icon">⚡</div>
    <h1>ChargeSense Battery Alert</h1>
    <p>Intelligent Charging Prediction System</p>
  </div>
  <div class="body">
    <p style="color:#5A5A57;font-size:0.95rem;">Hi <strong style="color:#2C2C2B">{user.full_name or user.username}</strong>,</p>
    <p style="color:#5A5A57;font-size:0.88rem;">Your battery has reached your configured charging target. ChargeSense has stopped the simulated charging session automatically.</p>
    <div style="text-align:center;">
      <div class="target-badge">{round(target_pct, 1)}% Reached</div>
    </div>
    <div class="info-row" style="border-top: 1px solid #EAE4DB;">
      <span class="info-label">Current Battery</span>
      <span class="info-val">{round(current_pct, 1)}%</span>
    </div>
    <div class="info-row">
      <span class="info-label">Target Set</span>
      <span class="info-val">{round(target_pct, 1)}%</span>
    </div>
    <div class="info-row">
      <span class="info-label">Session ID</span>
      <span class="info-val">#{session_id or 'N/A'}</span>
    </div>
    <div class="info-row">
      <span class="info-label">Time</span>
      <span class="info-val">{now_str}</span>
    </div>
    <div class="alert-box">
      🔌 <strong>Action Required:</strong> Your battery has reached {round(target_pct, 1)}%. <strong>Please unplug your charger</strong> now to prevent unnecessary electrochemical stress and preserve battery cycle life.
    </div>
    <a href="http://127.0.0.1:5000/dashboard" class="action-btn">Open ChargeSense Dashboard</a>
  </div>
  <div class="footer">
    ChargeSense – Intelligent Charging Prediction &bull; Powered by CC-CV Battery Physics<br>
    This is an automated alert. 1 email per charging session.
  </div>
</div>
</body>
</html>"""

        # 5. Print terminal log regardless
        print("\n" + "=" * 70)
        print(f"  [CHARGESENSE EMAIL ALERT]")
        print(f"  Recipient : {to_email}")
        print(f"  Subject   : {subject}")
        print(f"  Session   : #{session_id}")
        print(f"  Configured: {self.is_configured()}")
        print("=" * 70 + "\n")

        # 6. Send (async) or simulate
        if self.is_configured():
            self._send_in_thread(to_email, subject, html_body, text_body)
            status = 'sent'
        else:
            status = 'simulated'
            print("[ChargeSense Email] SMTP not configured — running in simulated mode. Set EMAIL_SMTP_USER + EMAIL_SMTP_PASSWORD in .env to go live.")

        # 7. Mark session alert sent & create in-app notification
        try:
            if session_id:
                session = ChargingSession.query.get(session_id)
                if session:
                    session.sms_sent = True      # reuse flag
                    session.sms_status = status

            notif = Notification(
                user_id=user.id,
                title=f"Email Alert Dispatched to {to_email}",
                message=f"Battery reached {round(target_pct, 1)}%. Email notification sent to {to_email}.",
                notification_type='success' if status == 'sent' else 'info',
                is_read=False,
                created_at=datetime.utcnow()
            )
            db.session.add(notif)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"[ChargeSense Email DB] Error saving notification: {e}")

        return {
            'success': True,
            'email': to_email,
            'subject': subject,
            'status': status,
            'is_live': self.is_configured(),
            'session_id': session_id,
            'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        }

    def send_test_email(self, user, to_email: str = None) -> dict:
        """Sends a test email to verify SMTP configuration."""
        self.reload_config()
        recipient = (
            to_email or
            os.getenv('NOTIFICATION_EMAIL') or
            getattr(user, 'notification_email', '') or
            getattr(user, 'email', '') or
            'saipavan9560@gmail.com'
        ).strip()
        if not recipient:
            return {'success': False, 'error': 'No email address provided.'}

        subject = "⚡ ChargeSense — Email Alert Test"
        text_body = "ChargeSense email alert test successful. Your email notifications are configured correctly."
        html_body = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
body{{font-family:'Segoe UI',Arial,sans-serif;background:#F2EDE5;margin:0;padding:0;}}
.w{{max-width:520px;margin:32px auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 8px 32px rgba(44,44,43,0.12);}}
.h{{background:linear-gradient(135deg,#3B5B56,#2B4440);padding:28px;text-align:center;color:#fff;}}
.b{{padding:28px;text-align:center;}}
.ok{{display:inline-block;background:#4DA06E;color:#fff;padding:10px 24px;border-radius:50px;font-weight:700;font-size:1rem;margin:16px 0;}}
.f{{background:#F2EDE5;padding:14px;text-align:center;font-size:0.75rem;color:#8E8E89;}}
</style></head><body>
<div class="w">
<div class="h"><div style="font-size:2rem;">⚡</div><h1 style="margin:0;font-size:1.3rem;">ChargeSense</h1><p style="margin:4px 0 0;opacity:0.75;font-size:0.82rem;">Email Alert Test</p></div>
<div class="b">
<p style="color:#5A5A57;font-size:0.95rem;">Hi <strong style="color:#2C2C2B">{user.full_name or user.username}</strong>!</p>
<div class="ok">✓ Email Alerts Active</div>
<p style="color:#5A5A57;font-size:0.85rem;">Your ChargeSense email notifications are working correctly.<br>You will receive an alert at <strong>{recipient}</strong> when your battery reaches the charging target.</p>
</div>
<div class="f">ChargeSense – Intelligent Charging Prediction</div>
</div></body></html>"""

        if self.is_configured():
            self._send_in_thread(recipient, subject, html_body, text_body)
            status = 'sent'
        else:
            status = 'simulated'

        print(f"[ChargeSense Email Test] {'Sent' if status == 'sent' else 'Simulated'} to {recipient}")
        return {'success': True, 'email': recipient, 'status': status, 'is_live': self.is_configured()}


email_service = EmailService()
