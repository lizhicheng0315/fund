import re
import time
from datetime import datetime, timedelta
from decimal import Decimal
from flask import current_app
from models import db, Fund, FundNav, FundWeekly
import requests

NAV_URL = 'https://fund.eastmoney.com/f10/F10DataApi.aspx'


def fetch_nav_page(fund_code, page=1, per_page=40, start_date=None, end_date=None):
    """Fetch one page of NAV data. Returns (records, total_pages).
    Each record: (nav_date, nav, acc_nav)."""
    params = {
        'fundCode': fund_code,
        'pageIndex': page,
        'pageSize': per_page,
    }
    if start_date:
        params['beginDate'] = start_date
    if end_date:
        params['endDate'] = end_date

    resp = requests.get(NAV_URL, params=params, timeout=30)
    resp.encoding = 'utf-8'
    text = resp.text

    # Parse total pages
    pages_match = re.search(r'pages:\s*(\d+)', text)
    total_pages = int(pages_match.group(1)) if pages_match else 0

    # Parse table rows: <td>2026-01-10</td><td>1.2345</td><td>1.2345</td>...
    # Columns: date, nav, acc_nav, change_pct
    row_pattern = r'<td>(\d{4}-\d{2}-\d{2})</td>\s*<td[^>]*>([\d.]+)</td>\s*<td[^>]*>([\d.]+)</td>'
    rows = re.findall(row_pattern, text)

    records = []
    for date_str, nav_str, acc_nav_str in rows:
        nav_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        nav = Decimal(nav_str)
        acc_nav = Decimal(acc_nav_str)
        records.append((nav_date, nav, acc_nav))

    return records, total_pages


def fetch_all_nav(fund_code, start_date=None, end_date=None):
    """Fetch all pages of NAV data for a fund."""
    all_records = []
    page = 1
    while True:
        records, total_pages = fetch_nav_page(fund_code, page=page, start_date=start_date, end_date=end_date)
        all_records.extend(records)
        if page >= total_pages:
            break
        page += 1
        time.sleep(0.2)
    return all_records


def save_nav_data(fund_code, records):
    """Save NAV records to database, skip duplicates."""
    saved = 0
    for nav_date, nav, acc_nav in records:
        existing = FundNav.query.filter_by(fund_code=fund_code, nav_date=nav_date).first()
        if existing:
            continue
        db.session.add(FundNav(fund_code=fund_code, nav_date=nav_date, nav=nav, acc_nav=acc_nav))
        saved += 1
    db.session.commit()
    return saved


def compute_weekly_changes(fund_code, start_date=None, end_date=None):
    """Compute weekly change_pct from fund_nav and save to fund_weekly."""
    query = FundNav.query.filter_by(fund_code=fund_code).order_by(FundNav.nav_date)
    if start_date:
        query = query.filter(FundNav.nav_date >= start_date)
    if end_date:
        query = query.filter(FundNav.nav_date <= end_date)

    nav_records = query.all()
    if not nav_records:
        return 0

    # Group by ISO week
    from collections import defaultdict
    weeks = defaultdict(list)
    for r in nav_records:
        iso_year, iso_week, _ = r.nav_date.isocalendar()
        weeks[(iso_year, iso_week)].append(r)

    saved = 0
    for (iso_year, iso_week), week_records in sorted(weeks.items()):
        week_records.sort(key=lambda r: r.nav_date)
        week_start = week_records[0].nav_date
        week_end = week_records[-1].nav_date
        nav_start = week_records[0].nav
        nav_end = week_records[-1].nav

        if nav_start == 0:
            continue

        change_pct = (nav_end - nav_start) / nav_start * Decimal('100')

        existing = FundWeekly.query.filter_by(fund_code=fund_code, week_start=week_start).first()
        if existing:
            existing.week_end = week_end
            existing.change_pct = change_pct
        else:
            db.session.add(FundWeekly(
                fund_code=fund_code,
                week_start=week_start,
                week_end=week_end,
                change_pct=change_pct
            ))
        saved += 1

    db.session.commit()
    return saved


def crawl_fund_nav(app, fund_code, start_date=None, end_date=None):
    """Crawl and persist NAV data for a single fund, then compute weekly changes."""
    interval = app.config.get('CRAWLER_INTERVAL_SECONDS', 0.5)
    with app.app_context():
        records = fetch_all_nav(fund_code, start_date=start_date, end_date=end_date)
        time.sleep(interval)
        saved_nav = save_nav_data(fund_code, records)
        saved_weekly = compute_weekly_changes(fund_code, start_date=start_date, end_date=end_date)
        return {'fund_code': fund_code, 'nav_saved': saved_nav, 'weekly_saved': saved_weekly}
