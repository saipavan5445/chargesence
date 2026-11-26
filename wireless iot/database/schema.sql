-- ChargeSense Database Schema
-- Target Database: MySQL 8.0+
-- Encoding: utf8mb4 / utf8mb4_unicode_ci

CREATE DATABASE IF NOT EXISTS chargesense_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE chargesense_db;

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(256) NOT NULL,
    full_name VARCHAR(100) DEFAULT '',
    phone_number VARCHAR(25) DEFAULT '',
    is_admin BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_username (username),
    INDEX idx_user_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. Charging Sessions Table
CREATE TABLE IF NOT EXISTS charging_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    start_percentage FLOAT NOT NULL,
    end_percentage FLOAT DEFAULT 0.0,
    target_percentage FLOAT DEFAULT 80.0,
    charging_speed VARCHAR(20) DEFAULT 'normal',
    charging_rate FLOAT DEFAULT 1.0,
    duration_minutes FLOAT DEFAULT 0.0,
    status VARCHAR(20) DEFAULT 'in_progress',
    sms_sent BOOLEAN DEFAULT FALSE,
    sms_status VARCHAR(30) DEFAULT 'none',
    start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    end_time DATETIME NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_session_user_status (user_id, status),
    INDEX idx_session_start_time (start_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Battery Readings Table (Telemetry)
CREATE TABLE IF NOT EXISTS battery_readings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT NOT NULL,
    user_id INT NOT NULL,
    percentage FLOAT NOT NULL,
    voltage FLOAT DEFAULT 3.85,
    temperature FLOAT DEFAULT 29.5,
    charging_rate FLOAT DEFAULT 1.0,
    status VARCHAR(20) DEFAULT 'charging',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES charging_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_readings_session (session_id),
    INDEX idx_readings_user (user_id),
    INDEX idx_readings_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Notifications Table
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(120) NOT NULL,
    message VARCHAR(255) NOT NULL,
    notification_type VARCHAR(20) DEFAULT 'info',
    is_read BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_notifications_user_read (user_id, is_read)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. User Settings Table
CREATE TABLE IF NOT EXISTS user_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    default_target_percentage FLOAT DEFAULT 80.0,
    default_charging_speed VARCHAR(20) DEFAULT 'normal',
    simulation_speed_multiplier FLOAT DEFAULT 1.0,
    browser_notifications_enabled BOOLEAN DEFAULT TRUE,
    phone_number VARCHAR(25) DEFAULT '',
    sms_alerts_enabled BOOLEAN DEFAULT TRUE,
    buzzer_alerts_enabled BOOLEAN DEFAULT TRUE,
    theme VARCHAR(10) DEFAULT 'dark',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. Prediction Results Table
CREATE TABLE IF NOT EXISTS prediction_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    session_id INT NULL,
    current_percentage FLOAT NOT NULL,
    target_percentage FLOAT NOT NULL,
    charging_speed VARCHAR(20) DEFAULT 'normal',
    baseline_predicted_minutes FLOAT NOT NULL,
    ml_predicted_minutes FLOAT NULL,
    actual_minutes FLOAT NULL,
    error_minutes FLOAT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES charging_sessions(id) ON DELETE SET NULL,
    INDEX idx_predictions_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. SMS Notifications Table (Twilio Log & Status Tracking in MySQL)
CREATE TABLE IF NOT EXISTS sms_notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    session_id INT NULL,
    phone_number VARCHAR(30) NOT NULL,
    message TEXT NOT NULL,
    status VARCHAR(30) DEFAULT 'sent',
    gateway VARCHAR(50) DEFAULT 'Twilio SMS API',
    sid VARCHAR(64) NULL,
    error_message VARCHAR(255) NULL,
    target_percentage FLOAT NULL,
    current_percentage FLOAT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES charging_sessions(id) ON DELETE SET NULL,
    INDEX idx_sms_user (user_id),
    INDEX idx_sms_session (session_id),
    INDEX idx_sms_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
