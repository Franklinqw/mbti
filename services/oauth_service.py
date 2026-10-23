"""可选的 Outlook OAuth2 令牌续期，缓存仅写入被 Git 忽略的 instance 目录。"""
import json
import os
import re
import secrets
import time
from pathlib import Path
from threading import Lock
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from flask import current_app

_lock = Lock()


def outlook_access_token():
    config = current_app.config
    client_id = config['MAIL_OAUTH_CLIENT_ID']
    if not client_id:
        return config['MAIL_OAUTH_TOKEN']
    tenant = config['MAIL_OAUTH_TENANT']
    if not re.fullmatch(r'[a-zA-Z0-9.-]{1,100}', tenant):
        raise ValueError('OAuth 租户无效')
    folder = Path(current_app.instance_path)
    folder.mkdir(exist_ok=True)
    path = folder / 'outlook_tokens.json'
    with _lock:
        try:
            cache = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            cache = {}
        identity = [client_id, config['MAIL_USERNAME'], tenant]
        if not isinstance(cache, dict) or cache.get('identity') != identity:
            cache = {}
        if cache.get('expires_at', 0) > time.time() + 120:
            return cache['access_token']
        refresh = cache.get('refresh_token') or config['MAIL_OAUTH_REFRESH_TOKEN']
        if not refresh:
            if config['MAIL_OAUTH_TOKEN']:
                return config['MAIL_OAUTH_TOKEN']
            raise ValueError('缺少 OAuth2 refresh_token')
        payload = {'client_id': client_id, 'grant_type': 'refresh_token',
                   'refresh_token': refresh,
                   'scope': 'https://outlook.office.com/SMTP.Send offline_access'}
        if config['MAIL_OAUTH_CLIENT_SECRET']:
            payload['client_secret'] = config['MAIL_OAUTH_CLIENT_SECRET']
        request = Request(f'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token',
                          data=urlencode(payload).encode(),
                          headers={'Content-Type': 'application/x-www-form-urlencoded'})
        with urlopen(request, timeout=10) as response:
            tokens = json.load(response)
        token = tokens.get('access_token')
        if not isinstance(token, str) or not token:
            raise ValueError('OAuth2 响应缺少访问令牌')
        cache = {'identity': identity, 'access_token': token,
                 'refresh_token': tokens.get('refresh_token', refresh),
                 'expires_at': time.time() + int(tokens.get('expires_in', 3600))}
        # 同目录临时文件 + 原子替换，避免进程中断写坏缓存。
        temporary = folder / f'outlook_tokens.{secrets.token_hex(12)}.tmp'
        try:
            with temporary.open('x', encoding='utf-8') as file:
                json.dump(cache, file)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return token
