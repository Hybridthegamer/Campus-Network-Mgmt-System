import os
from app import create_app
from app.models import db, User, AccessPoint, BandwidthPolicy, BandwidthUsage, NetworkLog, Alert
from datetime import datetime, timedelta
import random

app = create_app(os.environ.get('FLASK_ENV', 'default'))


@app.cli.command('init-db')
def init_db():
    """Create tables and seed demo data."""
    with app.app_context():
        db.create_all()
        print('Tables created.')

        if User.query.count() == 0:
            users = [
                User(username='superadmin', email='superadmin@wcnms.local',
                     full_name='Super Administrator', role='super_admin',
                     department='ICT', phone='+234 800 000 0001', is_active=True),
                User(username='netadmin', email='netadmin@wcnms.local',
                     full_name='Network Administrator', role='admin',
                     department='ICT', phone='+234 800 000 0002', is_active=True),
                User(username='viewer', email='viewer@wcnms.local',
                     full_name='Monitoring Viewer', role='read_only',
                     department='ICT', phone='+234 800 000 0003', is_active=True),
            ]
            for u in users:
                u.set_password('Admin123!')
            db.session.add_all(users)
            db.session.commit()
            print('Seed users created (password: Admin123!)')

        if BandwidthPolicy.query.count() == 0:
            policies = [
                BandwidthPolicy(policy_name='Student Policy', upload_cap_mbps=5.0,
                                download_cap_mbps=10.0, priority=3,
                                target_role='student',
                                description='Standard student bandwidth allocation'),
                BandwidthPolicy(policy_name='Staff Policy', upload_cap_mbps=20.0,
                                download_cap_mbps=50.0, priority=7,
                                target_role='staff',
                                description='Academic and administrative staff policy'),
                BandwidthPolicy(policy_name='Guest Policy', upload_cap_mbps=2.0,
                                download_cap_mbps=5.0, priority=1,
                                target_role='guest',
                                description='Guest / visitor restricted access'),
            ]
            db.session.add_all(policies)
            db.session.commit()
            print('Bandwidth policies created.')

        if AccessPoint.query.count() == 0:
            ap_data = [
                ('AP-ACAD-01', 'Academic Block', 'G', '192.168.10.1', 'A0:B1:C2:D3:E4:01', 'Lecture Hall A, Ground Floor'),
                ('AP-ACAD-02', 'Academic Block', '1', '192.168.10.2', 'A0:B1:C2:D3:E4:02', 'Computer Lab 1, First Floor'),
                ('AP-ACAD-03', 'Academic Block', '2', '192.168.10.3', 'A0:B1:C2:D3:E4:03', 'Seminar Room 2, Second Floor'),
                ('AP-ACAD-04', 'Academic Block', 'G', '192.168.10.4', 'A0:B1:C2:D3:E4:04', 'Library Annex, Ground Floor'),
                ('AP-ADMIN-01', 'Administrative Block', 'G', '192.168.20.1', 'B0:B1:C2:D3:E4:01', 'Reception / Lobby'),
                ('AP-ADMIN-02', 'Administrative Block', '1', '192.168.20.2', 'B0:B1:C2:D3:E4:02', 'Finance Office, First Floor'),
                ('AP-ADMIN-03', 'Administrative Block', '2', '192.168.20.3', 'B0:B1:C2:D3:E4:03', 'VC Office Suite, Second Floor'),
                ('AP-HOST-01',  'Hostel Block', 'G', '192.168.30.1', 'C0:B1:C2:D3:E4:01', 'Hostel A Common Room'),
                ('AP-HOST-02',  'Hostel Block', '1', '192.168.30.2', 'C0:B1:C2:D3:E4:02', 'Hostel B First Floor Corridor'),
                ('AP-HOST-03',  'Hostel Block', '2', '192.168.30.3', 'C0:B1:C2:D3:E4:03', 'Hostel C Rooftop Lounge'),
            ]
            channels_24 = [1, 6, 11, 1, 6, 11, 1, 6, 11, 1]
            channels_5  = [36, 40, 44, 48, 149, 153, 157, 161, 36, 44]
            statuses = ['online', 'online', 'online', 'online', 'online',
                        'online', 'degraded', 'online', 'online', 'offline']
            aps = []
            for i, (name, building, floor, ip, mac, loc) in enumerate(ap_data):
                ap = AccessPoint(
                    ap_name=name, building=building, floor=floor,
                    ip_address=ip, mac_address=mac, location=loc,
                    ssid='CampusNet', vlan_id=10 if building == 'Academic Block' else 20,
                    channel_24ghz=channels_24[i], channel_5ghz=channels_5[i],
                    tx_power=20, firmware_version='8.10.185.0',
                    status=statuses[i],
                    client_count=random.randint(0, 45) if statuses[i] == 'online' else 0,
                    channel_utilization=round(random.uniform(15, 75), 1) if statuses[i] != 'offline' else 0,
                    uptime_seconds=random.randint(3600, 864000),
                    last_polled=datetime.utcnow(),
                )
                aps.append(ap)
            db.session.add_all(aps)
            db.session.commit()
            print('10 sample access points created.')

        if NetworkLog.query.count() == 0:
            aps = AccessPoint.query.all()
            user = User.query.filter_by(role='read_only').first()
            events = ['auth_success', 'auth_fail', 'association', 'disassociation', 'dhcp', 'roaming']
            severities = {'auth_success': 'info', 'auth_fail': 'warning',
                          'association': 'info', 'disassociation': 'info',
                          'dhcp': 'info', 'roaming': 'info'}
            logs = []
            for _ in range(30):
                ap = random.choice(aps)
                ev = random.choice(events)
                mac = ':'.join(f'{random.randint(0,255):02X}' for _ in range(6))
                logs.append(NetworkLog(
                    ap_id=ap.id, event_type=ev,
                    description=f'{ev.replace("_"," ").title()} event on {ap.ap_name}',
                    severity=severities[ev], mac_address=mac,
                    ip_address=f'192.168.{random.randint(10,30)}.{random.randint(2,254)}',
                    timestamp=datetime.utcnow() - timedelta(minutes=random.randint(1, 1440)),
                ))
            db.session.add_all(logs)
            db.session.commit()
            print('30 sample network logs created.')

        if Alert.query.count() == 0:
            aps = AccessPoint.query.all()
            sample_alerts = [
                Alert(ap_id=aps[9].id, alert_type='ap_offline', severity='critical',
                      message=f'{aps[9].ap_name} is offline — no SNMP response for 120s.',
                      is_acknowledged=False),
                Alert(ap_id=aps[6].id, alert_type='high_utilization', severity='high',
                      message=f'{aps[6].ap_name} channel utilization at 81.3% — exceeds threshold.',
                      is_acknowledged=False),
                Alert(alert_type='bandwidth_exceeded', severity='high',
                      message='User ID 3 exceeded download cap of 10.0 Mbps.',
                      is_acknowledged=False),
                Alert(alert_type='rogue_ap', severity='critical',
                      message='Rogue AP detected: MAC DE:AD:BE:EF:00:01, SSID "FreeWiFi", Signal -42 dBm, Channel 6.',
                      is_acknowledged=False),
                Alert(ap_id=aps[0].id, alert_type='ap_recovered', severity='low',
                      message=f'{aps[0].ap_name} recovered and is back online.',
                      is_acknowledged=True),
            ]
            db.session.add_all(sample_alerts)
            db.session.commit()
            print('Sample alerts created.')

        print('\nDatabase initialised successfully.')
        print('Login credentials:')
        print('  superadmin / Admin123!  (Super Admin)')
        print('  netadmin   / Admin123!  (Admin)')
        print('  viewer     / Admin123!  (Read Only)')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
