"""
ChargeSense Prediction Service
Coordinates baseline & ML calculations, persists prediction records,
and computes evaluation and scenario data.
"""

from extensions import db
from models import PredictionResult
from predictor import predictor, CHARGING_RATES


class PredictionService:
    """Manages predictive analytics and history persistence."""

    @staticmethod
    def predict_and_record(user_id: int, current_pct: float, target_pct: float, speed: str = 'normal', session_id: int = None) -> dict:
        """Calculates prediction and records result in database."""
        result = predictor.predict_full_comparison(current_pct, target_pct, speed)

        # Store in prediction_results table
        record = PredictionResult(
            user_id=user_id,
            session_id=session_id,
            current_percentage=current_pct,
            target_percentage=target_pct,
            charging_speed=speed,
            baseline_predicted_minutes=result['baseline']['remaining_minutes'],
            ml_predicted_minutes=result['ml']['ml_minutes'],
            error_minutes=round(abs(result['ml']['ml_minutes'] - result['baseline']['remaining_minutes']), 1)
        )
        db.session.add(record)
        db.session.commit()

        result['saved_record_id'] = record.id
        return result

    @staticmethod
    def get_user_predictions(user_id: int, limit: int = 15):
        """Retrieves recent prediction calculations for a user."""
        return PredictionResult.query.filter_by(user_id=user_id).order_by(PredictionResult.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_model_evaluation_metrics():
        """Returns statistical evaluation metrics of the ML model."""
        return predictor.ml_metrics


prediction_service = PredictionService()
