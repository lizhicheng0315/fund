from .fund import fund_bp
from .crawler import crawler_bp


def register_blueprints(app):
    app.register_blueprint(fund_bp, url_prefix='/api/fund')
    app.register_blueprint(crawler_bp, url_prefix='/api/crawler')
