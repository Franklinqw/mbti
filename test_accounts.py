"""使用隔离数据库验证账号权限、通知、历史和改密，不发送真实邮件。"""
import unittest
import io
import json
import tempfile
from unittest.mock import patch
from sqlalchemy import func, select
from werkzeug.security import check_password_hash, generate_password_hash
from app import create_app
from models.database import Base, MailNotification, TestResult, User, get_db


class AccountTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(overrides={'TESTING': True, 'DATABASE_URL': 'sqlite://',
                                        'SECRET_KEY': 'testing-only-key', 'MAIL_HOST': ''})
        Base.metadata.create_all(self.app.extensions['db_engine'])
        with self.app.app_context():
            db = get_db()
            for username, role, status in [('admin', 'admin', 'approved'), ('alice', 'user', 'approved'), ('bob', 'user', 'pending')]:
                db.add(User(username=username, email=username + '@example.com',
                            password_hash=generate_password_hash('test-password'), role=role, status=status))
            db.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        self.app.extensions['db_engine'].dispose()

    def post(self, path, data, client=None):
        client = client or self.client
        token = client.get('/api/auth/session').json['data']['csrfToken']
        return client.post(path, json=data, headers={'X-CSRF-Token': token})

    def login(self, name='admin', client=None, password='test-password'):
        return self.post('/api/auth/login', {'identifier': name, 'password': password}, client)

    def test_register_review_login(self):
        response = self.post('/api/auth/register', {'username': 'newuser', 'email': 'new@example.com', 'password': 'new-password'})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json['data']['notificationStatus'], 'failed')
        self.assertEqual(self.login('newuser', password='new-password').status_code, 403)
        with self.app.app_context():
            user = get_db().scalar(select(User).where(User.username == 'newuser'))
            user_id = user.id
            self.assertNotIn('new-password', user.password_hash)
            self.assertTrue(check_password_hash(user.password_hash, 'new-password'))
            self.assertEqual(get_db().scalar(select(MailNotification)).recipient, 'qiwen421@outlook.com')
        self.login()
        listed = self.client.get('/api/admin/users').json['data']['items']
        self.assertIn(user_id, [u['id'] for u in listed])
        self.assertEqual(self.post(f'/api/admin/users/{user_id}/review', {'decision': 'approved'}).status_code, 200)
        self.assertEqual(self.post(f'/api/admin/users/{user_id}/review', {'decision': 'rejected', 'note': 'duplicate'}).status_code, 409)
        self.assertEqual(self.login('newuser', password='new-password').status_code, 200)

    def test_csrf_roles_and_rejection(self):
        self.assertEqual(self.client.post('/api/auth/register', json={}).status_code, 403)
        self.assertEqual(self.client.get('/api/me/results').status_code, 401)
        self.login('alice')
        self.assertEqual(self.client.get('/api/admin/users').status_code, 403)
        self.assertEqual(self.post('/api/admin/users/3/review', {'decision': 'approved'}).status_code, 403)
        self.login()
        self.assertEqual(self.post('/api/admin/users/3/review', {'decision': 'rejected'}).status_code, 400)
        self.assertEqual(self.post('/api/admin/users/3/review', {'decision': 'rejected', 'note': '资料需确认'}).status_code, 200)
        self.assertEqual(self.login('bob').status_code, 403)

    def test_history_isolation_and_idempotent_submission(self):
        self.login('alice')
        ids = []
        for mode, count in [('simple', 20), ('full', 60)]:
            attempt = self.post('/api/attempts', {'mode': mode}).json['data']['attemptId']
            payload = {'mode': mode, 'attemptId': attempt,
                       'answers': [{'questionIndex': i, 'optionKey': 'A'} for i in range(1, count + 1)]}
            response = self.post('/api/result', payload)
            self.assertEqual(response.status_code, 200)
            data = response.json['data']
            ids.append(data['recordId'])
            self.assertTrue(data['completedAt'].endswith('+00:00'))
            duplicate = self.post('/api/result', payload)
            self.assertEqual(duplicate.json['data']['recordId'], data['recordId'])
        history = self.client.get('/api/me/results').json['data']
        self.assertEqual(history['total'], 2)
        self.assertEqual(history['items'][0]['id'], ids[-1])
        self.assertEqual(self.client.get(f'/api/me/results/{ids[0]}').status_code, 200)
        self.login()
        self.assertEqual(self.client.get(f'/api/me/results/{ids[0]}').status_code, 404)
        self.assertEqual(self.client.get(f'/api/attempts/{attempt}').status_code, 404)
        self.assertEqual(self.post('/api/result', payload).status_code, 400)

    def test_change_password_revokes_all_sessions(self):
        other = self.app.test_client()
        self.login('alice')
        self.login('alice', client=other)
        self.assertEqual(self.post('/api/me/password', {'oldPassword': 'wrong', 'newPassword': 'changed-password'}).status_code, 400)
        response = self.post('/api/me/password', {'oldPassword': 'test-password', 'newPassword': 'changed-password'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/api/me/results').status_code, 401)
        self.assertEqual(other.get('/api/me/results').status_code, 401)
        self.assertEqual(self.login('alice').status_code, 401)
        self.assertEqual(self.login('alice', password='changed-password').status_code, 200)
        self.assertEqual(self.client.get('/api/me/results').status_code, 200)

    def test_email_content_and_retry(self):
        self.app.config.update(MAIL_HOST='smtp.example.com', MAIL_FROM='sender@example.com',
                               MAIL_USERNAME='sender@example.com', MAIL_PASSWORD='test-only-secret', MAIL_AUTH='password')
        with patch('services.mail_service.smtplib.SMTP') as smtp:
            smtp.return_value.__enter__.return_value = smtp.return_value
            response = self.post('/api/auth/register', {'username': 'mailuser', 'email': 'mailuser@example.com', 'password': 'mail-password'})
            self.assertEqual(response.json['data']['notificationStatus'], 'sent')
            message = smtp.return_value.send_message.call_args.args[0]
            self.assertEqual(message['To'], 'qiwen421@outlook.com')
            self.assertIn('/#admin', message.get_content())
            self.assertNotIn('mail-password', message.get_content())
            self.assertNotIn('test-only-secret', message.get_content())
            self.login()
            notice_id = self.client.get('/api/admin/users').json['data']['items'][0]['notification']['id']
            self.post(f'/api/admin/notifications/{notice_id}/retry', {})
            self.assertEqual(smtp.return_value.send_message.call_count, 1)

    def test_duplicate_registration_and_session_storage(self):
        data = {'username': 'alice', 'email': 'another@example.com', 'password': 'test-password'}
        self.assertEqual(self.post('/api/auth/register', data).status_code, 409)
        self.login('alice')
        with self.client.session_transaction() as cookie:
            self.assertNotIn('password', cookie)
            self.assertNotIn('password_hash', cookie)
        for _ in range(5):
            self.assertEqual(self.login('alice', password='wrong-password').status_code, 401)
        self.assertEqual(self.login('alice').status_code, 429)

    def test_outlook_oauth2_and_failed_notification_retry(self):
        response = self.post('/api/auth/register', {'username': 'outlookuser', 'email': 'oauth@example.com', 'password': 'oauth-password'})
        self.assertEqual(response.json['data']['notificationStatus'], 'failed')
        self.login()
        notice_id = self.client.get('/api/admin/users').json['data']['items'][0]['notification']['id']
        self.app.config.update(MAIL_HOST='smtp-mail.outlook.com', MAIL_FROM='sender@outlook.com',
                               MAIL_USERNAME='sender@outlook.com', MAIL_AUTH='oauth2',
                               MAIL_OAUTH_TOKEN='test-access-token', MAIL_OAUTH_CLIENT_ID='')
        with patch('services.mail_service.smtplib.SMTP') as smtp:
            smtp.return_value.__enter__.return_value = smtp.return_value
            smtp.return_value.docmd.return_value = (235, b'Authenticated')
            response = self.post(f'/api/admin/notifications/{notice_id}/retry', {})
            self.assertEqual(response.json['data']['status'], 'sent')
            smtp.return_value.starttls.assert_called_once()
            smtp.return_value.login.assert_not_called()
            self.assertEqual(smtp.return_value.docmd.call_args.args[0], 'AUTH')
            self.assertTrue(smtp.return_value.docmd.call_args.args[1].startswith('XOAUTH2 '))

    def test_outlook_token_refresh_and_cache(self):
        from services.oauth_service import outlook_access_token
        self.app.config.update(MAIL_OAUTH_CLIENT_ID='example-client', MAIL_OAUTH_TENANT='consumers',
                               MAIL_OAUTH_REFRESH_TOKEN='initial-refresh', MAIL_OAUTH_TOKEN='',
                               MAIL_OAUTH_CLIENT_SECRET='')
        with tempfile.TemporaryDirectory(dir=self.app.instance_path) as folder:
            self.app.instance_path = folder
            with self.app.app_context(), patch('services.oauth_service.urlopen') as request:
                request.return_value.__enter__.return_value = io.StringIO(json.dumps({
                    'access_token': 'new-access-token', 'refresh_token': 'rotated-refresh', 'expires_in': 3600}))
                self.assertEqual(outlook_access_token(), 'new-access-token')
                self.assertEqual(outlook_access_token(), 'new-access-token')
                self.assertEqual(request.call_count, 1)
                self.assertIn('login.microsoftonline.com/consumers/', request.call_args.args[0].full_url)
                from pathlib import Path
                cache = json.loads((Path(folder) / 'outlook_tokens.json').read_text())
                self.assertEqual(cache['refresh_token'], 'rotated-refresh')

    def test_superadmin_creation_and_admin_management(self):
        result = self.app.test_cli_runner().invoke(args=[
            'create-superadmin', '--username', 'superadmin', '--email', 'super@example.com'],
            input='super-test-password\nsuper-test-password\n')
        self.assertEqual(result.exit_code, 0, result.output)
        self.login('admin')
        self.assertEqual(self.post('/api/admin/users/2/role', {'role': 'admin'}).status_code, 403)
        self.assertEqual(self.login('superadmin', password='super-test-password').status_code, 200)
        self.assertEqual(self.client.get('/api/admin/users').status_code, 200)
        self.assertEqual(self.post('/api/admin/users/3/role', {'role': 'admin'}).status_code, 409)
        self.assertEqual(self.post('/api/admin/users/2/role', {'role': 'superadmin'}).status_code, 400)
        alice_client = self.app.test_client()
        self.login('alice', client=alice_client)
        self.assertEqual(self.post('/api/admin/users/2/role', {'role': 'admin'}).status_code, 200)
        self.assertEqual(alice_client.get('/api/me/results').status_code, 401)
        self.login('alice', client=alice_client)
        self.assertEqual(alice_client.get('/api/admin/users').status_code, 200)
        self.assertEqual(self.post('/api/admin/users/2/role', {'role': 'user'}).status_code, 200)
        self.login('alice', client=alice_client)
        self.assertEqual(alice_client.get('/api/admin/users').status_code, 403)
        with self.app.app_context():
            super_user = get_db().scalar(select(User).where(User.username == 'superadmin'))
            super_id = super_user.id
        self.assertEqual(self.post(f'/api/admin/users/{super_id}/role', {'role': 'user'}).status_code, 409)

    def test_password_length_boundaries(self):
        for length in (7, 21):
            response = self.post('/api/auth/register', {'username':'boundary', 'email':'boundary@example.com','password':'x'*length})
            self.assertEqual(response.status_code, 400)
        for length in (8, 20):
            response = self.post('/api/auth/register', {'username':f'boundary{length}', 'email':f'b{length}@example.com','password':'x'*length})
            self.assertEqual(response.status_code, 201)
        self.login('alice')
        self.assertEqual(self.post('/api/me/password', {'oldPassword':'test-password','newPassword':'x'*21}).status_code,400)
        self.login('admin')
        self.assertEqual(self.post('/api/admin/users/reset-password', {'userIds':[2],'newPassword':'x'*21}).status_code,400)

    def test_bulk_states_and_session_invalidation(self):
        alice = self.app.test_client()
        self.login('alice',client=alice)
        self.login('admin')
        response = self.post('/api/admin/users/state', {'userIds':[2,3],'accountState':'closed'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(alice.get('/api/me/results').status_code,401)
        self.assertEqual(self.login('alice',client=alice).status_code,403)
        listed = self.client.get('/api/admin/users?status=all&accountState=closed').json['data']
        self.assertEqual(listed['total'],2)
        self.assertEqual(self.post('/api/admin/users/state', {'userIds':[2,3],'accountState':'active'}).status_code,200)
        self.assertEqual(self.login('alice',client=alice).status_code,200)
        self.assertEqual(self.login('bob',client=alice).status_code,403)

    def test_password_reset_preserves_history_and_clears_lock(self):
        alice = self.app.test_client()
        self.login('alice',client=alice)
        attempt = self.post('/api/attempts', {'mode':'simple'},client=alice).json['data']['attemptId']
        payload={'mode':'simple','attemptId':attempt,'answers':[{'questionIndex':i,'optionKey':'A'} for i in range(1,21)]}
        self.assertEqual(self.post('/api/result',payload,client=alice).status_code,200)
        for _ in range(5): self.login('alice',client=alice,password='wrong-password')
        self.login('admin')
        reset=self.post('/api/admin/users/reset-password',{'userIds':[2],'newPassword':'reset-password'})
        self.assertEqual(reset.status_code,200)
        self.assertEqual(alice.get('/api/me/results').status_code,401)
        self.assertEqual(self.login('alice',client=alice).status_code,401)
        self.assertEqual(self.login('alice',client=alice,password='reset-password').status_code,200)
        self.assertEqual(alice.get('/api/me/results').json['data']['total'],1)

    def test_batch_passwords_and_atomic_permission_checks(self):
        self.login('admin')
        for ids in ([2,2],[True],[2,999999],[1,2]):
            self.assertIn(self.post('/api/admin/users/state',{'userIds':ids,'accountState':'closed'}).status_code,(400,403,404))
        with self.app.app_context(): self.assertEqual(get_db().get(User,2).account_state,'active')
        self.assertEqual(self.post('/api/admin/users/reset-password',{'userIds':[2,3],'newPassword':'shared-password'}).status_code,400)
        response=self.post('/api/admin/users/reset-password',{'userIds':[2,3],'generate':True})
        self.assertEqual(response.status_code,200)
        credentials=response.json['data']['credentials']
        self.assertEqual(len({c['password'] for c in credentials}),2)
        for credential in credentials:
            self.assertTrue(8<=len(credential['password'])<=20)
            with self.app.app_context():
                target=get_db().scalar(select(User).where(User.username==credential['username']))
                self.assertTrue(check_password_hash(target.password_hash,credential['password']))

    def test_regular_user_cannot_manage_accounts(self):
        self.login('alice')
        self.assertEqual(self.post('/api/admin/users/state',{'userIds':[3],'accountState':'closed'}).status_code,403)
        self.assertEqual(self.post('/api/admin/users/reset-password',{'userIds':[3],'generate':True}).status_code,403)
