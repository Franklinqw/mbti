"""注册通知持久化入队；失败不丢失注册记录，管理员可重试。"""
import base64
import smtplib
import ssl
from email.message import EmailMessage
from flask import current_app
from sqlalchemy import select
from models.database import MailNotification, User, get_db, iso_time, utcnow
from services.oauth_service import outlook_access_token


def send_registration_notice(notification_id):
    db = get_db()
    notice = db.scalar(select(MailNotification).where(
        MailNotification.id == notification_id).with_for_update().execution_options(populate_existing=True))
    if not notice or notice.status == 'sent':
        db.rollback()
        return 'sent' if notice else 'missing'
    config = current_app.config
    notice.attempts += 1
    if not config['MAIL_HOST'] or not config['MAIL_FROM'] or not config['MAIL_USERNAME']:
        notice.status = 'failed'
        notice.last_error = '尚未配置 SMTP 发件服务、发件人和账号'
        db.commit()
        return 'failed'
    try:
        token = None
        if config['MAIL_AUTH'] == 'oauth2':
            token = outlook_access_token()
            if not token:
                raise ValueError('缺少 OAuth2 访问令牌或续期凭据')
        elif config['MAIL_AUTH'] == 'password':
            if not config['MAIL_PASSWORD']:
                raise ValueError('缺少 SMTP 授权码')
        else:
            raise ValueError('不支持的 SMTP 认证方式')
        user = db.get(User, notice.user_id)
        message = EmailMessage()
        message['Subject'] = f'本色 MBTI：新账号待审核（#{user.id}）'
        message['From'] = config['MAIL_FROM']
        message['To'] = notice.recipient
        message.set_content(
            f'收到新的注册申请，请登录管理员界面审核。\n\n'
            f'账号：{user.username}\n邮箱：{user.email}\n'
            f'注册时间（UTC）：{iso_time(user.created_at)}\n\n'
            f'管理员界面：{config["PUBLIC_BASE_URL"]}/#admin\n'
            '邮件不包含用户密码；审批操作必须由已登录的管理员完成。')
        context = ssl.create_default_context()
        if config['MAIL_SECURITY'] == 'ssl':
            smtp = smtplib.SMTP_SSL(config['MAIL_HOST'], config['MAIL_PORT'], timeout=10, context=context)
        elif config['MAIL_SECURITY'] == 'starttls':
            smtp = smtplib.SMTP(config['MAIL_HOST'], config['MAIL_PORT'], timeout=10)
        else:
            raise ValueError('SMTP 必须使用 ssl 或 starttls')
        with smtp:
            smtp.ehlo()
            if config['MAIL_SECURITY'] == 'starttls':
                smtp.starttls(context=context)
                smtp.ehlo()
            if config['MAIL_AUTH'] == 'oauth2':
                auth = f'user={config["MAIL_USERNAME"]}\x01auth=Bearer {token}\x01\x01'
                code, _ = smtp.docmd('AUTH', 'XOAUTH2 ' + base64.b64encode(auth.encode()).decode())
                if code != 235:
                    raise smtplib.SMTPAuthenticationError(code, b'OAuth2 authentication failed')
            elif config['MAIL_AUTH'] == 'password':
                smtp.login(config['MAIL_USERNAME'], config['MAIL_PASSWORD'])
            smtp.send_message(message)
        notice.status, notice.last_error, notice.sent_at = 'sent', None, utcnow()
    except (OSError, smtplib.SMTPException, ValueError) as exc:
        notice.status = 'failed'
        # 不存放可能包含认证凭据的服务商原始响应。
        notice.last_error = f'发送失败（{type(exc).__name__}），请检查邮件配置后重试'
    db.commit()
    return notice.status
