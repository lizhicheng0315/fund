# 基金周度涨跌幅工具 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a tool to query weekly fund performance with category-based ranking, backed by MySQL and a scheduled crawler.

**Architecture:** Flask backend serves REST APIs from MySQL data. A scheduled crawler fetches fund list and NAV data from eastmoney APIs and stores them in MySQL. Frontend is a single HTML page with Chart.js for visualization.

**Tech Stack:** Python, Flask, Flask-SQLAlchemy, Flask-Caching, Flask-APScheduler, requests, pymysql, MySQL, HTML/CSS/JS, Chart.js

---

## File Structure

| File | Responsibility |
|------|---------------|
| `config.py` | DB connection, crawler params, cache config |
| `models.py` | SQLAlchemy models for all 4 tables |
| `app.py` | Flask app factory, blueprint registration, scheduler init |
| `requirements.txt` | Python dependencies |
| `sql/init.sql` | DDL script for all tables |
| `crawler/__init__.py` | Package init |
| `crawler/fund_list.py` | Fetch and persist fund list + categories from eastmoney |
| `crawler/fund_nav.py` | Fetch and persist daily NAV, compute weekly change |
| `crawler/scheduler.py` | APScheduler job: weekly incremental crawl |
| `api/__init__.py` | Package init, register blueprints |
| `api/fund.py` | Blueprint: search, categories, performance, ranking |
| `api/crawler.py` | Blueprint: trigger crawler run |
| `service/__init__.py` | Package init |
| `service/fund_service.py` | Query funds, categories, weekly performance |
| `service/ranking_service.py` | Compute category ranking with cumulative change |
| `static/index.html` | Main page structure |
| `static/style.css` | Styling |
| `static/app.js` | Frontend logic: search, query, render tables/chart |

---

### Task 1: Project Scaffold and Config

**Files:**
- Create: `requirements.txt`
- Create: `config.py`

- [ ] **Step 1: Create requirements.txt**

```
Flask==3.1.1
Flask-SQLAlchemy==3.1.1
Flask-Caching==2.3.1
Flask-APScheduler==1.13.1
requests==2.32.3
pymysql==1.1.1
```

- [ ] **Step 2: Create config.py**

```python
import os

class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URI',
        'mysql+pymysql://root:root@localhost:3306/fund?charset=utf8mb4'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 3600
    CRAWLER_INTERVAL_SECONDS = 0.5
    SCHEDULER_API_ENABLED = True
```

- [ ] **Step 3: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: all packages install successfully

- [ ] **Step 4: Commit**

```bash
git add requirements.txt config.py
git commit -m "feat: project scaffold with config and dependencies"
```

---

### Task 2: Database Schema and SQLAlchemy Models

**Files:**
- Create: `sql/init.sql`
- Create: `models.py`

- [ ] **Step 1: Create sql/init.sql**

```sql
CREATE DATABASE IF NOT EXISTS fund DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE fund;

CREATE TABLE IF NOT EXISTS fund_categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS funds (
    code VARCHAR(6) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category_id INT,
    FOREIGN KEY (category_id) REFERENCES fund_categories(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS fund_nav (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fund_code VARCHAR(6) NOT NULL,
    nav_date DATE NOT NULL,
    nav DECIMAL(10,4) NOT NULL,
    acc_nav DECIMAL(10,4) NOT NULL,
    FOREIGN KEY (fund_code) REFERENCES funds(code),
    UNIQUE KEY uk_fund_date (fund_code, nav_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS fund_weekly (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fund_code VARCHAR(6) NOT NULL,
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    change_pct DECIMAL(8,4) NOT NULL,
    FOREIGN KEY (fund_code) REFERENCES funds(code),
    UNIQUE KEY uk_fund_week (fund_code, week_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

- [ ] **Step 2: Create models.py**

```python
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class FundCategory(db.Model):
    __tablename__ = 'fund_categories'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    funds = db.relationship('Fund', backref='category', lazy='dynamic')


class Fund(db.Model):
    __tablename__ = 'funds'
    code = db.Column(db.String(6), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('fund_categories.id'))


class FundNav(db.Model):
    __tablename__ = 'fund_nav'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fund_code = db.Column(db.String(6), db.ForeignKey('funds.code'), nullable=False)
    nav_date = db.Column(db.Date, nullable=False)
    nav = db.Column(db.Numeric(10, 4), nullable=False)
    acc_nav = db.Column(db.Numeric(10, 4), nullable=False)
    __table_args__ = (db.UniqueConstraint('fund_code', 'nav_date'),)


class FundWeekly(db.Model):
    __tablename__ = 'fund_weekly'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fund_code = db.Column(db.String(6), db.ForeignKey('funds.code'), nullable=False)
    week_start = db.Column(db.Date, nullable=False)
    week_end = db.Column(db.Date, nullable=False)
    change_pct = db.Column(db.Numeric(8, 4), nullable=False)
    __table_args__ = (db.UniqueConstraint('fund_code', 'week_start'),)
```

- [ ] **Step 3: Run init.sql to create database and tables**

Run: `mysql -u root -p < sql/init.sql`
Expected: database `fund` and all 4 tables created

- [ ] **Step 4: Commit**

```bash
git add sql/init.sql models.py
git commit -m "feat: database schema and SQLAlchemy models"
```

---

### Task 3: Flask App Factory

**Files:**
- Create: `app.py`
- Create: `api/__init__.py`
- Create: `service/__init__.py`

- [ ] **Step 1: Create api/__init__.py**

```python
from .fund import fund_bp
from .crawler import crawler_bp


def register_blueprints(app):
    app.register_blueprint(fund_bp, url_prefix='/api/fund')
    app.register_blueprint(crawler_bp, url_prefix='/api/crawler')
```

- [ ] **Step 2: Create service/__init__.py**

```python
# empty init
```

- [ ] **Step 3: Create app.py**

```python
from flask import Flask
from flask_caching import Cache
from config import Config
from models import db

cache = Cache()


def create_app():
    app = Flask(__name__, static_folder='static', static_url_path='')
    app.config.from_object(Config)

    db.init_app(app)
    cache.init_app(app)

    from api import register_blueprints
    register_blueprints(app)

    from crawler.scheduler import start_scheduler
    start_scheduler(app)

    @app.route('/')
    def index():
        return app.send_static_file('index.html')

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)
```

- [ ] **Step 4: Test the app starts (will fail on missing blueprints, that's expected)**

Run: `cd E:/project/fund && python -c "from app import create_app; app = create_app(); print('OK')"`
Expected: ImportError for api.fund or api.crawler — this confirms the app factory is wired up, just needs the blueprints

- [ ] **Step 5: Commit**

```bash
git add app.py api/__init__.py service/__init__.py
git commit -m "feat: Flask app factory with blueprint registration"
```

---

### Task 4: Crawler - Fund List and Categories

**Files:**
- Create: `crawler/__init__.py`
- Create: `crawler/fund_list.py`

- [ ] **Step 1: Create crawler/__init__.py**

```python
# empty init
```

- [ ] **Step 2: Create crawler/fund_list.py**

```python
import re
import requests
from models import db, Fund, FundCategory

FUND_LIST_URL = 'https://fund.eastmoney.com/js/fundcode_search.js'


def fetch_fund_list():
    """Fetch fund list from eastmoney. Returns list of tuples: (code, name, category_name)."""
    resp = requests.get(FUND_LIST_URL, timeout=30)
    resp.encoding = 'utf-8'
    text = resp.text

    # Response format: var r = [["000001","HXCZ","华夏成长","HHGF","混合型"], ...]
    pattern = r'\["(\d{6})","[^"]*","([^"]*)","[^"]*","([^"]*)"'
    matches = re.findall(pattern, text)
    return [(code, name, category) for code, name, category in matches]


def sync_fund_list(app):
    """Fetch and persist fund list + categories into MySQL."""
    with app.app_context():
        funds_data = fetch_fund_list()
        if not funds_data:
            return {'synced': 0, 'errors': 0}

        # Sync categories
        category_names = set(cat for _, _, cat in funds_data)
        category_map = {}
        for name in category_names:
            cat = FundCategory.query.filter_by(name=name).first()
            if not cat:
                cat = FundCategory(name=name)
                db.session.add(cat)
                db.session.flush()
            category_map[name] = cat.id

        db.session.commit()

        # Sync funds
        synced = 0
        errors = 0
        for code, name, category_name in funds_data:
            try:
                existing = Fund.query.get(code)
                cat_id = category_map.get(category_name)
                if existing:
                    existing.name = name
                    existing.category_id = cat_id
                else:
                    db.session.add(Fund(code=code, name=name, category_id=cat_id))
                synced += 1
                if synced % 5000 == 0:
                    db.session.commit()
            except Exception:
                errors += 1
                db.session.rollback()

        db.session.commit()
        return {'synced': synced, 'errors': errors}
```

- [ ] **Step 3: Test fund list fetch (manual, requires network)**

Run: `cd E:/project/fund && python -c "from crawler.fund_list import fetch_fund_list; data = fetch_fund_list(); print(f'Fetched {len(data)} funds'); print(data[:3])"`
Expected: prints count and first 3 funds like `[('000001', '华夏成长', '混合型'), ...]`

- [ ] **Step 4: Commit**

```bash
git add crawler/__init__.py crawler/fund_list.py
git commit -m "feat: crawler module - fund list and category sync"
```

---

### Task 5: Crawler - NAV Data and Weekly Computation

**Files:**
- Create: `crawler/fund_nav.py`

- [ ] **Step 1: Create crawler/fund_nav.py**

```python
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
```

- [ ] **Step 2: Test NAV fetch for a single fund (manual, requires network + DB)**

Run: `cd E:/project/fund && python -c "from crawler.fund_nav import fetch_all_nav; data = fetch_all_nav('000001', start_date='2026-04-01', end_date='2026-05-17'); print(f'Fetched {len(data)} records'); print(data[:3])"`
Expected: prints count and first 3 NAV records

- [ ] **Step 3: Commit**

```bash
git add crawler/fund_nav.py
git commit -m "feat: crawler - NAV data fetch and weekly change computation"
```

---

### Task 6: Crawler - Scheduler and Full/Incremental Run

**Files:**
- Create: `crawler/scheduler.py`
- Create: `api/crawler.py`

- [ ] **Step 1: Create crawler/scheduler.py**

```python
import logging
from datetime import datetime, timedelta
from flask_apscheduler import APScheduler
from models import Fund
from crawler.fund_list import sync_fund_list
from crawler.fund_nav import crawl_fund_nav

logger = logging.getLogger(__name__)
scheduler = APScheduler()


def incremental_crawl(app):
    """Incremental crawl: sync fund list + crawl last week NAV for all funds."""
    with app.app_context():
        logger.info('Starting incremental crawl')
        result = sync_fund_list(app)
        logger.info(f'Fund list sync: {result}')

        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')

        funds = Fund.query.all()
        success = 0
        failed = 0
        for fund in funds:
            try:
                crawl_fund_nav(app, fund.code, start_date=start_date, end_date=end_date)
                success += 1
            except Exception as e:
                logger.error(f'Failed to crawl {fund.code}: {e}')
                failed += 1

        logger.info(f'Incremental crawl done: {success} success, {failed} failed')
        return {'success': success, 'failed': failed}


def full_crawl(app):
    """Full crawl: sync fund list + crawl all NAV history for all funds."""
    with app.app_context():
        logger.info('Starting full crawl')
        result = sync_fund_list(app)
        logger.info(f'Fund list sync: {result}')

        funds = Fund.query.all()
        success = 0
        failed = 0
        for fund in funds:
            try:
                crawl_fund_nav(app, fund.code)
                success += 1
            except Exception as e:
                logger.error(f'Failed to crawl {fund.code}: {e}')
                failed += 1

        logger.info(f'Full crawl done: {success} success, {failed} failed')
        return {'success': success, 'failed': failed}


def start_scheduler(app):
    """Register the weekly incremental crawl job."""
    scheduler.init_app(app)
    scheduler.add_job(
        'incremental_crawl',
        incremental_crawl,
        args=[app],
        trigger='cron',
        day_of_week='sat',
        hour=0,
        minute=30,
        id='weekly_incremental_crawl',
        replace_existing=True,
    )
    scheduler.start()
```

- [ ] **Step 2: Create api/crawler.py**

```python
from threading import Thread
from flask import Blueprint, request, jsonify, current_app
from crawler.scheduler import incremental_crawl, full_crawl

crawler_bp = Blueprint('crawler', __name__)


@crawler_bp.route('/run', methods=['POST'])
def run_crawler():
    mode = request.args.get('mode', 'increment')
    app = current_app._get_current_object()

    if mode == 'full':
        target = full_crawl
    else:
        target = incremental_crawl

    thread = Thread(target=target, args=[app])
    thread.start()

    return jsonify({'status': 'started', 'mode': mode})
```

- [ ] **Step 3: Commit**

```bash
git add crawler/scheduler.py api/crawler.py
git commit -m "feat: scheduler and crawler API trigger endpoint"
```

---

### Task 7: Service Layer - Fund and Ranking Queries

**Files:**
- Create: `service/fund_service.py`
- Create: `service/ranking_service.py`

- [ ] **Step 1: Create service/fund_service.py**

```python
from models import db, Fund, FundCategory, FundWeekly


def search_funds(keyword):
    """Search funds by code or name keyword."""
    like_pattern = f'%{keyword}%'
    funds = Fund.query.filter(
        db.or_(Fund.code.like(like_pattern), Fund.name.like(like_pattern))
    ).limit(50).all()
    return [{'code': f.code, 'name': f.name, 'category_name': f.category.name if f.category else ''} for f in funds]


def get_categories():
    """Return all fund categories."""
    cats = FundCategory.query.order_by(FundCategory.name).all()
    return [{'id': c.id, 'name': c.name} for c in cats]


def get_weekly_performance(fund_code, start_date, end_date):
    """Get weekly performance for a single fund in a date range."""
    records = FundWeekly.query.filter(
        FundWeekly.fund_code == fund_code,
        FundWeekly.week_start >= start_date,
        FundWeekly.week_end <= end_date
    ).order_by(FundWeekly.week_start).all()

    return [{
        'week_start': r.week_start.isoformat(),
        'week_end': r.week_end.isoformat(),
        'change_pct': float(r.change_pct)
    } for r in records]
```

- [ ] **Step 2: Create service/ranking_service.py**

```python
from decimal import Decimal
from models import db, Fund, FundWeekly
from app import cache


@cache.cached(timeout=3600, query_string=True)
def get_category_ranking(category_id, start_date, end_date, sort='desc'):
    """Compute ranking of all funds in a category by cumulative change over a period."""
    # Get all weekly changes for funds in this category within date range
    rows = db.session.query(
        FundWeekly.fund_code,
        Fund.code,
        Fund.name
    ).join(Fund, FundWeekly.fund_code == Fund.code).filter(
        Fund.category_id == category_id,
        FundWeekly.week_start >= start_date,
        FundWeekly.week_end <= end_date
    ).all()

    # Group by fund and compute cumulative change
    fund_changes = {}
    for row in rows:
        code = row[0]
        if code not in fund_changes:
            fund_changes[code] = {'code': row[1], 'name': row[2], 'weekly_changes': []}
        # We need the actual change_pct values
        fund_changes[code]['weekly_changes'].append(row)

    # Re-query with change_pct included
    weekly_rows = db.session.query(
        FundWeekly.fund_code,
        Fund.name,
        FundWeekly.change_pct
    ).join(Fund, FundWeekly.fund_code == Fund.code).filter(
        Fund.category_id == category_id,
        FundWeekly.week_start >= start_date,
        FundWeekly.week_end <= end_date
    ).all()

    fund_map = {}
    for row in weekly_rows:
        code = row[0]
        if code not in fund_map:
            fund_map[code] = {'code': code, 'name': row[1], 'changes': []}
        fund_map[code]['changes'].append(row[2])

    # Compute cumulative change: (1+w1)*(1+w2)*...*(1+wn) - 1
    ranking = []
    for code, info in fund_map.items():
        cumulative = Decimal('1')
        for change_pct in info['changes']:
            cumulative *= (Decimal('1') + change_pct / Decimal('100'))
        cumulative_pct = (cumulative - Decimal('1')) * Decimal('100')
        ranking.append({
            'code': code,
            'name': info['name'],
            'change_pct': float(cumulative_pct)
        })

    ranking.sort(key=lambda x: x['change_pct'], reverse=(sort == 'desc'))

    total = len(ranking)
    for i, item in enumerate(ranking):
        item['rank'] = i + 1
        item['total_funds'] = total

    return ranking
```

- [ ] **Step 3: Commit**

```bash
git add service/fund_service.py service/ranking_service.py
git commit -m "feat: service layer - fund search, performance, and ranking"
```

---

### Task 8: API Routes - Fund Endpoints

**Files:**
- Create: `api/fund.py`

- [ ] **Step 1: Create api/fund.py**

```python
from flask import Blueprint, request, jsonify
from service.fund_service import search_funds, get_categories, get_weekly_performance
from service.ranking_service import get_category_ranking

fund_bp = Blueprint('fund', __name__)


@fund_bp.route('/search')
def search():
    keyword = request.args.get('keyword', '')
    if not keyword:
        return jsonify([])
    return jsonify(search_funds(keyword))


@fund_bp.route('/categories')
def categories():
    return jsonify(get_categories())


@fund_bp.route('/performance')
def performance():
    code = request.args.get('code', '')
    start = request.args.get('start', '')
    end = request.args.get('end', '')
    if not all([code, start, end]):
        return jsonify({'error': 'code, start, end are required'}), 400
    return jsonify(get_weekly_performance(code, start, end))


@fund_bp.route('/ranking')
def ranking():
    category_id = request.args.get('category_id', '')
    start = request.args.get('start', '')
    end = request.args.get('end', '')
    sort = request.args.get('sort', 'desc')
    if not all([category_id, start, end]):
        return jsonify({'error': 'category_id, start, end are required'}), 400
    return jsonify(get_category_ranking(int(category_id), start, end, sort))
```

- [ ] **Step 2: Test app starts successfully**

Run: `cd E:/project/fund && python -c "from app import create_app; app = create_app(); print('App created OK'); print(app.url_map)"`
Expected: prints URL map with all 5 routes registered

- [ ] **Step 3: Commit**

```bash
git add api/fund.py
git commit -m "feat: API routes for fund search, categories, performance, ranking"
```

---

### Task 9: Frontend - HTML Page

**Files:**
- Create: `static/index.html`

- [ ] **Step 1: Create static/index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>基金周度涨跌幅</title>
    <link rel="stylesheet" href="/style.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
</head>
<body>
    <div class="container">
        <h1>基金周度涨跌幅查询</h1>

        <!-- Search bar -->
        <div class="search-bar">
            <input type="text" id="search-input" placeholder="输入基金代码或名称" autocomplete="off">
            <button id="search-btn">搜索</button>
            <div id="search-dropdown" class="dropdown hidden"></div>
        </div>

        <!-- Query conditions -->
        <div class="query-bar">
            <label>开始日期 <input type="date" id="start-date"></label>
            <label>结束日期 <input type="date" id="end-date"></label>
            <label>基金分类
                <select id="category-select">
                    <option value="">全部分类</option>
                </select>
            </label>
            <button id="query-rank-btn">查询排名</button>
        </div>

        <!-- Result area -->
        <div id="result-area"></div>
    </div>

    <script src="/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add static/index.html
git commit -m "feat: frontend HTML page structure"
```

---

### Task 10: Frontend - CSS Styling

**Files:**
- Create: `static/style.css`

- [ ] **Step 1: Create static/style.css**

```css
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, "Microsoft YaHei", sans-serif;
    background: #f5f5f5;
    color: #333;
}

.container {
    max-width: 960px;
    margin: 0 auto;
    padding: 24px 16px;
}

h1 {
    font-size: 22px;
    margin-bottom: 20px;
    color: #1a1a1a;
}

/* Search bar */
.search-bar {
    position: relative;
    display: flex;
    gap: 8px;
    margin-bottom: 16px;
}

.search-bar input {
    flex: 1;
    padding: 8px 12px;
    border: 1px solid #d9d9d9;
    border-radius: 4px;
    font-size: 14px;
}

.search-bar button {
    padding: 8px 20px;
    background: #1677ff;
    color: #fff;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
}

.search-bar button:hover {
    background: #0958d9;
}

.dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    right: 72px;
    background: #fff;
    border: 1px solid #d9d9d9;
    border-radius: 4px;
    max-height: 240px;
    overflow-y: auto;
    z-index: 10;
}

.dropdown.hidden {
    display: none;
}

.dropdown-item {
    padding: 8px 12px;
    cursor: pointer;
    font-size: 13px;
    display: flex;
    justify-content: space-between;
}

.dropdown-item:hover {
    background: #f0f5ff;
}

.dropdown-item .code {
    color: #1677ff;
    margin-right: 12px;
}

.dropdown-item .category {
    color: #999;
    font-size: 12px;
}

/* Query bar */
.query-bar {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
    margin-bottom: 20px;
    padding: 12px;
    background: #fff;
    border-radius: 4px;
    border: 1px solid #e8e8e8;
}

.query-bar label {
    font-size: 14px;
    display: flex;
    align-items: center;
    gap: 6px;
}

.query-bar input[type="date"],
.query-bar select {
    padding: 6px 8px;
    border: 1px solid #d9d9d9;
    border-radius: 4px;
    font-size: 14px;
}

.query-bar button {
    padding: 6px 16px;
    background: #1677ff;
    color: #fff;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
}

/* Fund info card */
.fund-card {
    background: #fff;
    border: 1px solid #e8e8e8;
    border-radius: 4px;
    padding: 16px;
    margin-bottom: 16px;
}

.fund-card .fund-name {
    font-size: 18px;
    font-weight: 600;
}

.fund-card .fund-meta {
    font-size: 13px;
    color: #666;
    margin-top: 4px;
}

/* Tables */
table {
    width: 100%;
    border-collapse: collapse;
    background: #fff;
    border: 1px solid #e8e8e8;
    border-radius: 4px;
    overflow: hidden;
    margin-bottom: 16px;
}

th, td {
    padding: 10px 12px;
    text-align: left;
    border-bottom: 1px solid #f0f0f0;
    font-size: 14px;
}

th {
    background: #fafafa;
    font-weight: 600;
}

.change-positive {
    color: #cf1322;
}

.change-negative {
    color: #3f8600;
}

tr.highlight {
    background: #fff7e6;
}

/* Chart */
.chart-container {
    background: #fff;
    border: 1px solid #e8e8e8;
    border-radius: 4px;
    padding: 16px;
    margin-bottom: 16px;
}

.chart-container canvas {
    max-height: 300px;
}

/* Empty state */
.empty-state {
    text-align: center;
    color: #999;
    padding: 40px;
    font-size: 14px;
}
```

- [ ] **Step 2: Commit**

```bash
git add static/style.css
git commit -m "feat: frontend CSS styling"
```

---

### Task 11: Frontend - JavaScript Logic

**Files:**
- Create: `static/app.js`

- [ ] **Step 1: Create static/app.js**

```javascript
const API_BASE = '/api/fund';
let chartInstance = null;
let selectedFund = null;

// --- Search ---
const searchInput = document.getElementById('search-input');
const searchBtn = document.getElementById('search-btn');
const searchDropdown = document.getElementById('search-dropdown');

async function doSearch() {
    const keyword = searchInput.value.trim();
    if (!keyword) return;
    const resp = await fetch(`${API_BASE}/search?keyword=${encodeURIComponent(keyword)}`);
    const funds = await resp.json();
    renderDropdown(funds);
}

function renderDropdown(funds) {
    if (!funds.length) {
        searchDropdown.innerHTML = '<div class="dropdown-item">无匹配结果</div>';
        searchDropdown.classList.remove('hidden');
        return;
    }
    searchDropdown.innerHTML = funds.map(f =>
        `<div class="dropdown-item" data-code="${f.code}" data-name="${f.name}" data-category="${f.category_name}">
            <span><span class="code">${f.code}</span> ${f.name}</span>
            <span class="category">${f.category_name}</span>
        </div>`
    ).join('');
    searchDropdown.classList.remove('hidden');

    searchDropdown.querySelectorAll('.dropdown-item[data-code]').forEach(item => {
        item.addEventListener('click', () => {
            selectedFund = {
                code: item.dataset.code,
                name: item.dataset.name,
                category: item.dataset.category
            };
            searchInput.value = `${selectedFund.code} ${selectedFund.name}`;
            searchDropdown.classList.add('hidden');
            queryPerformance();
        });
    });
}

searchBtn.addEventListener('click', doSearch);
searchInput.addEventListener('keydown', e => { if (e.key === 'Enter') doSearch(); });
document.addEventListener('click', e => {
    if (!searchDropdown.contains(e.target) && e.target !== searchInput) {
        searchDropdown.classList.add('hidden');
    }
});

// --- Load categories ---
async function loadCategories() {
    const resp = await fetch(`${API_BASE}/categories`);
    const cats = await resp.json();
    const select = document.getElementById('category-select');
    cats.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c.id;
        opt.textContent = c.name;
        select.appendChild(opt);
    });
}

loadCategories();

// --- Set default dates (last 3 months) ---
function setDefaultDates() {
    const end = new Date();
    const start = new Date();
    start.setMonth(start.getMonth() - 3);
    document.getElementById('end-date').value = formatDate(end);
    document.getElementById('start-date').value = formatDate(start);
}

function formatDate(d) {
    return d.toISOString().split('T')[0];
}

setDefaultDates();

// --- Query performance ---
async function queryPerformance() {
    if (!selectedFund) return;
    const start = document.getElementById('start-date').value;
    const end = document.getElementById('end-date').value;
    if (!start || !end) return;

    const resp = await fetch(`${API_BASE}/performance?code=${selectedFund.code}&start=${start}&end=${end}`);
    const data = await resp.json();
    renderFundResult(data);
}

function renderFundResult(weeklyData) {
    const area = document.getElementById('result-area');
    let html = `<div class="fund-card">
        <div class="fund-name">${selectedFund.name}</div>
        <div class="fund-meta">${selectedFund.code} | ${selectedFund.category}</div>
    </div>`;

    if (!weeklyData.length) {
        html += '<div class="empty-state">该时间段内无数据</div>';
        area.innerHTML = html;
        return;
    }

    html += '<table><thead><tr><th>周起始日</th><th>周结束日</th><th>周涨跌幅</th></tr></thead><tbody>';
    weeklyData.forEach(w => {
        const cls = w.change_pct >= 0 ? 'change-positive' : 'change-negative';
        const sign = w.change_pct >= 0 ? '+' : '';
        html += `<tr><td>${w.week_start}</td><td>${w.week_end}</td><td class="${cls}">${sign}${w.change_pct.toFixed(2)}%</td></tr>`;
    });
    html += '</tbody></table>';
    html += '<div class="chart-container"><canvas id="weekly-chart"></canvas></div>';
    area.innerHTML = html;

    renderChart(weeklyData);
}

function renderChart(weeklyData) {
    if (chartInstance) chartInstance.destroy();
    const ctx = document.getElementById('weekly-chart').getContext('2d');
    const labels = weeklyData.map(w => w.week_start);
    const values = weeklyData.map(w => w.change_pct);

    chartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: '周涨跌幅(%)',
                data: values,
                borderColor: '#1677ff',
                backgroundColor: 'rgba(22,119,255,0.1)',
                fill: true,
                tension: 0.2
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    ticks: { callback: v => v + '%' }
                }
            }
        }
    });
}

// --- Query ranking ---
document.getElementById('query-rank-btn').addEventListener('click', queryRanking);

async function queryRanking() {
    const categoryId = document.getElementById('category-select').value;
    const start = document.getElementById('start-date').value;
    const end = document.getElementById('end-date').value;
    if (!categoryId || !start || !end) {
        alert('请选择分类和日期范围');
        return;
    }

    const resp = await fetch(`${API_BASE}/ranking?category_id=${categoryId}&start=${start}&end=${end}`);
    const data = await resp.json();
    renderRankingResult(data);
}

function renderRankingResult(ranking) {
    const area = document.getElementById('result-area');
    if (!ranking.length) {
        area.innerHTML = '<div class="empty-state">该分类在指定时间段内无数据</div>';
        return;
    }

    const selectedCode = selectedFund ? selectedFund.code : null;
    let html = `<table><thead><tr><th>排名</th><th>基金代码</th><th>基金名称</th><th>累计涨跌幅</th></tr></thead><tbody>`;
    ranking.forEach(r => {
        const isHighlight = r.code === selectedCode;
        const cls = r.change_pct >= 0 ? 'change-positive' : 'change-negative';
        const sign = r.change_pct >= 0 ? '+' : '';
        html += `<tr class="${isHighlight ? 'highlight' : ''}">
            <td>${r.rank}/${r.total_funds}</td>
            <td>${r.code}</td>
            <td>${r.name}</td>
            <td class="${cls}">${sign}${r.change_pct.toFixed(2)}%</td>
        </tr>`;
    });
    html += '</tbody></table>';
    area.innerHTML = html;
}
```

- [ ] **Step 2: Commit**

```bash
git add static/app.js
git commit -m "feat: frontend JavaScript logic - search, query, render"
```

---

### Task 12: End-to-End Smoke Test

**Files:**
- None (verification only)

- [ ] **Step 1: Start the Flask app**

Run: `cd E:/project/fund && python app.py`
Expected: Flask dev server starts on port 5000

- [ ] **Step 2: Test categories API**

Run: `curl http://localhost:5000/api/fund/categories`
Expected: JSON array of categories (empty if no data yet, which is correct before running crawler)

- [ ] **Step 3: Test search API**

Run: `curl "http://localhost:5000/api/fund/search?keyword=000001"`
Expected: JSON array (empty before crawler runs)

- [ ] **Step 4: Test crawler trigger**

Run: `curl -X POST "http://localhost:5000/api/crawler/run?mode=increment"`
Expected: `{"status":"started","mode":"increment"}`

- [ ] **Step 5: Open browser to http://localhost:5000**

Expected: Page loads with search bar, date pickers, category dropdown

- [ ] **Step 6: Final commit if any fixes were needed**

```bash
git add -A
git commit -m "fix: adjustments from end-to-end smoke test"
```

---

### Task 13: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update CLAUDE.md with project info**

Replace the placeholder content with:

```markdown
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

国内基金周度涨跌幅查询工具。Flask后端 + MySQL主数据源 + 定时爬虫 + 前端单页面。

## Commands

- Start dev server: `python app.py`
- Install dependencies: `pip install -r requirements.txt`
- Initialize database: `mysql -u root -p < sql/init.sql`
- Trigger incremental crawl: `curl -X POST http://localhost:5000/api/crawler/run?mode=increment`
- Trigger full crawl: `curl -X POST http://localhost:5000/api/crawler/run?mode=full`

## Architecture

- **Flask backend** (`app.py`) serves REST APIs and static files
- **MySQL** is the primary data source (4 tables: fund_categories, funds, fund_nav, fund_weekly)
- **Crawler** (`crawler/`) fetches data from eastmoney APIs on schedule (APScheduler, weekly Saturday 00:30)
- **Service layer** (`service/`) handles business logic: fund search, weekly performance queries, category ranking
- **API layer** (`api/`) defines Flask blueprints: `/api/fund/*` and `/api/crawler/*`
- **Frontend** (`static/`) is a single HTML page with Chart.js for visualization

Data flow: eastmoney API → crawler → MySQL → Flask API → browser
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with project commands and architecture"
```
