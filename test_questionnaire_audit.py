"""独立题库审计与全部模式的题目 API 完整性回归检查。"""
import unittest
from functools import lru_cache
from werkzeug.security import generate_password_hash
from app import create_app
from models.database import Base, User, get_db
from services.question_service import SUPPORTED_MODES
from scripts.audit_questionnaires import audit


@lru_cache(maxsize=1)
def audited():
    return audit()


class QuestionnaireAuditTests(unittest.TestCase):
    def test_all_questions_and_every_option_generate_valid_reports(self):
        data = audited()
        self.assertEqual(sum(d['questions'] for d in data.values()), 115)
        self.assertEqual(sum(d['options'] for d in data.values()), 230)
        self.assertTrue(all(not d['duplicate_exact_stems'] for d in data.values()))

    def test_pdp_and_age_outcomes_are_reachable(self):
        data = audited()
        pdp = data['pdp']['exact_analysis']
        self.assertEqual(sum(pdp['winners_under_uniform_random_answers'].values()), 2 ** 20)
        self.assertEqual(len(pdp['winners_under_uniform_random_answers']), 5)
        age = data['mental_age']['exact_analysis']
        self.assertEqual(sum(age['band_counts_under_uniform_random_answers'].values()), 2 ** 15)
        self.assertEqual(len(age['band_counts_under_uniform_random_answers']), 5)
        self.assertEqual((min(age['reachable_ages']), max(age['reachable_ages'])), (12, 60))

    def test_api_serializes_all_four_banks_without_dropping_options(self):
        app = create_app(overrides={'TESTING':True,'DATABASE_URL':'sqlite://','SECRET_KEY':'audit-only'})
        Base.metadata.create_all(app.extensions['db_engine'])
        try:
            with app.app_context():
                db = get_db()
                db.add(User(username='audituser',email='audit@example.com',status='approved',password_hash=generate_password_hash('audit-password')))
                db.commit()
            client = app.test_client()
            csrf = client.get('/api/auth/session').json['data']['csrfToken']
            login = client.post('/api/auth/login',json={'identifier':'audituser','password':'audit-password'},headers={'X-CSRF-Token':csrf})
            self.assertEqual(login.status_code,200)
            headers = {'X-CSRF-Token':login.json['data']['csrfToken']}
            for mode, bank in SUPPORTED_MODES.items():
                with self.subTest(mode=mode):
                    data = client.get('/api/questions',query_string={'mode':mode}).json['data']
                    self.assertEqual(data['questions'],[q.to_dict() for q in bank])
                    attempt = client.post('/api/attempts',json={'mode':mode},headers=headers)
                    self.assertEqual(attempt.status_code,201)
                    self.assertEqual(attempt.json['data']['questions'],data['questions'])
        finally:
            app.extensions['db_engine'].dispose()
