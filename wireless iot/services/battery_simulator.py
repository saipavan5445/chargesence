"""
ChargeSense Battery Simulation & Hardware Telemetry Service
Provides in-memory simulation state and connects directly to physical
laptop battery telemetry on Windows via laptop_reader.
"""

from datetime import datetime
import random
from extensions import db
from models import ChargingSession, BatteryReading, Notification
from predictor import predictor, CHARGING_RATES
from services.laptop_battery import laptop_reader
from services.email_service import email_service
from services.buzzer_service import buzzer_service


class BatterySimulatorService:
    """Manages active battery simulations and real laptop hardware synchronization."""

    def __init__(self):
        # In-memory user state dictionary: {user_id: state_dict}
        self._user_states = {}

    def get_user_state(self, user_id: int) -> dict:
        """Retrieves or initializes simulated telemetry state for a user."""
        if user_id not in self._user_states:
            # Check if physical laptop battery is available
            hw = laptop_reader.read_battery()
            default_source = 'laptop' if hw['available'] else 'simulation'
            default_pct = hw['percentage'] if hw['available'] else 45.0
            default_status = hw['status'] if hw['available'] else 'idle'

            self._user_states[user_id] = {
                'current_percentage': default_pct,
                'target_percentage': 80.0,
                'charging_speed': 'normal',
                'status': default_status,
                'telemetry_source': default_source,
                'voltage': hw.get('voltage', 3.85),
                'temperature': 30.2,
                'charging_rate': CHARGING_RATES['normal'],
                'active_session_id': None,
                'session_start_time': None,
                'last_tick': datetime.utcnow()
            }
        return self._user_states[user_id]

    def set_telemetry_source(self, user_id: int, source: str) -> dict:
        """Switches between 'laptop' (physical hardware) and 'simulation' mode."""
        state = self.get_user_state(user_id)
        if source in ['laptop', 'simulation']:
            state['telemetry_source'] = source
            if source == 'laptop':
                hw = laptop_reader.read_battery()
                state['current_percentage'] = hw['percentage']
                state['status'] = hw['status']
                state['voltage'] = hw['voltage']
        return self.get_telemetry(user_id)

    def start_simulation(self, user, target_percentage: float = 80.0, speed: str = 'normal') -> dict:
        """Starts or resumes a charging session."""
        state = self.get_user_state(user.id)
        speed = speed.lower() if speed.lower() in CHARGING_RATES else 'normal'
        target_percentage = max(10.0, min(100.0, float(target_percentage)))

        if state['telemetry_source'] == 'laptop':
            hw = laptop_reader.read_battery()
            state['current_percentage'] = hw['percentage']

        # Create new charging session in the database
        session = ChargingSession(
            user_id=user.id,
            start_percentage=round(state['current_percentage'], 1),
            target_percentage=target_percentage,
            charging_speed=speed,
            charging_rate=CHARGING_RATES[speed],
            status='in_progress',
            start_time=datetime.utcnow()
        )
        db.session.add(session)
        db.session.commit()

        # Update in-memory state
        buzzer_service.stop_buzzer()
        state['buzzer_muted'] = False
        state['status'] = 'charging'
        state['target_percentage'] = target_percentage
        state['charging_speed'] = speed
        state['charging_rate'] = CHARGING_RATES[speed]
        state['active_session_id'] = session.id
        state['session_start_time'] = datetime.utcnow()
        state['last_tick'] = datetime.utcnow()
        state['sms_dispatched_for_target'] = False

        # Create starting battery reading
        initial_reading = BatteryReading(
            session_id=session.id,
            user_id=user.id,
            percentage=state['current_percentage'],
            voltage=self._calculate_voltage(state['current_percentage']),
            temperature=self._calculate_temperature(speed),
            charging_rate=state['charging_rate'],
            status='charging'
        )
        db.session.add(initial_reading)

        # Create system notification
        mode_label = "Laptop Battery" if state['telemetry_source'] == 'laptop' else "Simulation"
        notif = Notification(
            user_id=user.id,
            title='Charging Started',
            message=f"{mode_label} session #{session.id} started at {round(state['current_percentage'], 1)}% towards {target_percentage}%.",
            notification_type='info'
        )
        db.session.add(notif)
        db.session.commit()

        return self.get_telemetry(user.id)

    def stop_simulation(self, user) -> dict:
        """Stops the active charging session and concludes the session."""
        buzzer_service.stop_buzzer()
        state = self.get_user_state(user.id)
        state['buzzer_muted'] = True
        state['status'] = 'stopped'

        if state['active_session_id']:
            session = ChargingSession.query.get(state['active_session_id'])
            if session and session.status == 'in_progress':
                session.status = 'stopped'
                session.end_time = datetime.utcnow()
                session.end_percentage = round(state['current_percentage'], 1)
                if session.start_time:
                    elapsed = (session.end_time - session.start_time).total_seconds() / 60.0
                    session.duration_minutes = round(max(0.1, elapsed), 1)

                notif = Notification(
                    user_id=user.id,
                    title='Charging Paused',
                    message=f"Charging session #{session.id} stopped at {round(state['current_percentage'], 1)}%.",
                    notification_type='warning'
                )
                db.session.add(notif)
                db.session.commit()

        return self.get_telemetry(user.id)

    def trigger_discharge(self, user) -> dict:
        """Simulates battery discharge / device unplugged."""
        buzzer_service.stop_buzzer()
        state = self.get_user_state(user.id)
        state['buzzer_muted'] = True
        state['status'] = 'discharging'
        return self.get_telemetry(user.id)

    def reset_battery(self, user, percentage: float = 25.0) -> dict:
        """Resets battery state for demonstration testing."""
        buzzer_service.stop_buzzer()
        state = self.get_user_state(user.id)
        state['buzzer_muted'] = False
        state['sms_dispatched_for_target'] = False
        state['current_percentage'] = max(5.0, min(95.0, float(percentage)))
        state['status'] = 'idle'
        state['voltage'] = self._calculate_voltage(state['current_percentage'])
        state['temperature'] = 28.5
        return self.get_telemetry(user.id)

    def tick(self, user) -> dict:
        """
        Advances the telemetry state.
        If in laptop mode: syncs directly from Windows kernel32.
        If in simulation mode: advances simulated charge.
        """
        state = self.get_user_state(user.id)

        # Mode A: REAL PHYSICAL LAPTOP BATTERY
        if state.get('telemetry_source') == 'laptop':
            hw = laptop_reader.read_battery()
            if hw['available']:
                old_pct = state['current_percentage']
                state['current_percentage'] = hw['percentage']
                state['voltage'] = hw['voltage']
                state['charging_rate'] = hw['charging_rate']
                is_plugged = hw.get('ac_plugged', False)
                state['ac_plugged'] = is_plugged

                # CRITICAL: If physical charger is unplugged, IMMEDIATELY silence buzzer
                if not is_plugged:
                    buzzer_service.stop_buzzer()
                    state['buzzer_muted'] = True

                # CRITICAL: Check if real battery has reached or exceeded target percentage
                if state['current_percentage'] >= state['target_percentage']:
                    state['status'] = 'completed'  # Turn off charging state

                    # Trigger physical laptop speaker alarm buzzer ONLY if still plugged in and not muted
                    if is_plugged and not state.get('buzzer_muted'):
                        buzzer_service.start_buzzer()

                    # Dispatch Email Notification (strictly 1 email per session)
                    if not state.get('sms_dispatched_for_target'):
                        state['sms_dispatched_for_target'] = True
                        email_res = email_service.send_target_reached_alert(
                            user=user,
                            target_pct=state['target_percentage'],
                            current_pct=state['current_percentage'],
                            session_id=state.get('active_session_id')
                        )
                        state['last_sms_info'] = email_res

                    if state['active_session_id']:
                        session = ChargingSession.query.get(state['active_session_id'])
                        if session and session.status == 'in_progress':
                            session.status = 'completed'
                            session.end_time = datetime.utcnow()
                            session.end_percentage = state['current_percentage']
                            notif = Notification(
                                user_id=user.id,
                                title='Target Battery Reached on Laptop!',
                                message=f"Your laptop battery reached {state['target_percentage']}%. Charging turned off by smart limiter. Buzzer active & notification dispatched. Please unplug AC charger.",
                                notification_type='success'
                            )
                            db.session.add(notif)
                            db.session.commit()
                else:
                    state['sms_dispatched_for_target'] = False
                    state['buzzer_muted'] = False
                    if state.get('status') not in ['stopped', 'completed']:
                        state['status'] = hw['status']

                # If actively tracking a session, log readings
                if state['active_session_id']:
                    reading = BatteryReading(
                        session_id=state['active_session_id'],
                        user_id=user.id,
                        percentage=state['current_percentage'],
                        voltage=state['voltage'],
                        temperature=state['temperature'],
                        charging_rate=state['charging_rate'],
                        status=state['status']
                    )
                    db.session.add(reading)
                    db.session.commit()

            return self.get_telemetry(user.id)

        # Mode B: SIMULATION MODE
        now = datetime.utcnow()
        elapsed_sec = (now - state['last_tick']).total_seconds()
        state['last_tick'] = now

        if state['status'] == 'charging':
            speed = state.get('charging_speed', 'normal')
            base_rate = CHARGING_RATES.get(speed, 1.0)

            # Fast responsive charging increments
            if speed == 'turbo':
                gain = random.uniform(3.5, 5.0)
            elif speed == 'fast':
                gain = random.uniform(2.0, 2.8)
            elif speed == 'normal':
                gain = random.uniform(1.0, 1.5)
            else:
                gain = random.uniform(0.4, 0.7)

            if state['current_percentage'] > 85.0:
                gain *= 0.75

            effective_rate = base_rate
            new_pct = state['current_percentage'] + max(0.2, gain)

            # CRITICAL: Stop charging when reaching target percentage
            if new_pct >= state['target_percentage']:
                state['current_percentage'] = round(state['target_percentage'], 1)
                state['status'] = 'completed'  # STOP CHARGING!
            else:
                state['current_percentage'] = round(min(100.0, new_pct), 1)

            state['voltage'] = self._calculate_voltage(state['current_percentage'])
            state['temperature'] = self._calculate_temperature(state['charging_speed'])
            state['charging_rate'] = round(effective_rate, 2)

            if state['active_session_id']:
                state['tick_count'] = state.get('tick_count', 0) + 1
                is_completed = (state['status'] == 'completed')
                if state['tick_count'] % 4 == 0 or is_completed:
                    reading = BatteryReading(
                        session_id=state['active_session_id'],
                        user_id=user.id,
                        percentage=state['current_percentage'],
                        voltage=state['voltage'],
                        temperature=state['temperature'],
                        charging_rate=state['charging_rate'],
                        status=state['status']
                    )
                    db.session.add(reading)

                session = ChargingSession.query.get(state['active_session_id'])
                if session:
                    session.end_percentage = state['current_percentage']
                    if session.start_time:
                        elapsed = (datetime.utcnow() - session.start_time).total_seconds() / 60.0
                        session.duration_minutes = round(max(0.1, elapsed), 1)

                    if state['status'] == 'completed':
                        session.status = 'completed'
                        session.end_time = datetime.utcnow()

                        # Sound hardware buzzer alarm on physical laptop speakers only if not muted
                        if not state.get('buzzer_muted'):
                            buzzer_service.start_buzzer()

                        # Dispatch Email Notification (strictly 1 email per session)
                        if not state.get('sms_dispatched_for_target'):
                            state['sms_dispatched_for_target'] = True
                            email_res = email_service.send_target_reached_alert(
                                user=user,
                                target_pct=state['target_percentage'],
                                current_pct=state['current_percentage'],
                                session_id=state.get('active_session_id')
                            )
                            state['last_sms_info'] = email_res

                        notif = Notification(
                            user_id=user.id,
                            title='Target Battery Reached!',
                            message=f"Target threshold of {state['target_percentage']}% reached. Charging turned off.",
                            notification_type='success'
                        )
                        db.session.add(notif)

                db.session.commit()

        elif state['status'] == 'discharging':
            drop = random.uniform(0.3, 0.7)
            new_pct = max(5.0, state['current_percentage'] - drop)
            state['current_percentage'] = round(new_pct, 1)
            state['voltage'] = self._calculate_voltage(new_pct)
            state['temperature'] = max(26.0, round(state['temperature'] - 0.2, 1))

            if state['current_percentage'] <= 20.0 and state['current_percentage'] + drop > 20.0:
                notif = Notification(
                    user_id=user.id,
                    title='Low Battery Warning',
                    message=f"Battery level dropped to {state['current_percentage']}%. Please connect a charger.",
                    notification_type='danger'
                )
                db.session.add(notif)
                db.session.commit()

        return self.get_telemetry(user.id)

    def get_telemetry(self, user_id: int) -> dict:
        """Compiles real-time telemetry and prediction bundle for the frontend."""
        state = self.get_user_state(user_id)
        source = state.get('telemetry_source', 'simulation')

        hw_info = laptop_reader.read_battery()

        # If in laptop mode, ensure state is updated with fresh hardware reading
        if source == 'laptop' and hw_info['available']:
            state['current_percentage'] = hw_info['percentage']
            state['voltage'] = hw_info['voltage']

            # If current battery has reached or exceeded target limit, enforce completed status
            if state['current_percentage'] >= state['target_percentage']:
                state['status'] = 'completed'
            elif state.get('status') not in ['stopped', 'completed']:
                state['status'] = hw_info['status']

        # Compute real-time predictions
        prediction_bundle = predictor.predict_full_comparison(
            state['current_percentage'],
            state['target_percentage'],
            state['charging_speed']
        )

        return {
            'current_percentage': round(state['current_percentage'], 1),
            'target_percentage': round(state['target_percentage'], 1),
            'status': state['status'],
            'telemetry_source': source,
            'hardware_available': hw_info['available'],
            'ac_plugged': hw_info.get('ac_plugged', False),
            'charging_speed': state['charging_speed'],
            'charging_rate': round(state['charging_rate'], 2),
            'voltage': round(state['voltage'], 2),
            'temperature': round(state['temperature'], 1),
            'active_session_id': state['active_session_id'],
            'prediction': prediction_bundle['baseline'],
            'ml_prediction': prediction_bundle['ml'],
            'difference_minutes': prediction_bundle['difference_minutes'],
            'insights': prediction_bundle['insights'],
            'last_sms_info': state.get('last_sms_info'),
            'email_configured': email_service.is_configured(),
            'target_reached': (state['current_percentage'] >= state['target_percentage']),
            'buzzer_active': buzzer_service.is_active,
            'timestamp': datetime.utcnow().strftime('%H:%M:%S')
        }

    def _calculate_voltage(self, percentage: float) -> float:
        pct = max(0.0, min(100.0, percentage)) / 100.0
        voltage = 3.60 + (0.55 * pct) + (0.10 * (pct ** 3))
        return round(voltage, 2)

    def _calculate_temperature(self, speed: str) -> float:
        base_temp = {'slow': 28.5, 'normal': 31.5, 'fast': 37.0}.get(speed, 31.0)
        fluctuation = random.uniform(-0.4, 0.4)
        return round(base_temp + fluctuation, 1)


# Global singleton instance
simulator_service = BatterySimulatorService()
