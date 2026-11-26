"""
ChargeSense Analytics Routes & Visual Telemetry API
Supplies interactive Chart.js datasets, performance trends,
and smart analytical observations.
"""

from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from models import ChargingSession, BatteryReading, PredictionResult
from services.battery_simulator import simulator_service

analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route('/analytics')
@login_required
def analytics_view():
    """Renders the comprehensive battery analytics page."""
    user_id = current_user.id

    # Compute key performance indicators (KPIs)
    sessions = ChargingSession.query.filter_by(user_id=user_id).all()
    total_count = len(sessions)
    completed_count = sum(1 for s in sessions if s.status == 'completed')

    avg_duration = 0.0
    avg_gain = 0.0
    if total_count > 0:
        durations = [s.duration_minutes for s in sessions if s.duration_minutes > 0]
        avg_duration = round(sum(durations) / len(durations), 1) if durations else 0.0
        gains = [max(0.0, s.end_percentage - s.start_percentage) for s in sessions if s.end_percentage > 0]
        avg_gain = round(sum(gains) / len(gains), 1) if gains else 0.0

    return render_template(
        'analytics.html',
        total_sessions=total_count,
        completed_sessions=completed_count,
        avg_duration=avg_duration,
        avg_gain=avg_gain
    )


@analytics_bp.route('/api/analytics/charts')
@login_required
def get_chart_data():
    """
    Supplies real-time and historical datasets formatted for Chart.js.
    """
    user_id = current_user.id

    # 1. Recent session telemetry readings (Battery % vs Time)
    latest_session = ChargingSession.query.filter_by(user_id=user_id)\
        .order_by(ChargingSession.created_at.desc()).first()

    timeline_labels = []
    timeline_percentages = []
    timeline_rates = []

    if latest_session:
        readings = latest_session.readings.order_by(BatteryReading.timestamp.asc()).limit(30).all()
        for r in readings:
            timeline_labels.append(r.timestamp.strftime('%H:%M:%S'))
            timeline_percentages.append(r.percentage)
            timeline_rates.append(r.charging_rate)

    # Fallback simulated curve if session has few readings yet
    if len(timeline_percentages) < 2:
        curr = simulator_service.get_user_state(user_id)['current_percentage']
        timeline_labels = ['-15m', '-12m', '-9m', '-6m', '-3m', 'Now']
        timeline_percentages = [
            max(5, curr - 20), max(5, curr - 15), max(5, curr - 10),
            max(5, curr - 6), max(5, curr - 3), curr
        ]
        timeline_rates = [1.0, 1.0, 1.0, 0.95, 0.9, 0.85]

    # 2. Historical session durations (last 7 sessions)
    recent_sessions = ChargingSession.query.filter_by(user_id=user_id)\
        .order_by(ChargingSession.created_at.asc()).limit(7).all()

    history_labels = [f"Session #{s.id}" for s in recent_sessions]
    history_durations = [s.duration_minutes for s in recent_sessions]

    if not history_durations:
        history_labels = ['Session #1', 'Session #2', 'Session #3', 'Session #4']
        history_durations = [35.0, 48.0, 42.0, 55.0]

    # 3. Predicted vs Actual Duration Comparison
    predictions = PredictionResult.query.filter_by(user_id=user_id)\
        .order_by(PredictionResult.created_at.desc()).limit(6).all()

    pred_labels = [f"Pred #{p.id}" for p in reversed(predictions)]
    pred_baselines = [p.baseline_predicted_minutes for p in reversed(predictions)]
    pred_mls = [p.ml_predicted_minutes or p.baseline_predicted_minutes for p in reversed(predictions)]

    if not pred_baselines:
        pred_labels = ['Test A', 'Test B', 'Test C', 'Test D', 'Test E']
        pred_baselines = [30.0, 45.0, 60.0, 75.0, 90.0]
        pred_mls = [32.5, 48.0, 64.2, 81.0, 98.5]

    # 4. Multi-Scenario Charging Curves (0% to 100% time progression)
    # Slow (0.5%/min -> 200min), Normal (1.0%/min -> 100min), Fast (2.0%/min -> 50min)
    scenario_time_labels = [f"{t}m" for t in range(0, 121, 10)]
    slow_curve = [min(100, t * 0.5) for t in range(0, 121, 10)]
    normal_curve = [min(100, t * 1.0) for t in range(0, 121, 10)]
    fast_curve = [min(100, t * 2.0) for t in range(0, 121, 10)]

    return jsonify({
        'success': True,
        'timeline': {
            'labels': timeline_labels,
            'percentages': timeline_percentages,
            'rates': timeline_rates
        },
        'session_history': {
            'labels': history_labels,
            'durations': history_durations
        },
        'pred_vs_actual': {
            'labels': pred_labels,
            'baseline': pred_baselines,
            'ml': pred_mls
        },
        'scenario_curves': {
            'labels': scenario_time_labels,
            'slow': slow_curve,
            'normal': normal_curve,
            'fast': fast_curve
        }
    })
