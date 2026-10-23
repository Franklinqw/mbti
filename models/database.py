"""关系数据库模型。时间以 UTC 保存，通过 API 输出带时区的时间。"""
from datetime import datetime, timezone
from flask import current_app, g
from sqlalchemy import (JSON, Column, DateTime, ForeignKey, Index, Integer,
                        String, Text, UniqueConstraint, create_engine, event)
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso_time(value):
    return value.replace(tzinfo=timezone.utc).isoformat() if value else None


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(32), unique=True, nullable=False)
    email = Column(String(254), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(16), nullable=False, default='user')
    status = Column(String(16), nullable=False, default='pending', index=True)
    account_state = Column(String(16), nullable=False, default='active', server_default='active')
    created_at = Column(DateTime, nullable=False, default=utcnow)
    reviewed_at = Column(DateTime)
    reviewed_by = Column(Integer, ForeignKey('users.id'))
    review_note = Column(String(500), nullable=False, default='')
    session_version = Column(Integer, nullable=False, default=1)
    failed_logins = Column(Integer, nullable=False, default=0)
    locked_until = Column(DateTime)

    def public(self):
        return {'id': self.id, 'username': self.username, 'email': self.email,
                'role': self.role, 'status': self.status, 'accountState': self.account_state,
                'createdAt': iso_time(self.created_at),
                'reviewedAt': iso_time(self.reviewed_at), 'reviewNote': self.review_note}


class TestResult(Base):
    __tablename__ = 'test_results'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    attempt_id = Column(String(36), nullable=False)
    mode = Column(String(16), nullable=False)
    mbti_type = Column(String(4), nullable=False)
    answers = Column(JSON, nullable=False)
    report = Column(JSON, nullable=False)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=False, default=utcnow)
    __table_args__ = (UniqueConstraint('user_id', 'attempt_id', name='uq_result_attempt'),
                     Index('ix_results_user_time', 'user_id', 'completed_at'))

    def summary(self):
        return {'id': self.id, 'mode': self.mode, 'mbtiType': self.mbti_type,
                'nickname': self.report.get('nickname'), 'emoji': self.report.get('emoji'),
                'startedAt': iso_time(self.started_at), 'completedAt': iso_time(self.completed_at)}

    def detail(self):
        return {**self.summary(), 'report': self.report}


class TestAttempt(Base):
    __tablename__ = 'test_attempts'
    id = Column(String(36), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    mode = Column(String(16), nullable=False)
    started_at = Column(DateTime, nullable=False, default=utcnow)


class MailNotification(Base):
    __tablename__ = 'mail_notifications'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, unique=True)
    recipient = Column(String(254), nullable=False)
    status = Column(String(16), nullable=False, default='pending')
    attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(Text)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    sent_at = Column(DateTime)


def init_database(app):
    url = app.config['DATABASE_URL']
    options = {'pool_pre_ping': True, 'pool_recycle': 1800, 'hide_parameters': True}
    if str(url).startswith('mysql'):
        options['connect_args'] = {'connect_timeout': 5}
    engine = create_engine(url, **options)
    if engine.dialect.name == 'sqlite':
        @event.listens_for(engine, 'connect')
        def sqlite_foreign_keys(connection, record):
            connection.execute('PRAGMA foreign_keys=ON')
    app.extensions['db_engine'] = engine
    app.extensions['db_session_factory'] = sessionmaker(bind=engine, expire_on_commit=False)

    @app.teardown_appcontext
    def close_database(exception=None):
        db = g.pop('db', None)
        if db is not None:
            db.close()


def get_db():
    if 'db' not in g:
        g.db = current_app.extensions['db_session_factory']()
    return g.db
