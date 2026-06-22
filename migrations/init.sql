-- ============================================================
-- WCNMS Database Schema — MySQL 8.0
-- Wireless Campus Network Management System
-- ============================================================

CREATE DATABASE IF NOT EXISTS wcnms_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE wcnms_db;

-- ============================================================
-- Table 1: users
-- Stores administrator and staff accounts with RBAC roles
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(80)  NOT NULL UNIQUE,
    email         VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name     VARCHAR(120) NOT NULL,
    role          ENUM('super_admin','admin','read_only') NOT NULL DEFAULT 'read_only',
    department    VARCHAR(100),
    phone         VARCHAR(20),
    is_active     TINYINT(1)   NOT NULL DEFAULT 1,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login    DATETIME,
    INDEX idx_users_username (username),
    INDEX idx_users_email    (email),
    INDEX idx_users_role     (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- Table 2: bandwidth_policies
-- Per-group QoS bandwidth caps (FCAPS: Performance Management)
-- ============================================================
CREATE TABLE IF NOT EXISTS bandwidth_policies (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    policy_name       VARCHAR(100) NOT NULL UNIQUE,
    upload_cap_mbps   FLOAT        NOT NULL,
    download_cap_mbps FLOAT        NOT NULL,
    priority          INT          NOT NULL DEFAULT 5,
    target_role       VARCHAR(50),
    description       TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- Table 3: access_points
-- All managed IEEE 802.11ac APs (Configuration Management)
-- ============================================================
CREATE TABLE IF NOT EXISTS access_points (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    ap_name             VARCHAR(100) NOT NULL UNIQUE,
    mac_address         VARCHAR(17)  NOT NULL UNIQUE,
    ip_address          VARCHAR(15)  NOT NULL,
    location            VARCHAR(200),
    building            VARCHAR(100),
    floor               VARCHAR(20),
    status              ENUM('online','offline','degraded') NOT NULL DEFAULT 'offline',
    channel_24ghz       INT,
    channel_5ghz        INT,
    tx_power            INT,
    client_count        INT          DEFAULT 0,
    channel_utilization FLOAT        DEFAULT 0.0,
    uptime_seconds      BIGINT       DEFAULT 0,
    firmware_version    VARCHAR(50),
    ssid                VARCHAR(100),
    vlan_id             INT,
    last_polled         DATETIME,
    created_at          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ap_mac    (mac_address),
    INDEX idx_ap_status (status),
    INDEX idx_ap_building (building)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- Table 4: devices
-- Registered client devices (Accounting Management)
-- ============================================================
CREATE TABLE IF NOT EXISTS devices (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    mac_address  VARCHAR(17)  NOT NULL UNIQUE,
    ip_address   VARCHAR(15),
    device_name  VARCHAR(100),
    device_type  VARCHAR(50),
    user_id      INT,
    os_type      VARCHAR(50),
    first_seen   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_authorized TINYINT(1)  NOT NULL DEFAULT 1,
    vlan_id      INT,
    CONSTRAINT fk_devices_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_device_mac    (mac_address),
    INDEX idx_device_user   (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- Table 5: bandwidth_usage
-- Per-session bandwidth metering (Performance & Accounting)
-- ============================================================
CREATE TABLE IF NOT EXISTS bandwidth_usage (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    user_id           INT,
    device_id         INT,
    upload_bytes      BIGINT   NOT NULL DEFAULT 0,
    download_bytes    BIGINT   NOT NULL DEFAULT 0,
    total_bytes       BIGINT   NOT NULL DEFAULT 0,
    policy_id         INT,
    cap_upload_mbps   FLOAT,
    cap_download_mbps FLOAT,
    period_start      DATETIME NOT NULL,
    period_end        DATETIME NOT NULL,
    is_cap_exceeded   TINYINT(1) NOT NULL DEFAULT 0,
    CONSTRAINT fk_bw_user   FOREIGN KEY (user_id)   REFERENCES users(id)  ON DELETE CASCADE,
    CONSTRAINT fk_bw_device FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
    CONSTRAINT fk_bw_policy FOREIGN KEY (policy_id) REFERENCES bandwidth_policies(id) ON DELETE SET NULL,
    INDEX idx_bw_user   (user_id),
    INDEX idx_bw_period (period_start, period_end)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- Table 6: network_logs
-- Syslog / event archive (all FCAPS categories)
-- ============================================================
CREATE TABLE IF NOT EXISTS network_logs (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    ap_id       INT,
    device_id   INT,
    event_type  ENUM('auth_success','auth_fail','association','disassociation',
                     'roaming','dhcp','ap_offline','ap_recovered',
                     'bandwidth_exceeded','rogue_ap_detected','throttle_applied') NOT NULL,
    description TEXT,
    severity    ENUM('info','warning','critical') NOT NULL DEFAULT 'info',
    ip_address  VARCHAR(15),
    mac_address VARCHAR(17),
    timestamp   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_log_ap     FOREIGN KEY (ap_id)     REFERENCES access_points(id) ON DELETE SET NULL,
    CONSTRAINT fk_log_device FOREIGN KEY (device_id) REFERENCES devices(id)       ON DELETE SET NULL,
    INDEX idx_log_timestamp (timestamp),
    INDEX idx_log_ap        (ap_id),
    INDEX idx_log_severity  (severity)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- Table 7: alerts
-- NMS-generated fault and performance alerts
-- ============================================================
CREATE TABLE IF NOT EXISTS alerts (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    ap_id            INT,
    alert_type       ENUM('ap_offline','rogue_ap','bandwidth_exceeded','high_utilization',
                          'auth_failure_flood','interference','ap_recovered','bandwidth_warning') NOT NULL,
    severity         ENUM('low','medium','high','critical') NOT NULL,
    message          TEXT NOT NULL,
    is_acknowledged  TINYINT(1) NOT NULL DEFAULT 0,
    acknowledged_by  INT,
    created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at  DATETIME,
    CONSTRAINT fk_alert_ap   FOREIGN KEY (ap_id)           REFERENCES access_points(id) ON DELETE SET NULL,
    CONSTRAINT fk_alert_user FOREIGN KEY (acknowledged_by) REFERENCES users(id)         ON DELETE SET NULL,
    INDEX idx_alert_created  (created_at),
    INDEX idx_alert_acked    (is_acknowledged),
    INDEX idx_alert_severity (severity)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- Table 8: rogue_aps
-- Unauthorized APs detected via SNMP neighbor scanning
-- ============================================================
CREATE TABLE IF NOT EXISTS rogue_aps (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    mac_address       VARCHAR(17) NOT NULL,
    ssid              VARCHAR(100),
    signal_strength   INT,
    detected_at       DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    detected_by_ap_id INT,
    status            ENUM('pending','confirmed','dismissed') NOT NULL DEFAULT 'pending',
    channel           INT,
    CONSTRAINT fk_rogue_ap FOREIGN KEY (detected_by_ap_id) REFERENCES access_points(id) ON DELETE SET NULL,
    INDEX idx_rogue_mac    (mac_address),
    INDEX idx_rogue_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
