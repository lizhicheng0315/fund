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