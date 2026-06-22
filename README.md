# Wireless Campus Network Management System (WCNMS)

A centralised, web-based Network Management System for monitoring, managing, and securing wireless access points across a university campus. Built as a Final Year Project aligned with the FCAPS model (Fault, Configuration, Accounting, Performance, Security management) and the IEEE 802.11 / 802.1X standards.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Tool Stack & Rationale](#tool-stack--rationale)
3. [System Requirements](#system-requirements)
4. [Quick Start (Docker)](#quick-start-docker)
5. [Manual Setup](#manual-setup)
6. [Default Credentials](#default-credentials)
7. [Project Structure](#project-structure)
8. [Key Features](#key-features)
9. [Architecture](#architecture)
10. [Algorithms Implemented](#algorithms-implemented)

---

## System Overview

The WCNMS provides network administrators with a single pane of glass to:

- **Monitor** all IEEE 802.11ac Access Points via simulated SNMPv3 polling every 60 seconds
- **Manage** AP provisioning, user accounts, and bandwidth policies
- **Detect** rogue (unauthorised) APs via automated neighbour scanning every 300 seconds
- **Enforce** per-user bandwidth caps with automatic throttling notifications
- **Alert** administrators via in-app notifications for AP failures, high utilisation, and security events
- **Report** on AP uptime, bandwidth usage, authentication logs, and alert summaries (CSV and PDF)

The system simulates integration with FreeRADIUS (802.1X/EAP-TTLS authentication) and a Cisco Wireless LAN Controller (CAPWAP-based AP management) — making it fully functional for demonstration and testing without physical network hardware.

---

## Tool Stack & Rationale

| Layer | Technology | Version | Reason for Choice |
|---|---|---|---|
| **Backend Framework** | Python / Flask | 3.0.x | Lightweight, modular blueprint architecture maps cleanly to the FCAPS management domains. Extensive SNMP library support (`pysnmp`). Faster development cycle than Java EE; more control than Django for a custom NMS. |
| **Database** | MySQL | 8.0 | Specified in the project design (Chapter 3). Mature, widely supported, strong referential integrity with InnoDB. Schema designed in 3NF. |
| **ORM** | Flask-SQLAlchemy | 3.1.x | Decouples business logic from raw SQL; supports MySQL and SQLite (testing). Enables clean model definitions and relationship navigation. |
| **Authentication** | Flask-Login + bcrypt | 0.6.x / 4.1.x | Session-based login aligned with the 802.1X/RBAC requirement. bcrypt provides strong adaptive hashing (cost factor 12) for password storage — credentials never stored in plaintext as required by the specification. |
| **SNMP Polling** | pysnmp | 4.4.x | De-facto Python SNMP library supporting SNMPv1/v2c/v3. Chosen over net-snmp CLI wrappers for in-process polling without shell injection risk. |
| **Background Scheduler** | APScheduler | 3.10.x | Runs the three core algorithms (SNMP poll every 60 s, rogue AP scan every 300 s, bandwidth enforcement every 120 s) as daemon threads inside the Flask process. No separate Celery/Redis infrastructure required for deployment at campus scale. |
| **Frontend** | Bootstrap 5 + Chart.js | 5.3 / 4.4 | Responsive, accessible UI without a JavaScript framework build step. Chart.js provides the doughnut and bar charts on the dashboard. Bootstrap's utility classes reduce custom CSS. |
| **Email Alerts** | Flask-Mail | 0.10.x | SMTP integration for alert notifications. Supports TLS (port 587) as required by the non-functional security specification. |
| **PDF Export** | ReportLab | 4.2.x | Pure-Python PDF generation; no system dependencies (unlike WeasyPrint which requires Cairo). Produces publication-quality tabular reports suitable for Chapter 5 results documentation. |
| **Containerisation** | Docker + Docker Compose | — | Ensures reproducible deployment across Windows, macOS, and Linux lab environments. MySQL 8.0 and the Flask app run in isolated containers with a shared internal network. |
| **WSGI Server** | Gunicorn | 22.0.x | Production-grade Python WSGI server. Supports multiple worker processes for handling concurrent SNMP polling threads alongside HTTP requests. |

---

## System Requirements

### Minimum Hardware
| Component | Minimum | Recommended |
|---|---|---|
| CPU | 2 cores | 4 cores |
| RAM | 2 GB | 4 GB |
| Disk | 5 GB free | 20 GB |
| Network | 100 Mbps | 1 Gbps |

### Software Requirements

**Option A — Docker (recommended)**
- Docker Engine 24+ and Docker Compose v2+
- Any OS: Linux, macOS, or Windows 10/11 with WSL 2

**Option B — Manual**
- Python 3.11+
- MySQL Server 8.0+
- pip / virtualenv

---

## Quick Start (Docker)

```bash
# 1. Clone the repository
git clone https://github.com/hybridthegamer/campus-network-mgmt-system.git
cd campus-network-mgmt-system

# 2. Copy environment file and set a strong secret key
cp .env.example .env
# Edit .env — set SECRET_KEY to a random string

# 3. Build and start containers (first run takes ~2–3 minutes)
docker compose up --build -d

# 4. Open the browser
open http://localhost:5000
```

The `docker-compose.yml` automatically:
- Starts MySQL 8.0 and waits for it to be healthy
- Runs `flask init-db` to create tables and seed demo data
- Starts Gunicorn with 2 workers on port 5000

---

## Manual Setup

```bash
# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Configure MySQL
mysql -u root -p << 'SQL'
CREATE DATABASE wcnms_db CHARACTER SET utf8mb4;
CREATE USER 'wcnms'@'localhost' IDENTIFIED BY 'wcnms_pass';
GRANT ALL PRIVILEGES ON wcnms_db.* TO 'wcnms'@'localhost';
FLUSH PRIVILEGES;
SQL

# 4. Set environment variables
cp .env.example .env
# Edit .env with your DATABASE_URL and SECRET_KEY

# 5. Create tables and seed demo data
flask --app run init-db

# 6. Run the development server
python run.py
# → http://localhost:5000
```

---

## Default Credentials

| Username | Password | Role |
|---|---|---|
| `superadmin` | `Admin123!` | Super Admin — full system access |
| `netadmin` | `Admin123!` | Admin — manage APs, users, policies |
| `viewer` | `Admin123!` | Read Only — view dashboards and reports |

> **Change these passwords immediately in any production deployment.**

---

## Project Structure

```
campus-network-mgmt-system/
├── app/
│   ├── __init__.py              # Flask app factory, blueprint registration, APScheduler init
│   ├── models.py                # SQLAlchemy models (8 tables, 3NF schema)
│   ├── auth/                    # Authentication blueprint (login/logout)
│   ├── dashboard/               # Main dashboard with live stats
│   ├── access_points/           # AP CRUD and detail views
│   ├── users_mgmt/              # User account management (RBAC)
│   ├── monitoring/              # Real-time SNMP monitoring view
│   ├── alerts/                  # Alert management with AJAX acknowledgement
│   ├── bandwidth/               # Policy management and usage tracking
│   ├── reports/                 # CSV/PDF report generation
│   ├── api/                     # REST JSON API (v1)
│   ├── services/
│   │   ├── snmp_service.py      # Algorithm 1 — SNMP polling (60 s)
│   │   ├── rogue_ap_detector.py # Algorithm 2 — Rogue AP detection (300 s)
│   │   ├── bandwidth_enforcer.py# Algorithm 3 — Bandwidth enforcement (120 s)
│   │   └── alert_service.py     # Alert creation helpers
│   ├── static/css/main.css      # Custom CSS (sidebar layout, card styles)
│   └── templates/               # Jinja2 HTML templates (Bootstrap 5)
├── migrations/init.sql          # Full MySQL schema with indices and FK constraints
├── config.py                    # Environment-based config (Dev/Prod/Test)
├── run.py                       # App entry point + flask init-db CLI command
├── requirements.txt             # Python dependencies (pinned versions)
├── Dockerfile                   # Python 3.11-slim image
├── docker-compose.yml           # MySQL 8.0 + Flask services
└── .env.example                 # Environment variable template
```

---

## Key Features

### Dashboard
- Real-time stat cards: total APs, online APs, active users, active alerts
- Doughnut chart showing AP online/degraded/offline distribution
- Bar chart of connected clients per AP
- AP status map table with colour-coded health indicators
- Recent alerts and network event log
- Auto-refreshes stats via REST API every 60 seconds

### Access Point Management
- Paginated, searchable, filterable AP table
- Per-AP detail view with uptime, channel utilisation, client count
- AP provisioning wizard (SSID, VLAN, channel, TX power, firmware)
- Edit and delete operations (admin/super-admin only)

### Real-Time Monitoring
- Live SNMP metrics for every AP: client count, channel utilisation, uptime
- Auto-refreshes every 30 seconds
- Recent network event log (last 50 events)

### Security & Authentication
- RBAC: Super Admin, Admin, Read-Only roles
- All passwords hashed with bcrypt (cost factor 12)
- Session-based auth with remember-me
- CSRF protection on all forms (Flask-WTF)
- Input validation client-side (JS) and server-side (Python)

### Alerts
- AJAX-based single-alert and bulk acknowledgement
- Filterable by severity, type, and acknowledgement status
- Colour-coded rows (critical = red, high = yellow)
- Automatic alert deduplication (no duplicate unacknowledged alerts for same AP/type)

### Reports
- AP Uptime Report
- Bandwidth Usage Report
- Authentication Log Report
- Alert Summary Report
- Export to CSV (always available) or PDF (requires ReportLab)

### REST API
| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/aps` | GET | List all APs with status |
| `/api/v1/aps/<id>` | GET | AP detail |
| `/api/v1/alerts` | GET | List active alerts |
| `/api/v1/alerts/<id>/acknowledge` | POST | Acknowledge alert |
| `/api/v1/dashboard/stats` | GET | Live dashboard statistics |
| `/api/v1/monitoring/live` | GET | All AP SNMP metrics |
| `/api/v1/logs` | GET | Recent network logs |

---

## Architecture

The system implements the three-tier hierarchical campus network architecture described in Chapter 3:

```
Internet ──► Core Switch (Cisco Catalyst 9500)
                │
     ┌──────────┼──────────┐
     ▼          ▼          ▼
  Dist-A     Dist-B     Dist-C
(Academic) (Admin)   (Hostel)
     │          │          │
   APs        APs        APs
(VLAN 10)  (VLAN 20)  (VLAN 30)

Management Plane (campus data centre):
  ┌─────────────┐  ┌───────────────┐  ┌─────────────┐
  │ WLAN Ctrl   │  │ FreeRADIUS    │  │ NMS (Flask) │
  │ (CAPWAP)    │  │ 802.1X/EAP    │  │ + MySQL 8.0 │
  └─────────────┘  └───────────────┘  └─────────────┘
```

---

## Algorithms Implemented

### Algorithm 1 — SNMP Polling (`services/snmp_service.py`)
Runs every **60 seconds**. Polls each registered AP for: client count, channel utilisation, uptime, and reachability. Creates `ap_offline` critical alerts for unreachable APs and `high_utilization` high alerts when channel utilisation exceeds 80%.

### Algorithm 2 — Rogue AP Detection (`services/rogue_ap_detector.py`)
Runs every **300 seconds**. Queries the authorised AP MAC list, simulates SNMP neighbour scanning on each online AP, and flags unknown MAC addresses as rogue APs. Creates critical alerts for new rogues and escalates to highest priority if signal strength > -50 dBm.

### Algorithm 3 — Bandwidth Policy Enforcement (`services/bandwidth_enforcer.py`)
Runs every **120 seconds**. Checks all active bandwidth usage records against assigned policy caps. Issues a warning alert at 90% consumption and a `bandwidth_exceeded` high alert with simulated WLC throttle command at 100%. Resets usage counters at midnight for the new daily period.

---

## References

- IEEE Std 802.11-2020 — Wireless LAN MAC and PHY Specifications
- ITU-T M.3400 — FCAPS Network Management Functions
- RFC 5415 — CAPWAP Protocol Specification
- RFC 2865 — Remote Authentication Dial-In User Service (RADIUS)
- Cisco Systems (2023) — Cisco WLC Configuration Guide, Release 8.10
- Turnbull, J. (2016) — *The Art of Monitoring* (Nagios/Zabbix evaluation)
