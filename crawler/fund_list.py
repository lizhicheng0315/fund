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
