from decimal import Decimal
from models import db, Fund, FundWeekly
from extensions import cache


@cache.cached(timeout=3600, query_string=True)
def get_category_ranking(category_id, start_date, end_date, sort='desc'):
    """Compute ranking of all funds in a category by cumulative change over a period."""
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
