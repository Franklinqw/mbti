"""从 config.ini 读取配置；MBTI_CONFIG 可指定其他配置文件。"""
import configparser
import os
import secrets
from datetime import timedelta
from pathlib import Path
from sqlalchemy import URL

BASE_DIR = Path(__file__).resolve().parent


def get_config(env='default'):
    settings = configparser.ConfigParser(interpolation=None)
    settings.read(BASE_DIR / 'config.example.ini', encoding='utf-8-sig')
    settings.read(os.getenv('MBTI_CONFIG', str(BASE_DIR / 'config.ini')), encoding='utf-8-sig')
    secret = os.getenv('MBTI_SECRET_KEY') or settings.get('app', 'secret_key', fallback='')
    if not secret:
        folder = BASE_DIR / 'instance'
        folder.mkdir(exist_ok=True)
        path = folder / 'secret_key'
        try:
            with path.open('x', encoding='utf-8') as file:
                file.write(secrets.token_hex(32))
        except FileExistsError:
            pass
        secret = path.read_text(encoding='utf-8').strip()
    database_url = URL.create(
        'mysql+pymysql', username=settings.get('database', 'user'),
        password=os.getenv('MBTI_DB_PASSWORD', settings.get('database', 'password')),
        host=settings.get('database', 'host'), port=settings.getint('database', 'port'),
        database=settings.get('database', 'name'), query={'charset': 'utf8mb4'})
    return {
        'SECRET_KEY': secret, 'DEBUG': False, 'DATABASE_URL': database_url,
        'SESSION_COOKIE_HTTPONLY': True, 'SESSION_COOKIE_SAMESITE': 'Lax',
        'SESSION_COOKIE_SECURE': settings.getboolean('app', 'secure_cookie'),
        'PERMANENT_SESSION_LIFETIME': timedelta(hours=12),
        'MAX_CONTENT_LENGTH': 128 * 1024,
        'ADMIN_EMAIL': settings.get('mail', 'admin_email'),
        'PUBLIC_BASE_URL': settings.get('app', 'base_url').rstrip('/'),
        'MAIL_HOST': settings.get('mail', 'host'), 'MAIL_PORT': settings.getint('mail', 'port'),
        'MAIL_USERNAME': settings.get('mail', 'username'),
        'MAIL_PASSWORD': os.getenv('MBTI_MAIL_PASSWORD', settings.get('mail', 'password')),
        'MAIL_FROM': settings.get('mail', 'sender'),
        'MAIL_SECURITY': settings.get('mail', 'security'), 'MAIL_AUTH': settings.get('mail', 'auth'),
        'MAIL_OAUTH_TOKEN': os.getenv('MBTI_MAIL_OAUTH_TOKEN', settings.get('mail', 'oauth_token')),
        'MAIL_OAUTH_CLIENT_ID': settings.get('mail', 'oauth_client_id'),
        'MAIL_OAUTH_CLIENT_SECRET': os.getenv('MBTI_MAIL_CLIENT_SECRET', settings.get('mail', 'oauth_client_secret')),
        'MAIL_OAUTH_REFRESH_TOKEN': os.getenv('MBTI_MAIL_REFRESH_TOKEN', settings.get('mail', 'oauth_refresh_token')),
        'MAIL_OAUTH_TENANT': settings.get('mail', 'oauth_tenant'),
    }
