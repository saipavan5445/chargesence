"""
ChargeSense ML Prediction Standalone CLI
Allows testing and comparing charging predictions from the terminal.
"""

import sys
import os
import argparse

# Add parent directory to path so predictor can be imported directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from predictor import predictor, CHARGING_RATES


def main():
    parser = argparse.ArgumentParser(description="ChargeSense Intelligent Prediction CLI")
    parser.add_argument("--current", type=float, default=25.0, help="Current battery percentage (0-100)")
    parser.add_argument("--target", type=float, default=80.0, help="Target battery percentage (0-100)")
    parser.add_argument("--speed", type=str, default="normal", choices=['slow', 'normal', 'fast'], help="Charging speed scenario")

    args = parser.parse_args()

    print("=" * 60)
    print("  CHARGESENSE - INTELLIGENT CHARGING PREDICTION")
    print("=" * 60)
    print(f"Current Battery : {args.current}%")
    print(f"Target Battery  : {args.target}%")
    print(f"Charging Mode   : {args.speed.upper()} ({CHARGING_RATES[args.speed]}%/min)")
    print("-" * 60)

    result = predictor.predict_full_comparison(args.current, args.target, args.speed)

    baseline = result['baseline']
    ml = result['ml']

    print(f"Baseline Formula Prediction: {baseline['remaining_minutes']} minutes (~{baseline['hours']}h {baseline['minutes']}m)")
    print(f"Baseline Completion Time   : {baseline['completion_time_str']}")
    print(f"Baseline Equation          : {baseline['formula']}")
    print("-" * 60)
    print(f"AI/ML Model Prediction     : {ml['ml_minutes']} minutes (~{ml['hours']}h {ml['minutes']}m)")
    print(f"AI/ML Model Name           : {ml['model_name']}")
    print(f"Estimated Finish Time      : {ml['completion_time_str']}")
    print(f"Model R² Score             : {ml['metrics'].get('r2_score', 'N/A')}")
    print(f"Model MAE                  : {ml['metrics'].get('mae_minutes', 'N/A')} minutes")
    print(f"CC-CV Difference           : {result['difference_minutes']} minutes")
    print("-" * 60)
    print("Multi-Scenario Comparison:")
    for mode, data in result['scenarios'].items():
        print(f"  * {mode.capitalize():<7}: Baseline: {data['baseline_minutes']:>5.1f} min | AI: {data['ml_minutes']:>5.1f} min | Est. Completion: {data['completion_time']}")
    print("=" * 60)


if __name__ == '__main__':
    main()
