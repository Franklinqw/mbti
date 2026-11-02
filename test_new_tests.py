"""PDP 动物人格与心理年龄测试的题库、计分与接口流程验证。"""
import unittest
from collections import Counter
from sqlalchemy import select
from werkzeug.security import generate_password_hash
from app import create_app
from models.database import Base, TestResult, User, get_db
from models.pdp_questions import PDP_QUESTIONS, PDP_RESULTS, PDP_SIDES
from models.mental_age_questions import (MENTAL_AGE_BANDS, MENTAL_AGE_QUESTIONS,
                                         MENTAL_AGE_SCORE_MAX, MENTAL_AGE_SCORE_MIN)
from services.scoring_service import scoring_service
from services.result_service import result_service


def answers_picking(questions, key_of):
    return [{'questionIndex': q.index, 'optionKey': key_of(q)} for q in questions]


class BankStructureTests(unittest.TestCase):
    def test_pdp_bank_balance(self):
        self.assertEqual(len(PDP_QUESTIONS), 20)
        tally = Counter()
        for i, question in enumerate(PDP_QUESTIONS, start=1):
            self.assertEqual(question.index, i)
            self.assertEqual(len(question.options), 2)
            sides = [opt.side for opt in question.options]
            self.assertEqual(len(set(sides)), 2, '同一题的两个选项不应属于同一种动物')
            tally.update(sides)
        self.assertEqual(sorted(tally.values()), [8] * 5)

    def test_mental_age_bank_structure(self):
        self.assertEqual(len(MENTAL_AGE_QUESTIONS), 15)
        for i, question in enumerate(MENTAL_AGE_QUESTIONS, start=1):
            self.assertEqual(question.index, i)
            self.assertEqual(sorted(opt.key for opt in question.options), ['A', 'B'])
            for opt in question.options:
                self.assertTrue(1 <= opt.score <= 5)
        self.assertEqual(MENTAL_AGE_SCORE_MIN, 30)
        self.assertEqual(MENTAL_AGE_SCORE_MAX, 62)
        # 分段区间应完整覆盖且不重叠
        ranges = [(low, high) for low, high, _ in MENTAL_AGE_BANDS]
        self.assertEqual(ranges[0][0], 12)
        self.assertEqual(ranges[-1][1], 60)
        for (_, high), (next_low, _) in zip(ranges, ranges[1:]):
            self.assertEqual(next_low, high + 1)


class ScoringTests(unittest.TestCase):
    def test_pdp_forced_winner(self):
        # 每题优先选孔雀选项(无孔雀时选第一项),孔雀应胜出
        answers = answers_picking(
            PDP_QUESTIONS,
            lambda q: next((o.key for o in q.options if o.side == 'PEACOCK'), q.options[0].key))
        self.assertEqual(scoring_service.calculate_pdp_type(answers), 'PEACOCK')
        detail = result_service.build_result_detail(answers, 'pdp')
        self.assertEqual(detail['mbtiType'], '孔雀')
        self.assertEqual(detail['dimensionKind'], 'single')
        self.assertEqual(detail['nickname'], PDP_RESULTS['PEACOCK'].nickname)
        # 维度占比合计约等于 100
        self.assertEqual(sum(v['percent'] for v in detail['dimensions'].values()), 100)

    def test_pdp_tie_stable(self):
        # 全部选第一项时结果稳定(可能平局,按固定顺序取先出现者)
        answers = answers_picking(PDP_QUESTIONS, lambda q: q.options[0].key)
        first = scoring_service.calculate_pdp_type(answers)
        for _ in range(3):
            self.assertEqual(scoring_service.calculate_pdp_type(answers), first)

    def test_mental_age_extremes(self):
        young = answers_picking(MENTAL_AGE_QUESTIONS, lambda q: min(q.options, key=lambda o: o.score).key)
        mature = answers_picking(MENTAL_AGE_QUESTIONS, lambda q: max(q.options, key=lambda o: o.score).key)
        self.assertEqual(scoring_service.calculate_mental_age(young), 12)
        self.assertEqual(scoring_service.calculate_mental_age(mature), 60)
        low = result_service.build_result_detail(young, 'mental_age')
        high = result_service.build_result_detail(mature, 'mental_age')
        self.assertEqual(low['mbtiType'], '12岁')
        self.assertEqual(low['mentalAge'], 12)
        self.assertEqual(low['animal'], '小鹿')
        self.assertEqual(high['mentalAge'], 60)
        self.assertEqual(high['animal'], '大象')

    def test_mental_age_mixed_answer(self):
        # 前半选低分、后半选高分,年龄应落在两个极值之间
        answers = [{'questionIndex': q.index,
                    'optionKey': (min(q.options, key=lambda o: o.score).key if q.index <= 8
                                  else max(q.options, key=lambda o: o.score).key)}
                   for q in MENTAL_AGE_QUESTIONS]
        age = scoring_service.calculate_mental_age(answers)
        self.assertTrue(12 < age < 60)
        detail = result_service.build_result_detail(answers, 'mental_age')
        self.assertEqual(detail['mbtiType'], f'{age}岁')

    def test_invalid_answers_rejected(self):
        for mode, bank in (('pdp', PDP_QUESTIONS), ('mental_age', MENTAL_AGE_QUESTIONS)):
            complete = answers_picking(bank, lambda q: q.options[0].key)
            with self.subTest(mode=mode):
                with self.assertRaises(ValueError):
                    scoring_service.calculate_pdp_type(complete[:-1], mode) if mode == 'pdp' \
                        else scoring_service.calculate_mental_age(complete[:-1], mode)
                bad = [dict(a) for a in complete]
                bad[0]['optionKey'] = 'Z'
                with self.assertRaises(ValueError):
                    scoring_service.calculate_pdp_type(bad, mode) if mode == 'pdp' \
                        else scoring_service.calculate_mental_age(bad, mode)


class ApiFlowTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(overrides={'TESTING': True, 'DATABASE_URL': 'sqlite://',
                                         'SECRET_KEY': 'testing-only-key', 'MAIL_HOST': ''})
        Base.metadata.create_all(self.app.extensions['db_engine'])
        with self.app.app_context():
            db = get_db()
            db.add(User(username='alice', email='alice@example.com',
                        password_hash=generate_password_hash('test-password'), status='approved'))
            db.commit()
        self.client = self.app.test_client()
        token = self.client.get('/api/auth/session').json['data']['csrfToken']
        self.headers = {'X-CSRF-Token': token}
        login = self.client.post('/api/auth/login', json={'identifier': 'alice', 'password': 'test-password'},
                                 headers=self.headers)
        self.assertEqual(login.status_code, 200)
        self.headers = {'X-CSRF-Token': login.json['data']['csrfToken']}

    def tearDown(self):
        self.app.extensions['db_engine'].dispose()

    def submit_test(self, mode, bank, key_of):
        created = self.client.post('/api/attempts', json={'mode': mode}, headers=self.headers)
        self.assertEqual(created.status_code, 201)
        data = created.json['data']
        self.assertEqual(data['total'], len(bank))
        answers = answers_picking(bank, key_of)
        result = self.client.post('/api/result', json={'mode': mode, 'attemptId': data['attemptId'],
                                                       'answers': answers}, headers=self.headers)
        self.assertEqual(result.status_code, 200)
        return result.json['data']

    def test_pdp_flow(self):
        report = self.submit_test('pdp', PDP_QUESTIONS,
                                  lambda q: next((o.key for o in q.options if o.side == 'KOALA'), q.options[0].key))
        self.assertIn(report['mbtiType'], {'老虎', '孔雀', '考拉', '猫头鹰', '变色龙'})
        self.assertEqual(report['dimensionKind'], 'single')
        history = self.client.get('/api/me/results').json['data']['items']
        self.assertEqual(history[0]['mode'], 'pdp')
        self.assertEqual(history[0]['mbtiType'], report['mbtiType'])

    def test_mental_age_flow(self):
        report = self.submit_test('mental_age', MENTAL_AGE_QUESTIONS,
                                  lambda q: max(q.options, key=lambda o: o.score).key)
        self.assertTrue(report['mbtiType'].endswith('岁'))
        detail = self.client.get('/api/me/results').json['data']['items'][0]
        self.assertEqual(detail['mode'], 'mental_age')

    def test_mode_mismatch_rejected(self):
        created = self.client.post('/api/attempts', json={'mode': 'pdp'}, headers=self.headers).json['data']
        answers = answers_picking(PDP_QUESTIONS, lambda q: q.options[0].key)
        mismatch = self.client.post('/api/result', json={'mode': 'simple', 'attemptId': created['attemptId'],
                                                         'answers': answers}, headers=self.headers)
        self.assertEqual(mismatch.status_code, 400)

    def test_record_counts(self):
        self.submit_test('pdp', PDP_QUESTIONS, lambda q: q.options[0].key)
        with self.app.app_context():
            records = get_db().scalars(select(TestResult)).all()
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].mode, 'pdp')
            self.assertLessEqual(len(records[0].mbti_type), 4)


if __name__ == '__main__':
    unittest.main()
