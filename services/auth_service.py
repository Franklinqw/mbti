"""Cookie 会话、CSRF 校验和账号权限。"""
import secrets
from functools import wraps
from flask import g, jsonify, request, session
from models.database import User, get_db
from utils.response import error


def csrf_token():
    if 'csrf' not in session:
        session['csrf'] = secrets.token_urlsafe(32)
    return session['csrf']


def current_user():
    if 'current_user' not in g:
        user = get_db().get(User, session['user_id']) if 'user_id' in session else None
        if user and (user.status != 'approved' or user.account_state != 'active' or user.session_version != session.get('version')):
            session.clear()
            user = None
        g.current_user = user
    return g.current_user


def login_required(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        if not current_user():
            return jsonify(error('请先登录已通过审核的账号')), 401
        return function(*args, **kwargs)
    return wrapped


def admin_required(function):
    @wraps(function)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user().role not in ('admin', 'superadmin'):
            return jsonify(error('需要管理员权限')), 403
        return function(*args, **kwargs)
    return wrapped


def superadmin_required(function):
    @wraps(function)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user().role != 'superadmin':
            return jsonify(error('需要超级管理员权限')), 403
        return function(*args, **kwargs)
    return wrapped


def install_security(app):
    @app.before_request
    def protect_api():
        if request.path.startswith('/api/') and request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            supplied = request.headers.get('X-CSRF-Token', '')
            expected = session.get('csrf', '')
            if not supplied or not expected or not secrets.compare_digest(supplied, expected):
                return jsonify(error('页面验证已失效，请刷新后重试')), 403

    @app.after_request
    def response_headers(response):
        if request.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Referrer-Policy'] = 'same-origin'
        return response
