import re
import requests
from models import db, Fund, FundCategory

FUND_TYPES = {
    'gp': '股票型',
    'hh': '混合型',
    'zq': '债券型',
    'zs': '指数型',
    'qdii': 'QDII',
    'fof': 'FOF',
    'hb': '货币型',
    'fim': '理财型',
}

RANK_URL = 'https://fund.eastmoney.com/Data/FundGuideapi.aspx'


def fetch_fund_list():
    """Fetch fund list from eastmoney ranking API. Returns list of tuples: (code, name, category_name)."""
    all_funds = []
    for ft_code, ft_name in FUND_TYPES.items():
        page = 1
        while True:
            params = {
                'dt': '0',
                'ft': ft_code,
                'sd': '',
                'ed': '',
                'sc': 'z',
                'st': 'desc',
                'pi': str(page),
                'pn': '500',
                'zf': 'diy',
                'sh': 'list',
            }
            resp = requests.get(RANK_URL, params=params, timeout=30)
            text = resp.content.decode('utf-8')

            # Parse datacount and datas
            count_match = re.search(r'datacount\":\"(\d+)\"', text)
            total = int(count_match.group(1)) if count_match else 0

            datas_match = re.search(r'datas\":\[(.*?)\]', text)
            if not datas_match:
                break

            raw_items = datas_match.group(1).split('","')
            for item in raw_items:
                item = item.strip('"')
                fields = item.split(',')
                if len(fields) >= 4:
                    code = fields[0]
                    name = fields[1]
                    category = fields[3]
                    all_funds.append((code, name, category))

            if page * 500 >= total:
                break
            page += 1

    return all_funds


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
