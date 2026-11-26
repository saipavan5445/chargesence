"""
ChargeSense Prediction Routes & API
Provides endpoints for baseline and ML charging time prediction,
error evaluation, and multi-scenario comparisons.
"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from services.prediction_service import prediction_service
from services.battery_simulator import simulator_service
from predictor import predictor

prediction_bp = Blueprint('prediction', __name__)


@prediction_bp.route('/prediction')
@login_required
def prediction_view():
    """Renders the interactive charging-time prediction lab."""
    telemetry = simulator_service.get_telemetry(current_user.id)
    history = prediction_service.get_user_predictions(current_user.id, limit=8)
    metrics = prediction_service.get_model_evaluation_metrics()

    initial_calc = predictor.predict_full_comparison(
        telemetry['current_percentage'],
        telemetry['target_percentage'],
        telemetry['charging_speed']
    )

    return render_template(
        'prediction.html',
        telemetry=telemetry,
        history=history,
        metrics=metrics,
        initial_calc=initial_calc
    )


@prediction_bp.route('/api/predict', methods=['POST'])
@login_required
def predict_api():
    """
    Computes charging time predictions for given current, target, and speed.
    Records the prediction in the database.
    """
    data = request.get_json() or {}

    try:
        current_pct = float(data.get('current_percentage', 50.0))
        target_pct = float(data.get('target_percentage', 80.0))
        speed = data.get('charging_speed', 'normal')
        save_record = bool(data.get('save_record', True))

        if current_pct < 0 or current_pct > 100 or target_pct < 0 or target_pct > 100:
            return jsonify({'success': False, 'error': 'Percentages must be between 0 and 100.'}), 400

        if save_record:
            result = prediction_service.predict_and_record(
                user_id=current_user.id,
                current_pct=current_pct,
                target_pct=target_pct,
                speed=speed
            )
        else:
            result = predictor.predict_full_comparison(current_pct, target_pct, speed)

        return jsonify({
            'success': True,
            'data': result
        })

    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid numerical inputs.'}), 400


@prediction_bp.route('/api/predict/metrics')
@login_required
def metrics_api():
    """Returns the ML model evaluation metrics (R², MAE, RMSE)."""
    return jsonify({
        'success': True,
        'metrics': prediction_service.get_model_evaluation_metrics()
    })
