/**
 * ChargeSense Interactive Chart.js Controllers
 * Manages rich visualizations for Analytics & Prediction modules.
 */

document.addEventListener('DOMContentLoaded', () => {
    loadAnalyticsCharts();
});

function loadAnalyticsCharts() {
    const timelineCanvas = document.getElementById('analyticsTimelineChart');
    if (!timelineCanvas) return;

    fetch('/api/analytics/charts')
        .then(res => res.json())
        .then(data => {
            if (!data.success) return;

            // 1. Battery Percentage Timeline
            renderTimelineChart(data.timeline);

            // 2. Session Durations Bar Chart
            renderDurationsChart(data.session_history);

            // 3. Predicted vs Actual Duration Comparison
            renderPredVsActualChart(data.pred_vs_actual);

            // 4. Charging Scenarios Comparison
            renderScenariosChart(data.scenario_curves);
        })
        .catch(err => console.error("Error loading analytics charts:", err));
}

function renderTimelineChart(timeline) {
    const ctx = document.getElementById('analyticsTimelineChart');
    if (!ctx) return;

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: timeline.labels,
            datasets: [{
                label: 'Battery Charge (%)',
                data: timeline.percentages,
                borderColor: '#10b981',
                backgroundColor: 'rgba(16, 185, 129, 0.15)',
                borderWidth: 3,
                tension: 0.35,
                fill: true,
                pointRadius: 4,
                pointBackgroundColor: '#10b981'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    min: 0,
                    max: 100,
                    grid: { color: 'rgba(148, 163, 184, 0.08)' },
                    ticks: { color: '#94a3b8' }
                },
                x: {
                    grid: { color: 'rgba(148, 163, 184, 0.08)' },
                    ticks: { color: '#94a3b8' }
                }
            }
        }
    });
}

function renderDurationsChart(history) {
    const ctx = document.getElementById('analyticsDurationsChart');
    if (!ctx) return;

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: history.labels,
            datasets: [{
                label: 'Duration (Minutes)',
                data: history.durations,
                backgroundColor: 'rgba(56, 189, 248, 0.65)',
                borderColor: '#38bdf8',
                borderWidth: 1.5,
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(148, 163, 184, 0.08)' },
                    ticks: { color: '#94a3b8' }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8' }
                }
            }
        }
    });
}

function renderPredVsActualChart(pred) {
    const ctx = document.getElementById('analyticsPredVsActualChart');
    if (!ctx) return;

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: pred.labels,
            datasets: [
                {
                    label: 'Baseline Formula (min)',
                    data: pred.baseline,
                    backgroundColor: 'rgba(99, 102, 241, 0.6)',
                    borderColor: '#6366f1',
                    borderWidth: 1,
                    borderRadius: 6
                },
                {
                    label: 'AI Model / Actual (min)',
                    data: pred.ml,
                    backgroundColor: 'rgba(16, 185, 129, 0.7)',
                    borderColor: '#10b981',
                    borderWidth: 1,
                    borderRadius: 6
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(148, 163, 184, 0.08)' },
                    ticks: { color: '#94a3b8' }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8' }
                }
            }
        }
    });
}

function renderScenariosChart(scenarios) {
    const ctx = document.getElementById('analyticsScenariosChart');
    if (!ctx) return;

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: scenarios.labels,
            datasets: [
                {
                    label: 'Fast Charging (2.0%/min)',
                    data: scenarios.fast,
                    borderColor: '#38bdf8',
                    borderWidth: 2.5,
                    borderDash: [],
                    tension: 0.2
                },
                {
                    label: 'Normal Charging (1.0%/min)',
                    data: scenarios.normal,
                    borderColor: '#10b981',
                    borderWidth: 2.5,
                    tension: 0.2
                },
                {
                    label: 'Slow Charging (0.5%/min)',
                    data: scenarios.slow,
                    borderColor: '#f59e0b',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    tension: 0.2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    min: 0,
                    max: 100,
                    title: { display: true, text: 'Battery %', color: '#94a3b8' },
                    grid: { color: 'rgba(148, 163, 184, 0.08)' },
                    ticks: { color: '#94a3b8' }
                },
                x: {
                    title: { display: true, text: 'Elapsed Time', color: '#94a3b8' },
                    grid: { color: 'rgba(148, 163, 184, 0.08)' },
                    ticks: { color: '#94a3b8' }
                }
            }
        }
    });
}
