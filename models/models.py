from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Interview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role_selected = db.Column(db.String(100), nullable=False)
    interview_date = db.Column(db.DateTime, default=datetime.utcnow)
    final_score = db.Column(db.Integer)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))