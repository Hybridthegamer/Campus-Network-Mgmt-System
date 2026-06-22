import csv
import io
from datetime import datetime, timedelta
from flask import render_template, request, send_file, flash, redirect, url_for
from flask_login import login_required
from app.models import AccessPoint, NetworkLog, Alert, BandwidthUsage
from . import reports_bp

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


@reports_bp.route('/')
@login_required
def index():
    return render_template('reports/index.html', reportlab_available=REPORTLAB_AVAILABLE)


@reports_bp.route('/generate', methods=['POST'])
@login_required
def generate():
    report_type = request.form.get('report_type', 'ap_uptime')
    fmt = request.form.get('format', 'csv')
    date_from_str = request.form.get('date_from', '')
    date_to_str = request.form.get('date_to', '')
    try:
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d') if date_from_str else datetime.utcnow() - timedelta(days=7)
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d') + timedelta(days=1) if date_to_str else datetime.utcnow()
    except ValueError:
        flash('Invalid date format.', 'danger')
        return redirect(url_for('reports.index'))
    dispatch = {'ap_uptime': _ap_uptime_report, 'bandwidth': _bandwidth_report,
                'auth_log': _auth_log_report, 'alert_summary': _alert_summary_report}
    fn = dispatch.get(report_type)
    if not fn:
        flash('Unknown report type.', 'danger')
        return redirect(url_for('reports.index'))
    if report_type == 'ap_uptime':
        return fn(fmt)
    return fn(fmt, date_from, date_to)


def _ap_uptime_report(fmt):
    aps = AccessPoint.query.order_by(AccessPoint.building, AccessPoint.ap_name).all()
    headers = ['AP Name', 'Building', 'Floor', 'IP Address', 'Status', 'Uptime', 'Clients', 'Channel Util %']
    rows = [[ap.ap_name, ap.building or '', ap.floor or '', ap.ip_address, ap.status,
             ap.get_uptime_formatted(), ap.client_count or 0,
             f'{ap.channel_utilization or 0:.1f}'] for ap in aps]
    if fmt == 'pdf' and REPORTLAB_AVAILABLE:
        return _make_pdf('AP Uptime Report', headers, rows, 'ap_uptime_report.pdf')
    return _make_csv(headers, rows, 'ap_uptime_report.csv')


def _bandwidth_report(fmt, date_from, date_to):
    records = (BandwidthUsage.query
               .filter(BandwidthUsage.period_start >= date_from, BandwidthUsage.period_start <= date_to)
               .order_by(BandwidthUsage.total_bytes.desc()).all())
    headers = ['User ID', 'Upload (MB)', 'Download (MB)', 'Total (MB)', 'Cap Exceeded', 'Period Start', 'Period End']
    rows = [[r.user_id or 'N/A', r.get_upload_mb(), r.get_download_mb(), r.get_total_mb(),
             'Yes' if r.is_cap_exceeded else 'No',
             r.period_start.strftime('%Y-%m-%d') if r.period_start else '',
             r.period_end.strftime('%Y-%m-%d') if r.period_end else ''] for r in records]
    if fmt == 'pdf' and REPORTLAB_AVAILABLE:
        return _make_pdf('Bandwidth Usage Report', headers, rows, 'bandwidth_report.pdf')
    return _make_csv(headers, rows, 'bandwidth_report.csv')


def _auth_log_report(fmt, date_from, date_to):
    logs = (NetworkLog.query
            .filter(NetworkLog.event_type.in_(['auth_success', 'auth_fail']),
                    NetworkLog.timestamp >= date_from, NetworkLog.timestamp <= date_to)
            .order_by(NetworkLog.timestamp.desc()).all())
    headers = ['Timestamp', 'Event Type', 'Severity', 'MAC Address', 'IP Address', 'Description']
    rows = [[l.timestamp.strftime('%Y-%m-%d %H:%M:%S') if l.timestamp else '', l.event_type,
             l.severity, l.mac_address or '', l.ip_address or '',
             (l.description or '')[:80]] for l in logs]
    if fmt == 'pdf' and REPORTLAB_AVAILABLE:
        return _make_pdf('Authentication Log Report', headers, rows, 'auth_log_report.pdf')
    return _make_csv(headers, rows, 'auth_log_report.csv')


def _alert_summary_report(fmt, date_from, date_to):
    alerts = (Alert.query
              .filter(Alert.created_at >= date_from, Alert.created_at <= date_to)
              .order_by(Alert.created_at.desc()).all())
    headers = ['ID', 'Type', 'Severity', 'Message', 'Acknowledged', 'Created At']
    rows = [[a.id, a.alert_type, a.severity, (a.message or '')[:60],
             'Yes' if a.is_acknowledged else 'No',
             a.created_at.strftime('%Y-%m-%d %H:%M') if a.created_at else ''] for a in alerts]
    if fmt == 'pdf' and REPORTLAB_AVAILABLE:
        return _make_pdf('Alert Summary Report', headers, rows, 'alert_summary_report.pdf')
    return _make_csv(headers, rows, 'alert_summary_report.csv')


def _make_csv(headers, rows, filename):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode('utf-8')), mimetype='text/csv',
                     as_attachment=True, download_name=filename)


def _make_pdf(title, headers, rows, filename):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = [Paragraph(title, styles['Title']), Spacer(1, 12),
                Paragraph(f'Generated: {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}', styles['Normal']),
                Spacer(1, 12)]
    table_data = [headers] + [[str(c) for c in row] for row in rows]
    t = Table(table_data, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d6efd')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(t)
    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name=filename)
