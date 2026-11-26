# ChargeSense – Intelligent Charging Prediction System

**ChargeSense** is an academic mini-project combining battery monitoring, mathematical charging duration modeling, empirical non-linear lithium-ion electrochemistry, and IoT architecture.

The application delivers a commercial-grade SaaS analytics experience with real-time simulated telemetry, responsive dark navy & blue glassmorphism UI, interactive Chart.js visualizations, and evaluation metrics for college faculty evaluation.

---

## 1. Key Features

- **Live Battery Monitoring Simulation**: Real-time simulated battery percentage with animated liquid fill, charging bolt pulse, temperature, and open-circuit voltage calculations (3.60V–4.25V).
- **Intelligent Charging-Time Prediction**:
  - **Baseline Mathematical Formula**: `Remaining Time = (Target Battery - Current Battery) / Charging Rate`
  - **Lithium-Ion CC-CV Non-Linear AI Model**: Accounts for Constant Current to Constant Voltage tapering above 80% SoC.
  - **Evaluation Metrics**: Model R² Score ($0.98+$), Mean Absolute Error (MAE), and Root Mean Squared Error (RMSE).
- **Multiple Charging Scenarios**: Real-time comparison across **Slow** (0.5%/min, ~5W trickle), **Normal** (1.0%/min, ~15W standard), and **Fast** (2.0%/min, ~30W+ turbo).
- **Interactive Chart.js Analytics**:
  - Live Battery % progression curve
  - Session duration history bar chart
  - Baseline vs AI prediction accuracy comparison
  - Multi-scenario discharge and charge trajectories
- **User Authentication & Isolation**: Flask-Login session management with PBKDF2 password hashing. Each user's charging history and settings are completely isolated.
- **Dedicated Charging History**: Filterable, searchable, and paginated logs with CSV export and modal telemetry drill-down.
- **Smart Notification System**: In-app milestone alerts and optional browser desktop notifications (HTML5 Notifications API).
- **Administrator Console**: Manage registered accounts, toggle admin privileges, and monitor global system utilization.
- **Future IoT Hardware Ready**: Dedicated REST API endpoint (`/api/iot/telemetry`) engineered for ESP32 and INA219 current sensors.

---

## 2. Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | HTML5, CSS3, JavaScript (ES6+), Bootstrap 5, Font Awesome 6, Chart.js 4 |
| **Backend** | Python 3.10+, Flask Framework, RESTful API architecture |
| **Database** | MySQL 8.0+ / SQLite fallback, Flask-SQLAlchemy, PyMySQL |
| **Data & AI** | Pandas, NumPy, Scikit-learn, Polynomial Ridge Regression, CC-CV Curve Modeling |
| **Security** | Flask-Login, Werkzeug PBKDF2 password hashing, secure session cookies, input validation |

---

## 3. System Architecture

```mermaid
flowchart TD
    subgraph Client ["Frontend Client (Browser)"]
        UI["Dashboard & Prediction Lab UI"]
        JS["Dashboard Controller (dashboard.js)"]
        Charts["Chart.js Telemetry Visualizer"]
    end

    subgraph Server ["Flask Application Server"]
        App["Flask App Factory (app.py)"]
        Routes["Blueprints (auth, dashboard, prediction, analytics, history)"]
        Sim["Battery Simulator Service"]
        Pred["Intelligent Predictor Engine"]
    end

    subgraph ML ["Machine Learning Pipeline"]
        Dataset["charging_data.csv (1,500 samples)"]
        Train["train_model.py (Polynomial Regression)"]
        Weights["model_weights.json (R²=0.9821, MAE=3.11m)"]
    end

    subgraph Storage ["Database Layer"]
        DB[("MySQL Database / SQLite fallback")]
        Tables["users | charging_sessions | battery_readings | notifications | user_settings | prediction_results"]
    end

    UI -->|AJAX Polling / REST API| Routes
    Routes --> Sim
    Routes --> Pred
    Pred --> Weights
    Train --> Weights
    Dataset --> Train
    Sim --> Storage
    Routes --> Storage
```

---

## 4. Project Directory Structure

```text
chargesense/
│   .env                                # Environment variables & DB connection string
│   app.py                              # Flask application factory and entry point
│   config.py                           # Configuration classes (Dev, Prod, Testing)
│   extensions.py                       # SQLAlchemy & LoginManager instances
│   models.py                           # Database entities (User, Session, Reading, etc.)
│   predictor.py                        # Baseline & AI prediction logic
│   requirements.txt                    # Project Python dependencies
│   README.md                           # Documentation and setup instructions
│
├── database/
│       schema.sql                      # Native MySQL 8 DDL database schema
│
├── ml/
│   │   predict.py                      # Standalone CLI prediction tool
│   │   train_model.py                  # Training pipeline for regression model
│   │   model_weights.json              # Trained regression weights and metrics
│   └── dataset/
│           charging_data.csv           # 1,500 simulated lithium-ion charging sessions
│
├── routes/
│       admin.py                        # Admin management routes
│       analytics.py                    # Analytics charts and KPI routes
│       auth.py                         # Login, registration, and logout
│       dashboard.py                    # Real-time monitoring & telemetry API
│       history.py                      # History listing, pagination, and CSV export
│       notifications.py                # Alert management routes
│       prediction.py                   # Prediction lab routes & API
│       settings.py                     # User profile and simulation settings
│
├── services/
│       battery_simulator.py            # Battery telemetry simulation engine
│       notification_service.py         # Notification persistence helpers
│       prediction_service.py           # Prediction coordinator
│
├── static/
│   ├── css/
│   │       style.css                   # Dark navy theme, glassmorphism, animations
│   └── js/
│           app.js                      # Theme switcher, toasts, browser notifications
│           charts.js                   # Chart.js analytics configuration
│           dashboard.js                # Live polling & battery animation logic
│
└── templates/
        admin.html                      # System administrator console
        analytics.html                  # Interactive charts and trends
        base.html                       # Global layout with sidebar and navbar
        dashboard.html                  # Main live monitoring dashboard
        history.html                    # Paginated charging session history
        landing.html                    # Commercial SaaS landing page
        login.html                      # Sign in page with demo autofill
        notifications.html              # Notification center
        prediction.html                 # AI prediction laboratory
        register.html                   # User registration page
        settings.html                   # Preferences and profile management
```

---

## 5. Quick Installation & Setup

### Prerequisites
- Python 3.10 or higher
- (Optional) MySQL 8.0 or higher. If MySQL is not installed, the application automatically runs on built-in SQLite without any setup!

### Step 1: Open the Project Directory
```powershell
cd c:\Users\heman\OneDrive\Desktop\SMART-MEDICINE\chargesense
```

### Step 2: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: (Optional) MySQL Database Setup
If you want to use MySQL instead of the default SQLite:
1. Ensure your MySQL server is running (e.g., via XAMPP, WAMP, or MySQL Workbench).
2. Create the database and tables using the provided schema:
   ```bash
   mysql -u root -p < database/schema.sql
   ```
3. Update `.env`:
   ```ini
   DATABASE_URL=mysql+pymysql://root:yourpassword@localhost:3306/chargesense_db
   ```

### Step 4: Run the Machine Learning Training Pipeline
```bash
python ml/train_model.py
```
This generates the realistic training dataset in `ml/dataset/charging_data.csv` and outputs `ml/model_weights.json` with evaluation metrics ($R^2$, MAE, RMSE).

### Step 5: Start the ChargeSense Application
```bash
python app.py
```

Open your browser and navigate to:
```
http://127.0.0.1:5000/
```

---

## 6. Default Demonstration Accounts

The system automatically seeds demo credentials on first launch:

| Role | Username | Password | Notes |
|---|---|---|---|
| **Demo User** | `demo` | `demo123` | Pre-loaded with realistic historical sessions, telemetry readings, and metrics |
| **Administrator** | `admin` | `admin123` | Access to the administrative console and user management |

*Quick login buttons are available on the login page for instant faculty evaluation.*

---

## 7. Machine Learning & Prediction Formulas

### 1. Baseline Formula (Linear Physics)
$$\text{Remaining Time (minutes)} = \frac{\text{Target Battery } \% - \text{Current Battery } \%}{\text{Charging Rate } (\%/\text{minute})}$$

- **Slow Mode (5W USB)**: $0.5\% / \text{min}$ ($120 \text{ min}$ for $0\% \to 60\%$)
- **Normal Mode (15W Standard)**: $1.0\% / \text{min}$ ($60 \text{ min}$ for $0\% \to 60\%$)
- **Fast Mode (30W Turbo)**: $2.0\% / \text{min}$ ($30 \text{ min}$ for $0\% \to 60\%$)

### 2. Lithium-Ion CC-CV Saturation Model
In real batteries, charging from $80\%$ to $100\%$ transitions from Constant Current (CC) to Constant Voltage (CV). The charging rate exponentially decays:
$$\text{Rate}_{\text{effective}}(p) = \text{Rate}_{\text{nominal}} \times \left(1 - \left[\frac{p - 80}{22}\right]^{1.4}\right) \quad \text{for } p > 80$$

This adds a realistic $\approx 15\% \text{–} 25\%$ duration curve to the final top-up phase, preventing over-optimistic linear predictions.

---

## 8. REST API Reference

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/telemetry` | Live battery percentage, voltage, temp, and active prediction | Yes |
| `POST` | `/api/simulation/start` | Starts charging session (`{target_percentage, charging_speed}`) | Yes |
| `POST` | `/api/simulation/stop` | Pauses or concludes the active charging session | Yes |
| `POST` | `/api/simulation/discharge` | Simulates battery drain (unplugged device) | Yes |
| `POST` | `/api/simulation/reset` | Resets battery to $25\%$ for demonstration testing | Yes |
| `POST` | `/api/predict` | Predicts charging duration with baseline and AI models | Yes |
| `GET` | `/api/analytics/charts` | Chart.js datasets (timeline, durations, scenarios) | Yes |
| `GET` | `/api/history/<id>/readings` | Telemetry points drill-down for a session | Yes |
| `POST` | `/api/iot/telemetry` | IoT sensor telemetry ingestion endpoint | API Key |

---

## 9. Future IoT Integration Architecture

ChargeSense is architected for hardware expansion:
- **Microcontroller**: ESP32 or ESP8266 Wi-Fi module
- **Sensor**: INA219 Voltage/Current I2C sensor or MAX17043 LiPo Fuel Gauge
- **Data Ingestion**: Transmits JSON telemetry to `/api/iot/telemetry`:
  ```json
  {
    "api_key": "YOUR_DEVICE_KEY",
    "percentage": 68.5,
    "voltage": 3.92,
    "temperature": 32.1,
    "charging": true
  }
  ```

---

## 10. Academic Presentation Guide

When presenting to faculty or examiners, emphasize:
1. **Academic Honesty**: Clearly explain that this is a software prototype with simulated electrochemical telemetry rather than falsely asserting direct browser sensor access.
2. **AI vs Formula Differentiation**: Open the **AI Prediction Lab** (`/prediction`) and demonstrate how linear baseline formulas underestimate charging time above $80\%$ due to lithium-ion CC-CV physics.
3. **Data Analytics**: Showcase the **Analytics** page with 4 interactive Chart.js graphs and the CSV export capability.
4. **Architectural Separation**: Highlight the modular Flask blueprint structure, SQLAlchemy models, and RESTful separation of frontend and backend.
