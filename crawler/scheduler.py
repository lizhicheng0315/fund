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
        func=incremental_crawl,
        args=[app],
        trigger='cron',
        id='weekly_incremental_crawl',
        day_of_week='sat',
        hour=0,
        minute=30,
        replace_existing=True,
    )
    scheduler.start()
