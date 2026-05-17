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
