from flask import Flask
from config import Config
from models import db
from extensions import cache


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
