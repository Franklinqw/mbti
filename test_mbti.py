"""运行 python -m unittest test_mbti -v。"""
import unittest
from collections import Counter
from itertools import product
from app import create_app
from services.question_service import question_service
from models.database import Base, User, get_db
from werkzeug.security import generate_password_hash


class TestModes(unittest.TestCase):
    def setUp(self):
        self.app = create_app(overrides={'TESTING': True, 'DATABASE_URL':'sqlite://', 'SECRET_KEY':'test-key'})
        Base.metadata.create_all(self.app.extensions['db_engine'])
        with self.app.app_context():
            db = get_db()
            db.add(User(username='tester', email='tester@example.com', status='approved', password_hash=generate_password_hash('test-password')))
            db.commit()
        self.client = self.app.test_client()
        csrf = self.client.get('/api/auth/session').json['data']['csrfToken']
        response = self.client.post('/api/auth/login', json={'identifier':'tester','password':'test-password'}, headers={'X-CSRF-Token':csrf})
        self.headers = {'X-CSRF-Token':response.json['data']['csrfToken']}

    def tearDown(self):
        self.app.extensions['db_engine'].dispose()

    def test_balanced_question_banks(self):
        for mode, total in [('simple', 20), ('full', 60)]:
            with self.subTest(mode=mode):
                response = self.client.get('/api/questions', query_string={'mode': mode})
                questions = response.json['data']['questions']
                self.assertEqual(len(questions), total)
                self.assertEqual(len({q['index'] for q in questions}), total)
                self.assertEqual(set(Counter(q['dimension'] for q in questions).values()), {total // 4})

    def test_all_sixteen_results_in_both_modes(self):
        for mode in ['simple', 'full']:
            for letters in product('EI', 'SN', 'TF', 'JP'):
                target = ''.join(letters)
                answers = [
                    {'questionIndex': q.index,
                     'optionKey': next(o.key for o in q.options if o.side in target)}
                    for q in question_service.get_all_questions(mode)
                ]
                with self.subTest(mode=mode, target=target):
                    attempt = self.client.post('/api/attempts', json={'mode':mode}, headers=self.headers).json['data']['attemptId']
                    response = self.client.post('/api/result', json={'mode': mode, 'answers': answers, 'attemptId':attempt}, headers=self.headers)
                    self.assertEqual(response.status_code, 200)
                    data = response.json['data']
                    self.assertEqual(data['mbtiType'], target)
                    self.assertTrue(data['strengths'])
                    for dim in data['dimensions'].values():
                        self.assertEqual(dim['left']['percent'] + dim['right']['percent'], 100)

    def test_invalid_answers_and_modes(self):
        valid = [{'questionIndex': i, 'optionKey': 'A'} for i in range(1, 21)]
        invalid = [valid[:-1], [valid[0]] * 20, [None] * 20,
                   [{'questionIndex': True, 'optionKey': 'A'}] + valid[1:],
                   [{'questionIndex': 100, 'optionKey': 'A'}] + valid[1:],
                   [{'questionIndex': 1, 'optionKey': 'C'}] + valid[1:]]
        for answers in invalid:
            self.assertEqual(self.client.post('/api/result', json={'answers': answers}, headers=self.headers).status_code, 400)
        self.assertEqual(self.client.get('/api/questions?mode=unknown').status_code, 400)
        self.assertEqual(self.client.post('/api/result', json={'mode': 'full', 'answers': valid}, headers=self.headers).status_code, 400)
        self.assertEqual(self.client.post('/api/result', json=[1], headers=self.headers).status_code, 400)


if __name__ == '__main__':
    unittest.main()
