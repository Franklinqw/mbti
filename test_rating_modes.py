"""五级题库的正反向计分、平局、完整性和历史流程。"""
import unittest
from collections import Counter
from app import create_app
from models.database import Base,User,get_db
from services.question_service import question_service
from services.result_service import result_service
from werkzeug.security import generate_password_hash

class RatingTests(unittest.TestCase):
    def test_structure_and_polarity(self):
        for mode,n,dimensions in [('communication',24,4),('big_five',50,5)]:
            bank=question_service.get_all_questions(mode)
            self.assertEqual(len(bank),n)
            self.assertEqual(len(set(q.text for q in bank)),n)
            self.assertEqual(set(Counter(q.dimension for q in bank).values()),{n//dimensions})
            for q in bank:
                self.assertEqual([o.key for o in q.options],list('ABCDE'))
                self.assertEqual(sorted(o.score for o in q.options),[1,2,3,4,5])
        bank=question_service.get_all_questions('big_five')
        positive=Counter(q.dimension for q in bank if q.options[0].score==1)
        self.assertEqual(dict(positive),{'E':5,'A':6,'C':6,'S':2,'O':7})

    def test_extremes_neutral_and_every_option(self):
        for mode in ['communication','big_five']:
            bank=question_service.get_all_questions(mode)
            for target in [1,3,5]:
                answers=[{'questionIndex':q.index,'optionKey':next(o.key for o in q.options if o.score==target)} for q in bank]
                report=result_service.build_result_detail(answers,mode)
                self.assertEqual(report['dimensionKind'],'scale')
                self.assertTrue(report['methodNote'])
                self.assertTrue(all(d['mean']==target and d['percent']==(target-1)*25 for d in report['dimensions'].values()))
                self.assertEqual(len(report['insights']),4 if mode=='communication' else 5)
            for q in bank:
                for o in q.options:
                    answers=[{'questionIndex':item.index,'optionKey':'C'} for item in bank]
                    answers[q.index-1]['optionKey']=o.key
                    report=result_service.build_result_detail(answers,mode)
                    dimension=report['dimensions'][q.dimension]
                    self.assertEqual(dimension['score'],3*(dimension['count']-1)+o.score)
            for invalid in [answers[:-1],answers[:-1]+[answers[0]], [{'questionIndex':i+1,'optionKey':'F'} for i in range(len(bank))]]:
                with self.assertRaises(ValueError): result_service.build_result_detail(invalid,mode)

    def test_api_history_idempotency_and_isolation(self):
        app=create_app(overrides={'TESTING':True,'DATABASE_URL':'sqlite://','SECRET_KEY':'rating-test-key'})
        Base.metadata.create_all(app.extensions['db_engine'])
        try:
            with app.app_context():
                db=get_db()
                for name in ['rating_user','other_user']:
                    db.add(User(username=name,email=name+'@example.com',status='approved',password_hash=generate_password_hash('test-password')))
                db.commit()
            client=app.test_client()
            def login(name):
                csrf=client.get('/api/auth/session').json['data']['csrfToken']
                res=client.post('/api/auth/login',json={'identifier':name,'password':'test-password'},headers={'X-CSRF-Token':csrf})
                self.assertEqual(res.status_code,200)
                return {'X-CSRF-Token':res.json['data']['csrfToken']}
            headers=login('rating_user');ids=[]
            for mode in ['communication','big_five']:
                attempt=client.post('/api/attempts',json={'mode':mode},headers=headers)
                self.assertEqual(attempt.status_code,201)
                data=attempt.json['data']
                self.assertTrue(all(len(q['options'])==5 for q in data['questions']))
                payload={'mode':mode,'attemptId':data['attemptId'],'answers':[{'questionIndex':q['index'],'optionKey':'E'} for q in data['questions']]}
                response=client.post('/api/result',json=payload,headers=headers)
                self.assertEqual(response.status_code,200,response.json)
                record=response.json['data'];ids.append(record['recordId'])
                self.assertLessEqual(len(record['mbtiType']),4)
                self.assertEqual(client.post('/api/result',json=payload,headers=headers).json['data']['recordId'],record['recordId'])
                self.assertEqual(client.get('/api/me/results/'+str(record['recordId'])).json['data']['report']['dimensions'],record['dimensions'])
            self.assertEqual(client.get('/api/me/results').json['data']['total'],2)
            login('other_user')
            for id in ids:self.assertEqual(client.get('/api/me/results/'+str(id)).status_code,404)
        finally:app.extensions['db_engine'].dispose()
