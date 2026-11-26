"""
ChargeSense Automated Full-Stack Test Suite
Verifies all routes, database operations, predictions, telemetry,
authentication, and template rendering.
"""

import sys
import os

# Add chargesense root directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from extensions import db
from models import User, ChargingSession, BatteryReading, Notification, UserSettings, PredictionResult
from predictor import predictor


def run_tests():
    print("=" * 65)
    print("  RUNNING CHARGESENSE AUTOMATED VERIFICATION SUITE")
    print("=" * 65)

    app = create_app('testing')
    client = app.test_client()

    with app.app_context():
        db.create_all()

        # Test 1: Landing Page
        res = client.get('/')
        assert res.status_code == 200, f"Landing page failed: {res.status_code}"
        print("[PASS] 1. Landing page loaded successfully (HTTP 200)")

        # Test 2: Login Page
        res = client.get('/login')
        assert res.status_code == 200, f"Login page failed: {res.status_code}"
        print("[PASS] 2. Login page loaded successfully (HTTP 200)")

        # Test 3: Register Page
        res = client.get('/register')
        assert res.status_code == 200, f"Register page failed: {res.status_code}"
        print("[PASS] 3. Register page loaded successfully (HTTP 200)")

        # Test 4: Register New User
        res = client.post('/register', data={
            'username': 'tester',
            'email': 'tester@example.com',
            'full_name': 'Test Engineer',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        assert res.status_code == 200, f"Registration failed: {res.status_code}"
        user = User.query.filter_by(username='tester').first()
        assert user is not None, "User not found in database"
        assert user.check_password('password123'), "Password verification failed"
        print("[PASS] 4. User registration and secure hashing verified")

        # Test 5: Dashboard View
        res = client.get('/dashboard')
        assert res.status_code == 200, f"Dashboard view failed: {res.status_code}"
        assert b"Live Battery Monitor" in res.data, "Dashboard title missing"
        print("[PASS] 5. Main Dashboard rendered with telemetry (HTTP 200)")

        # Test 6: Telemetry REST API
        res = client.get('/api/telemetry')
        assert res.status_code == 200, f"Telemetry API failed: {res.status_code}"
        json_data = res.get_json()
        assert json_data['success'] is True, "Telemetry success flag missing"
        assert 'current_percentage' in json_data['data'], "Battery percentage missing"
        assert 'prediction' in json_data['data'], "Prediction bundle missing"
        print(f"[PASS] 6. Live Telemetry API returned {json_data['data']['current_percentage']}% SoC (HTTP 200)")

        # Switch to simulation mode for deterministic simulation test
        client.post('/api/battery/mode', json={'source': 'simulation'})

        # Test 7: Start Simulation API
        res = client.post('/api/simulation/start', json={
            'target_percentage': 90.0,
            'charging_speed': 'fast'
        })
        assert res.status_code == 200, f"Start simulation failed: {res.status_code}"
        start_json = res.get_json()
        assert start_json['data']['status'] == 'charging', "Status is not charging"
        assert start_json['data']['charging_speed'] == 'fast', "Charging speed mismatch"
        print("[PASS] 7. Start Simulation API created active session (HTTP 200)")

        # Test 8: Prediction Calculation API
        res = client.post('/api/predict', json={
            'current_percentage': 30.0,
            'target_percentage': 85.0,
            'charging_speed': 'normal',
            'save_record': True
        })
        assert res.status_code == 200, f"Prediction API failed: {res.status_code}"
        pred_json = res.get_json()
        assert pred_json['data']['baseline']['remaining_minutes'] == 55.0, "Baseline calculation incorrect"
        assert 'ml' in pred_json['data'], "ML prediction missing"
        print(f"[PASS] 8. Intelligent Prediction API: Baseline 55.0 min, ML {pred_json['data']['ml']['ml_minutes']} min (HTTP 200)")

        # Test 9: Analytics Chart Data API
        res = client.get('/api/analytics/charts')
        assert res.status_code == 200, f"Analytics charts failed: {res.status_code}"
        chart_json = res.get_json()
        assert 'timeline' in chart_json, "Timeline missing"
        assert 'scenario_curves' in chart_json, "Scenario curves missing"
        print("[PASS] 9. Analytics Chart.js data API verified (HTTP 200)")

        # Test 10: Charging History View & Pagination
        res = client.get('/history')
        assert res.status_code == 200, f"History view failed: {res.status_code}"
        print("[PASS] 10. Charging History view rendered successfully (HTTP 200)")

        # Test 11: Notifications Center
        res = client.get('/notifications')
        assert res.status_code == 200, f"Notifications view failed: {res.status_code}"
        print("[PASS] 11. Notification Center rendered successfully (HTTP 200)")

        # Test 12: User Settings View
        res = client.get('/settings')
        assert res.status_code == 200, f"Settings view failed: {res.status_code}"
        print("[PASS] 12. User Settings rendered successfully (HTTP 200)")

        # Test 13: Stop Simulation
        res = client.post('/api/simulation/stop')
        assert res.status_code == 200, f"Stop simulation failed: {res.status_code}"
        stop_json = res.get_json()
        assert stop_json['data']['status'] == 'stopped', "Status is not stopped"
        print("[PASS] 13. Stop Simulation API concluded session (HTTP 200)")

        # Test 14: CSV Export
        res = client.get('/history/export')
        assert res.status_code == 200, f"CSV export failed: {res.status_code}"
        assert res.mimetype == 'text/csv', "Incorrect MIME type for CSV"
        print("[PASS] 14. History CSV export verified (HTTP 200)")

        # Test 15: IoT Ingestion Endpoint
        res = client.post('/api/iot/telemetry', json={
            'api_key': 'DEMO-ESP32-DEVICE-KEY',
            'percentage': 74.5,
            'voltage': 4.02,
            'temperature': 33.1,
            'charging': True
        })
        assert res.status_code == 200, f"IoT API failed: {res.status_code}"
        iot_json = res.get_json()
        assert iot_json['status'] == 'received', "IoT status error"
        print("[PASS] 15. Future IoT ESP32 Telemetry endpoint verified (HTTP 200)")

        # Test 16: Admin View Access Control
        # User 'tester' is not admin -> must return 403
        res = client.get('/admin')
        assert res.status_code == 403, f"Non-admin allowed into admin console: {res.status_code}"
        print("[PASS] 16. Admin authorization check enforced (HTTP 403 for non-admin)")

        # Promote user to admin and test again
        user.is_admin = True
        db.session.commit()
        res = client.get('/admin')
        assert res.status_code == 200, f"Admin console failed for authorized admin: {res.status_code}"
        print("[PASS] 17. Admin console accessible for administrator (HTTP 200)")

        # Test 18: Quick Phone Number Registration API
        res = client.post('/api/user/phone', json={'phone_number': '+919876543210'})
        assert res.status_code == 200, f"Phone API failed: {res.status_code}"
        phone_json = res.get_json()
        assert phone_json['success'] is True, "Phone update failed"
        assert phone_json['phone_number'] == '+919876543210', "Phone mismatch"
        print("[PASS] 18. Quick Phone Number Registration API verified (HTTP 200)")

        # Test 19: Hardware Buzzer Control APIs (Test & Stop)
        res = client.post('/api/buzzer/test')
        assert res.status_code == 200, f"Buzzer test failed: {res.status_code}"
        res = client.post('/api/buzzer/stop')
        assert res.status_code == 200, f"Buzzer stop failed: {res.status_code}"
        print("[PASS] 19. Hardware Buzzer test & stop endpoints verified (HTTP 200)")

        # Test 20: Full Buzzer & Mobile Notification Dispatch
        res = client.post('/api/alerts/test-full', json={'phone_number': '+919876543210'})
        assert res.status_code == 200, f"Full alert test failed: {res.status_code}"
        alert_json = res.get_json()
        assert alert_json['buzzer_triggered'] is True, "Buzzer not triggered"
        assert alert_json['sms_result']['success'] is True, "SMS dispatch not successful"
        print(f"[PASS] 20. Target Reached Buzzer & SMS Alert Dispatched to {alert_json['sms_result']['phone']} (HTTP 200)")

        # Test 21: Toggle SMS Notifications Enable/Disable API
        res = client.post('/api/sms/toggle', json={'enabled': False})
        assert res.status_code == 200, f"SMS toggle failed: {res.status_code}"
        toggle_json = res.get_json()
        assert toggle_json['sms_alerts_enabled'] is False, "SMS was not disabled"
        # Test that target reached SMS respects disabled setting
        from services.sms_service import sms_service
        disabled_res = sms_service.send_target_reached_alert(user, target_pct=80.0, current_pct=80.0)
        assert disabled_res['skipped'] is True and disabled_res['status'] == 'disabled', "Disabled SMS check failed"
        # Re-enable SMS
        res = client.post('/api/sms/toggle', json={'enabled': True})
        assert res.get_json()['sms_alerts_enabled'] is True, "SMS was not re-enabled"
        print("[PASS] 21. Option to enable/disable SMS notifications verified (HTTP 200)")

        # Test 22: Twilio SMS Test Dispatch Endpoint
        res = client.post('/api/sms/test', json={'phone_number': '+919876543210'})
        assert res.status_code == 200, f"Twilio SMS test failed: {res.status_code}"
        sms_test_json = res.get_json()
        assert sms_test_json['success'] is True, "SMS test dispatch failed"
        print(f"[PASS] 22. Twilio SMS API test dispatch verified for {sms_test_json['phone']} (HTTP 200)")

        # Test 23: Verify SMS Logs Saved in MySQL/Database
        res = client.get('/api/sms/logs')
        assert res.status_code == 200, f"SMS logs API failed: {res.status_code}"
        logs_json = res.get_json()
        assert len(logs_json['logs']) > 0, "No SMS logs recorded in database"
        assert 'status' in logs_json['logs'][0], "Status column missing in SMS log"
        print(f"[PASS] 23. SMS status tracking in database verified ({len(logs_json['logs'])} records) (HTTP 200)")

        # Test 24: Enforce Strictly ONLY ONE SMS Per Charging Session
        # Create a new session
        test_session = ChargingSession(
            user_id=user.id,
            start_percentage=50.0,
            target_percentage=80.0,
            status='in_progress',
            sms_sent=False
        )
        db.session.add(test_session)
        db.session.commit()

        # First trigger when target is reached -> Should send 1 SMS
        first_sms = sms_service.send_target_reached_alert(user, target_pct=80.0, current_pct=80.0, session_id=test_session.id)
        assert first_sms['success'] is True, "First SMS dispatch failed"
        assert test_session.sms_sent is True, "Session sms_sent flag was not updated in DB"

        # Second trigger during the same session -> MUST be skipped (strictly 1 SMS per session)
        second_sms = sms_service.send_target_reached_alert(user, target_pct=80.0, current_pct=80.5, session_id=test_session.id)
        assert second_sms['skipped'] is True and second_sms['status'] == 'already_sent', "Duplicate SMS was sent for same session!"
        print(f"[PASS] 24. Strictly 1 SMS per session rule enforced (second dispatch safely blocked) (HTTP 200)")

    print("=" * 65)
    print("  ALL 24 TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 65)


if __name__ == '__main__':
    run_tests()
