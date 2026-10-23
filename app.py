"""Flask 应用入口和数据库管理命令。"""
import os
import re
import click
from flask import Flask, jsonify, render_template
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import generate_password_hash
from config import get_config
from models.database import Base, User, get_db, init_database
from services.auth_service import install_security
from api.controllers.mbti_controller import mbti_bp
from api.controllers.account_controller import account_bp
from utils.response import error


def create_app(env='default', overrides=None):
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config.update(get_config(env))
    if overrides:
        app.config.update(overrides)
    init_database(app)
    install_security(app)
    app.register_blueprint(mbti_bp)
    app.register_blueprint(account_bp)

    @app.get('/')
    def index():
        return render_template('index.html')

    @app.errorhandler(SQLAlchemyError)
    def database_error(exception):
        app.logger.error('Database request failed: %s', type(exception).__name__)
        return jsonify(error('数据库暂时不可用，请检查配置或稍后重试')), 503

    @app.errorhandler(413)
    def too_large(exception):
        return jsonify(error('提交内容过大')), 413

    @app.cli.command('init-db')
    def init_db_command():
        """创建配置的数据库及缺失的表，不删除已有数据。"""
        url = make_url(app.config['DATABASE_URL'])
        if url.get_backend_name() == 'mysql':
            name = url.database
            if not name or not re.fullmatch(r'[a-zA-Z0-9_]{1,64}', name):
                raise click.ClickException('数据库名只能包含英文字母、数字或下划线')
            server = create_engine(url.set(database=''), connect_args={'connect_timeout': 5})
            try:
                with server.begin() as connection:
                    connection.execute(text(f'CREATE DATABASE IF NOT EXISTS `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci'))
            finally:
                server.dispose()
        Base.metadata.create_all(app.extensions['db_engine'])
        click.echo('数据库和数据表初始化完成（未删除已有数据）。')

    @app.cli.command('create-admin')
    @click.option('--username', prompt='管理员用户名')
    @click.option('--email', prompt='管理员邮箱')
    @click.option('--superadmin', is_flag=True, help='创建超级管理员')
    @click.password_option(confirmation_prompt=True)
    def create_admin_command(username, email, password, superadmin=False):
        """由部署者在终端创建管理员，无默认管理员密码。"""
        username, email = username.strip().lower(), email.strip().lower()
        if not re.fullmatch(r'[a-z0-9_\u4e00-\u9fff]{3,32}', username):
            raise click.ClickException('用户名需为 3–32 位中文、字母、数字或下划线')
        if len(email) > 254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
            raise click.ClickException('请输入有效邮箱')
        if not 8 <= len(password) <= 20:
            raise click.ClickException('密码长度应为 8–20 位')
        db = get_db()
        if db.scalar(select(User).where((User.username == username) | (User.email == email))):
            raise click.ClickException('用户名或邮箱已存在，请使用其他管理员账号')
        db.add(User(username=username, email=email, password_hash=generate_password_hash(password), role='superadmin' if superadmin else 'admin', status='approved'))
        db.commit()
        click.echo('管理员已创建，可在页面登录后进入“管理员审核”。')

    @app.cli.command('create-superadmin')
    @click.option('--username', prompt='超级管理员用户名')
    @click.option('--email', prompt='超级管理员邮箱')
    @click.password_option(confirmation_prompt=True)
    def create_superadmin_command(username, email, password):
        """创建无需审核的超级管理员，可管理普通管理员权限。"""
        click.get_current_context().invoke(create_admin_command, username=username,
                                           email=email, password=password, superadmin=True)

    @app.cli.command('retry-mail')
    def retry_mail_command():
        """重试未发送的注册审核通知。"""
        from models.database import MailNotification
        from services.mail_service import send_registration_notice
        ids = list(get_db().scalars(select(MailNotification.id).where(MailNotification.status != 'sent')))
        for notice_id in ids:
            click.echo(f'通知 #{notice_id}: {send_registration_notice(notice_id)}')
        click.echo(f'已处理 {len(ids)} 条通知。')

    @app.cli.command('migrate-db')
    def migrate_db_command():
        """为既有 users 表增加激活/封闭状态，不删除用户或测试结果。"""
        engine = app.extensions['db_engine']
        if 'users' not in inspect(engine).get_table_names():
            raise click.ClickException('请先运行 init-db')
        columns = {c['name'] for c in inspect(engine).get_columns('users')}
        if 'account_state' not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE users ADD COLUMN account_state VARCHAR(16) NOT NULL DEFAULT 'active'"))
        click.echo('账号状态迁移已完成，已有账号默认激活，原有数据保留。')

    return app


app = create_app(os.getenv('FLASK_ENV', 'default'))

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
