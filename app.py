from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# =========================
# CONFIG
# =========================

app.config['SECRET_KEY'] = 'prepbot_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

db = SQLAlchemy(app)

# =========================
# LOGIN MANAGER
# =========================

login_manager = LoginManager()
login_manager.init_app(app)

login_manager.login_view = 'login'

# =========================
# DATABASE MODELS
# =========================

class User(UserMixin, db.Model):

    id = db.Column(db.Integer, primary_key=True)

    full_name = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(200),
        nullable=False
    )

class Interview(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    role = db.Column(db.String(100))

    question = db.Column(db.Text)

    answer = db.Column(db.Text)

    feedback = db.Column(db.Text)

    score = db.Column(db.Integer)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id')
    )

# =========================
# USER LOADER
# =========================

@login_manager.user_loader
def load_user(user_id):

    return User.query.get(int(user_id))

# =========================
# HOME
# =========================

@app.route('/')
def home():

    return render_template('index.html')

# =========================
# SIGNUP
# =========================

@app.route('/signup', methods=['GET', 'POST'])
def signup():

    if request.method == 'POST':

        full_name = request.form['full_name']

        email = request.form['email']

        password = request.form['password']

        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:

            flash('Email already exists')

            return redirect(url_for('signup'))

        hashed_password = generate_password_hash(password)

        new_user = User(
            full_name=full_name,
            email=email,
            password=hashed_password
        )

        db.session.add(new_user)

        db.session.commit()

        flash('Account created successfully')

        return redirect(url_for('login'))

    return render_template('signup.html')

# =========================
# LOGIN
# =========================

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']

        password = request.form['password']

        user = User.query.filter_by(
            email=email
        ).first()

        if user and check_password_hash(
            user.password,
            password
        ):

            login_user(user)

            flash('Login successful')

            return redirect(url_for('dashboard'))

        else:

            flash('Invalid email or password')

    return render_template('login.html')

# =========================
# DASHBOARD
# =========================

@app.route('/dashboard')
@login_required
def dashboard():

    return render_template(
        'dashboard.html',
        user=current_user
    )

# =========================
# INTERVIEW
# =========================

@app.route('/interview', methods=['GET', 'POST'])
@login_required
def interview():

    if request.method == 'POST':

        role = request.form['role']

        answer = request.form['answer']

        feedback = (
            "Good answer. "
            "Try adding more technical details."
        )

        score = 8

        new_interview = Interview(
            role=role,
            question="Tell me about yourself",
            answer=answer,
            feedback=feedback,
            score=score,
            user_id=current_user.id
        )

        db.session.add(new_interview)

        db.session.commit()

        flash('Interview submitted successfully')

        return redirect(url_for('history'))

    return render_template('interview.html')

# =========================
# HISTORY
# =========================

@app.route('/history')
@login_required
def history():

    interviews = Interview.query.filter_by(
        user_id=current_user.id
    ).all()

    return render_template(
        'history.html',
        interviews=interviews
    )

# =========================
# LOGOUT
# =========================

@app.route('/logout')
@login_required
def logout():

    logout_user()

    flash('Logged out successfully')

    return redirect(url_for('home'))

# =========================
# RUN APP
# =========================

if __name__ == '__main__':

    with app.app_context():

        db.create_all()

    app.run(debug=True)