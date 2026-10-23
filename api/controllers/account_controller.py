"""注册、登录、个人中心及管理员审核接口。"""
import re
import secrets
from datetime import timedelta
from flask import Blueprint, jsonify, request, session
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash
from models.database import MailNotification, TestResult, User, get_db, iso_time, utcnow
from services.auth_service import admin_required, superadmin_required, csrf_token, current_user, login_required
from services.mail_service import send_registration_notice
from utils.response import error, success

account_bp = Blueprint('account', __name__, url_prefix='/api')
# 对不存在的账号也执行一次密码哈希比较，避免明显的时间差。
DUMMY_HASH = generate_password_hash('dummy-not-a-real-password')


def body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def text(data, key):
    value = data.get(key, '')
    return value if isinstance(value, str) else ''


def fail(message, status=400):
    return jsonify(error(message)), status


def valid_password(password):
    return 8 <= len(password) <= 20


@account_bp.get('/auth/session')
def get_session():
    user = current_user()
    return jsonify(success({'user': user.public() if user else None, 'csrfToken': csrf_token()}))


@account_bp.post('/auth/register')
def register():
    from flask import current_app
    data = body()
    username = text(data, 'username').strip().lower()
    email = text(data, 'email').strip().lower()
    password = text(data, 'password')
    if not re.fullmatch(r'[a-z0-9_\u4e00-\u9fff]{3,32}', username):
        return fail('用户名需为 3–32 位中文、字母、数字或下划线')
    if len(email) > 254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
        return fail('请输入有效的邮箱地址')
    if not valid_password(password):
        return fail('密码长度需为 8–20 位')
    db = get_db()
    user = User(username=username, email=email, password_hash=generate_password_hash(password))
    try:
        db.add(user)
        db.flush()
        notice = MailNotification(user_id=user.id, recipient=current_app.config['ADMIN_EMAIL'])
        db.add(notice)
        db.commit()
    except IntegrityError:
        db.rollback()
        return fail('用户名或邮箱已被注册', 409)
    state = send_registration_notice(notice.id)
    message = '注册成功，审核通知已发送，请等待管理员审核。' if state == 'sent' else '注册申请已保存，等待管理员审核。邮件通知暂未发送，管理员可在审核界面查看并重试。'
    return jsonify(success({'status': 'pending', 'notificationStatus': state}, message)), 201


@account_bp.post('/auth/login')
def login():
    data = body()
    identifier = text(data, 'identifier').strip().lower()
    password = text(data, 'password')
    # 允许旧账号使用此前已设置的长密码登录，再将新密码修改为 8–20 位。
    if not identifier or len(identifier) > 254 or not 8 <= len(password) <= 128:
        return fail('账号或密码错误', 401)
    db = get_db()
    user = db.scalar(select(User).where(or_(User.username == identifier, User.email == identifier)).with_for_update())
    if user and user.locked_until and user.locked_until > utcnow():
        db.rollback()
        return fail('尝试次数过多，请 15 分钟后重试', 429)
    matched = check_password_hash(user.password_hash if user else DUMMY_HASH, password)
    if not user or not matched:
        if user:
            user.failed_logins = (user.failed_logins or 0) + 1
            if user.failed_logins >= 5:
                user.locked_until = utcnow() + timedelta(minutes=15)
                user.failed_logins = 0
            db.commit()
        return fail('账号或密码错误', 401)
    user.failed_logins, user.locked_until = 0, None
    db.commit()
    if user.status != 'approved':
        return fail('账号正在等待管理员审核' if user.status == 'pending' else '注册申请未通过审核：' + (user.review_note or '请联系管理员'), 403)
    if user.account_state != 'active':
        return fail('账号已封闭，请联系管理员', 403)
    session.clear()
    session.permanent = True
    session.update(user_id=user.id, version=user.session_version)
    return jsonify(success({'user': user.public(), 'csrfToken': csrf_token()}, '登录成功'))


@account_bp.post('/auth/logout')
def logout():
    session.clear()
    return jsonify(success({'csrfToken': csrf_token()}, '已退出登录'))


@account_bp.post('/me/password')
@login_required
def change_password():
    data = body()
    old, new = text(data, 'oldPassword'), text(data, 'newPassword')
    db = get_db()
    user = db.scalar(select(User).where(User.id == current_user().id).with_for_update())
    if len(old) > 128 or not check_password_hash(user.password_hash, old):
        return fail('当前密码不正确')
    if not valid_password(new):
        return fail('新密码长度需为 8–20 位')
    if old == new:
        return fail('新密码应与原密码不同')
    user.password_hash = generate_password_hash(new)
    user.session_version += 1
    user.failed_logins, user.locked_until = 0, None
    db.commit()
    session.clear()
    return jsonify(success({'csrfToken': csrf_token()}, '密码已修改，请重新登录；其他设备的登录也已失效。'))


def page_number():
    return max(1, min(request.args.get('page', 1, type=int) or 1, 100000))


@account_bp.get('/me/results')
@login_required
def results():
    db, page = get_db(), page_number()
    query = select(TestResult).where(TestResult.user_id == current_user().id)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    records = db.scalars(query.order_by(TestResult.completed_at.desc(), TestResult.id.desc()).offset((page - 1) * 10).limit(10)).all()
    return jsonify(success({'items': [r.summary() for r in records], 'total': total, 'page': page, 'pageSize': 10}))


@account_bp.get('/me/results/<int:result_id>')
@login_required
def result_detail(result_id):
    record = get_db().scalar(select(TestResult).where(TestResult.id == result_id, TestResult.user_id == current_user().id))
    if not record:
        return fail('未找到该测试记录', 404)
    return jsonify(success(record.detail()))


@account_bp.get('/admin/users')
@admin_required
def admin_users():
    status = request.args.get('status', 'pending')
    if status not in ('all', 'pending', 'approved', 'rejected'):
        return fail('无效的审核状态')
    db, page = get_db(), page_number()
    query = select(User)
    if status != 'all':
        query = query.where(User.status == status)
    account_state = request.args.get('accountState', 'all')
    if account_state not in ('all', 'active', 'closed'):
        return fail('无效的账号状态')
    if account_state != 'all':
        query = query.where(User.account_state == account_state)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    users = db.scalars(query.order_by(User.created_at.desc(), User.id.desc()).offset((page - 1) * 10).limit(10)).all()
    items = []
    for user in users:
        notice = db.scalar(select(MailNotification).where(MailNotification.user_id == user.id))
        items.append({**user.public(), 'canManage': can_manage_user(current_user(), user),
                      'notification': None if not notice else {
            'id': notice.id, 'status': notice.status, 'attempts': notice.attempts,
            'lastError': notice.last_error, 'sentAt': iso_time(notice.sent_at)}})
    return jsonify(success({'items': items, 'total': total, 'page': page, 'pageSize': 10}))


def can_manage_user(actor, target):
    if actor.id == target.id or target.role == 'superadmin':
        return False
    return target.role == 'user' or (actor.role == 'superadmin' and target.role == 'admin')


def managed_users(data):
    """整个批次先校验再修改，避免只更新一部分用户。"""
    ids = data.get('userIds')
    if (not isinstance(ids, list) or not 1 <= len(ids) <= 100
            or any(type(i) is not int or i <= 0 for i in ids)
            or len(set(ids)) != len(ids)):
        return None, fail('请选择 1–100 个不重复的用户')
    users = get_db().scalars(select(User).where(User.id.in_(ids)).order_by(User.id).with_for_update()).all()
    if len(users) != len(ids):
        return None, fail('部分用户不存在，请刷新列表后重试', 404)
    if any(not can_manage_user(current_user(), user) for user in users):
        return None, fail('不能修改自己、超级管理员或无权管理的管理员账号', 403)
    return users, None


@account_bp.post('/admin/users/state')
@admin_required
def set_account_state():
    data = body()
    state = data.get('accountState')
    if state not in ('active', 'closed'):
        return fail('账号状态必须为激活或封闭')
    users, failure = managed_users(data)
    if failure:
        return failure
    for user in users:
        if user.account_state != state:
            user.account_state = state
            user.session_version += 1
    get_db().commit()
    return jsonify(success({'updated': len(users)}, f'已将 {len(users)} 个账号设为' + ('激活' if state == 'active' else '封闭')))


@account_bp.post('/admin/users/reset-password')
@admin_required
def reset_user_password():
    data = body()
    # 单用户可指定新密码；批量操作为每人生成独立密码。
    password = text(data, 'newPassword')
    generated = data.get('generate') is True
    if not generated and not valid_password(password):
        return fail('新密码长度需为 8–20 位')
    users, failure = managed_users(data)
    if failure:
        return failure
    if not generated and len(users) != 1:
        return fail('批量重置时必须为每个用户生成独立密码')
    credentials = []
    for user in users:
        new_password = secrets.token_urlsafe(9) if generated else password
        user.password_hash = generate_password_hash(new_password)
        user.session_version += 1
        user.failed_logins, user.locked_until = 0, None
        if generated:
            credentials.append({'username': user.username, 'password': new_password})
    get_db().commit()
    return jsonify(success({'updated': len(users), 'credentials': credentials},
                           f'已重置 {len(users)} 个账号密码，原登录会话已失效'))


@account_bp.post('/admin/users/<int:user_id>/review')
@admin_required
def review(user_id):
    data = body()
    decision = text(data, 'decision')
    note = text(data, 'note').strip()
    if decision not in ('approved', 'rejected') or len(note) > 500:
        return fail('审核决定无效，备注不得超过 500 字')
    if decision == 'rejected' and not note:
        return fail('请填写拒绝原因')
    db = get_db()
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if not user:
        return fail('账号不存在', 404)
    if user.status != 'pending' or user.role != 'user':
        return fail('只能审核待审核的普通账号', 409)
    user.status, user.review_note = decision, note
    user.reviewed_at, user.reviewed_by = utcnow(), current_user().id
    db.commit()
    return jsonify(success(user.public(), '审核已保存'))


@account_bp.post('/admin/users/<int:user_id>/role')
@superadmin_required
def change_admin_role(user_id):
    role = text(body(), 'role')
    if role not in ('user', 'admin'):
        return fail('只能设置普通用户或管理员角色')
    db = get_db()
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if not user:
        return fail('账号不存在', 404)
    if user.role == 'superadmin' or user.id == current_user().id or user.status != 'approved':
        return fail('只能调整已通过审核的普通用户或管理员权限', 409)
    if user.role != role:
        user.role = role
        user.session_version += 1
        db.commit()
    return jsonify(success(user.public(), '权限已更新，该用户需重新登录'))


@account_bp.post('/admin/notifications/<int:notice_id>/retry')
@admin_required
def retry_notice(notice_id):
    notice = get_db().get(MailNotification, notice_id)
    if not notice:
        return fail('通知不存在', 404)
    state = send_registration_notice(notice_id)
    return jsonify(success({'status': state}, '通知已发送' if state == 'sent' else '发送失败，请检查 SMTP 配置'))
