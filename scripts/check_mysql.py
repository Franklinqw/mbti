"""MySQL 实际集成检查：测试数据全部放在事务中回滚，不发送真实邮件。"""
import secrets
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash
from app import create_app
from models.database import TestResult, User, get_db


def main():
    app = create_app(overrides={'TESTING': True, 'MAIL_HOST': ''})
    engine = app.extensions['db_engine']
    password = secrets.token_urlsafe(12)
    suffix = secrets.token_hex(5)
    username = 'check_' + suffix
    admin = 'check_admin_' + suffix
    with engine.connect() as connection:
        transaction = connection.begin()
        app.extensions['db_session_factory'] = sessionmaker(
            bind=connection, join_transaction_mode='create_savepoint', expire_on_commit=False)
        try:
            with app.app_context():
                db = get_db()
                db.add(User(username=admin, email=admin + '@example.com',
                            password_hash=generate_password_hash(password), role='admin', status='approved'))
                db.commit()
            client = app.test_client()

            def post(path, payload):
                token = client.get('/api/auth/session').json['data']['csrfToken']
                return client.post(path, json=payload, headers={'X-CSRF-Token': token})

            assert post('/api/auth/register', {'username': username, 'email': username + '@example.com', 'password': password}).status_code == 201
            assert post('/api/auth/login', {'identifier': username, 'password': password}).status_code == 403
            assert post('/api/auth/login', {'identifier': admin, 'password': password}).status_code == 200
            pending = client.get('/api/admin/users').json['data']['items']
            user_id = next(u['id'] for u in pending if u['username'] == username)
            assert post(f'/api/admin/users/{user_id}/review', {'decision': 'approved'}).status_code == 200
            assert post('/api/auth/login', {'identifier': username, 'password': password}).status_code == 200
            for mode, total in [('simple', 20), ('full', 60)]:
                attempt = post('/api/attempts', {'mode': mode}).json['data']['attemptId']
                payload = {'mode': mode, 'attemptId': attempt, 'answers': [
                    {'questionIndex': i, 'optionKey': 'A'} for i in range(1, total + 1)]}
                response = post('/api/result', payload)
                assert response.status_code == 200, response.json
                record_id = response.json['data']['recordId']
                assert post('/api/result', payload).json['data']['recordId'] == record_id
                detail = client.get(f'/api/me/results/{record_id}').json['data']
                assert len(detail['report']['dimensions']) == 4
            assert client.get('/api/me/results').json['data']['total'] == 2
            assert post('/api/me/password', {'oldPassword': password, 'newPassword': secrets.token_urlsafe(12)}).status_code == 200
            assert client.get('/api/me/results').status_code == 401
            assert post('/api/auth/login', {'identifier': admin, 'password': password}).status_code == 200
            assert post('/api/admin/users/state', {'userIds':[user_id], 'accountState':'closed'}).status_code == 200
            assert post('/api/admin/users/reset-password', {'userIds':[user_id], 'newPassword':'Reset-check-123!'}).status_code == 200
            other = app.test_client()
            token = other.get('/api/auth/session').json['data']['csrfToken']
            assert other.post('/api/auth/login',json={'identifier':username,'password':'Reset-check-123!'},headers={'X-CSRF-Token':token}).status_code == 403
            assert post('/api/admin/users/state', {'userIds':[user_id], 'accountState':'active'}).status_code == 200
            assert other.post('/api/auth/login',json={'identifier':username,'password':'Reset-check-123!'},headers={'X-CSRF-Token':token}).status_code == 200
            assert other.get('/api/me/results').json['data']['total'] == 2
            print('PASS: MySQL state migration, close/reactivate, administrator password reset, preserved history')
            print('PASS: MySQL registration, review, login, both test modes, JSON reports, history, idempotency, password changes')
        finally:
            transaction.rollback()
    with engine.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(User).where(User.username.in_([username, admin]))) == 0
    engine.dispose()
    print('PASS: all temporary MySQL accounts and test data rolled back; no real email sent')


if __name__ == '__main__':
    main()
