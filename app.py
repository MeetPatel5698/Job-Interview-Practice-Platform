from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.config['SECRET_KEY'] = 'prepbot_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

db = SQLAlchemy(app)

# ======================
# DATABASE MODELS
# ======================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Interview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(100))
    question = db.Column(db.Text)
    answer = db.Column(db.Text)
    feedback = db.Column(db.Text)
    score = db.Column(db.Integer)

# ======================
# ROUTES
# ======================

@app.route('/')
def home():
    return render_template('index.html')

# SIGNUP
@app.route('/signup', methods=['GET', 'POST'])
def signup():

    if request.method == 'POST':

        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']

        hashed_password = generate_password_hash(password)

        new_user = User(
            full_name=full_name,
            email=email,
            password=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully!')

        return redirect(url_for('login'))

    return render_template('signup.html')

# LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            return redirect(url_for('dashboard'))

        flash('Invalid email or password')

    return render_template('login.html')

# DASHBOARD
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# INTERVIEW PAGE
@app.route('/interview', methods=['GET', 'POST'])
def interview():

    if request.method == 'POST':

        role = request.form['role']
        answer = request.form['answer']

        # Temporary dummy AI feedback
        feedback = "Good answer. Try adding more technical details."
        score = 8

        interview = Interview(
            role=role,
            question="Tell me about yourself",
            answer=answer,
            feedback=feedback,
            score=score
        )

        db.session.add(interview)
        db.session.commit()

        flash('Interview submitted successfully!')

        return redirect(url_for('history'))

    return render_template('interview.html')

# HISTORY PAGE
@app.route('/history')
def history():

    interviews = Interview.query.all()

    return render_template(
        'history.html',
        interviews=interviews
    )

# ======================
# RUN APP
# ======================

if __name__ == '__main__':

    with app.app_context():
        db.create_all()

    app.run(debug=True)