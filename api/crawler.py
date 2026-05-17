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
