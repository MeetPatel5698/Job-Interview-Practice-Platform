from datetime import datetime
from uuid import uuid4

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
from sqlalchemy import text
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from services.ai_services import (
    evaluate_interview_answer,
    generate_answer_suggestion,
    generate_interview_question,
    summarize_interview_session
)

app = Flask(__name__)

# =========================
# CONFIG
# =========================

app.config['SECRET_KEY'] = 'prepbot_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

db = SQLAlchemy(app)

ROLE_OPTIONS = [
    'Software Developer',
    'Web Developer',
    'Data Analyst'
]

RESUME_TEXT_EXTENSIONS = {'.txt', '.md', '.csv', '.pdf'}
SESSION_LENGTH_OPTIONS = [5, 6, 7, 8]
DEFAULT_SESSION_QUESTIONS = 5

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

    improvements = db.Column(db.Text)

    answer_suggestion = db.Column(db.Text)

    session_id = db.Column(db.String(36))

    question_number = db.Column(db.Integer)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id')
    )

class InterviewDraft(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    role = db.Column(db.String(100))

    role_description = db.Column(db.Text)

    question = db.Column(db.Text)

    answer = db.Column(db.Text)

    resume_text = db.Column(db.Text)

    resume_filename = db.Column(db.String(255))

    feedback = db.Column(db.Text)

    improvements = db.Column(db.Text)

    answer_suggestion = db.Column(db.Text)

    score = db.Column(db.Integer)

    question_number = db.Column(db.Integer, default=0)

    total_questions = db.Column(
        db.Integer,
        default=DEFAULT_SESSION_QUESTIONS
    )

    session_id = db.Column(db.String(36))

    completed = db.Column(db.Boolean, default=False)

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        unique=True
    )

# =========================
# DATABASE SCHEMA CHECK
# =========================

def ensure_database_schema():

    db.create_all()

    interview_columns = {
        column[1]
        for column in db.session.execute(
            text('PRAGMA table_info(interview)')
        ).fetchall()
    }

    if 'user_id' not in interview_columns:

        db.session.execute(
            text('ALTER TABLE interview ADD COLUMN user_id INTEGER')
        )

        db.session.commit()

    interview_column_sql = {
        'improvements': 'ALTER TABLE interview ADD COLUMN improvements TEXT',
        'answer_suggestion': 'ALTER TABLE interview ADD COLUMN answer_suggestion TEXT',
        'session_id': 'ALTER TABLE interview ADD COLUMN session_id VARCHAR(36)',
        'question_number': 'ALTER TABLE interview ADD COLUMN question_number INTEGER',
    }

    for column_name, sql in interview_column_sql.items():

        if column_name not in interview_columns:

            db.session.execute(
                text(sql)
            )

    draft_columns = {
        column[1]
        for column in db.session.execute(
            text('PRAGMA table_info(interview_draft)')
        ).fetchall()
    }

    draft_column_sql = {
        'resume_text': 'ALTER TABLE interview_draft ADD COLUMN resume_text TEXT',
        'resume_filename': 'ALTER TABLE interview_draft ADD COLUMN resume_filename VARCHAR(255)',
        'answer_suggestion': 'ALTER TABLE interview_draft ADD COLUMN answer_suggestion TEXT',
        'total_questions': 'ALTER TABLE interview_draft ADD COLUMN total_questions INTEGER',
        'session_id': 'ALTER TABLE interview_draft ADD COLUMN session_id VARCHAR(36)',
        'completed': 'ALTER TABLE interview_draft ADD COLUMN completed BOOLEAN',
    }

    for column_name, sql in draft_column_sql.items():

        if column_name not in draft_columns:

            db.session.execute(
                text(sql)
            )

    db.session.commit()

# =========================
# INTERVIEW DRAFT HELPERS
# =========================

def get_interview_draft(user_id):

    return InterviewDraft.query.filter_by(
        user_id=user_id
    ).first()


def get_or_create_interview_draft(user_id):

    draft = get_interview_draft(user_id)

    if draft:

        return draft

    draft = InterviewDraft(user_id=user_id)

    db.session.add(draft)

    return draft


def save_interview_draft(
    user_id,
    role,
    role_description,
    question,
    answer,
    question_number,
    feedback=None,
    improvements=None,
    score=None,
    resume_text=None,
    resume_filename=None,
    answer_suggestion=None,
    total_questions=None,
    session_id=None,
    completed=None
):

    draft = get_or_create_interview_draft(user_id)

    draft.role = role
    draft.role_description = role_description
    draft.question = question
    draft.answer = answer
    draft.question_number = question_number
    draft.feedback = feedback
    draft.improvements = improvements
    draft.score = score
    draft.answer_suggestion = answer_suggestion

    if total_questions is not None:

        draft.total_questions = total_questions

    if session_id is not None:

        draft.session_id = session_id

    if completed is not None:

        draft.completed = completed

    if resume_text is not None:

        draft.resume_text = resume_text

    if resume_filename is not None:

        draft.resume_filename = resume_filename

    draft.updated_at = datetime.utcnow()

    db.session.commit()

    return draft


def extract_resume_text(uploaded_file):

    if not uploaded_file or not uploaded_file.filename:

        return '', ''

    filename = secure_filename(uploaded_file.filename)

    extension = ''

    if '.' in filename:

        extension = filename[filename.rfind('.'):].lower()

    if extension not in RESUME_TEXT_EXTENSIONS:

        return '', filename

    if extension == '.pdf':

        try:

            from pypdf import PdfReader

            reader = PdfReader(uploaded_file)

            resume_text = '\n'.join(
                page.extract_text() or ''
                for page in reader.pages
            ).strip()

            return resume_text, filename

        except Exception:

            return '', filename

    raw_data = uploaded_file.read()

    for encoding in ('utf-8', 'utf-16', 'latin-1'):

        try:

            return raw_data.decode(encoding).strip(), filename

        except UnicodeDecodeError:

            continue

    return '', filename


def normalize_total_questions(value):

    try:

        total_questions = int(value)

    except (TypeError, ValueError):

        return DEFAULT_SESSION_QUESTIONS

    if total_questions not in SESSION_LENGTH_OPTIONS:

        return DEFAULT_SESSION_QUESTIONS

    return total_questions


def get_session_answers(user_id, session_id):

    return Interview.query.filter_by(
        user_id=user_id,
        session_id=session_id
    ).order_by(
        Interview.question_number.asc(),
        Interview.id.asc()
    ).all()


def render_interview_setup_page(
    selected_role=None,
    role_description='',
    resume_text='',
    resume_filename='',
    active_draft=None,
    total_questions=DEFAULT_SESSION_QUESTIONS
):

    return render_template(
        'interview.html',
        roles=ROLE_OPTIONS,
        session_lengths=SESSION_LENGTH_OPTIONS,
        selected_role=selected_role or ROLE_OPTIONS[0],
        role_description=role_description or '',
        resume_text=resume_text or '',
        resume_filename=resume_filename or '',
        active_draft=active_draft,
        total_questions=normalize_total_questions(total_questions)
    )


def render_mock_interview_page(
    selected_role=None,
    role_description='',
    question='',
    question_number=0,
    answer='',
    resume_text='',
    resume_filename='',
    feedback=None,
    score=None,
    improvements=None,
    answer_suggestion=None,
    saved_progress=False,
    total_questions=DEFAULT_SESSION_QUESTIONS
):

    return render_template(
        'mock_interview.html',
        roles=ROLE_OPTIONS,
        selected_role=selected_role or ROLE_OPTIONS[0],
        role_description=role_description or '',
        resume_text=resume_text or '',
        resume_filename=resume_filename or '',
        question=question or '',
        question_number=question_number or 0,
        answer=answer or '',
        feedback=feedback,
        score=score,
        improvements=improvements,
        answer_suggestion=answer_suggestion,
        saved_progress=saved_progress,
        total_questions=normalize_total_questions(total_questions)
    )


def render_results_page(draft, answers):

    total_score = sum(
        answer.score or 0
        for answer in answers
    )

    average_score = round(total_score / len(answers), 1) if answers else 0

    strengths, weaknesses, improvements = summarize_interview_session(
        draft.role,
        draft.role_description,
        draft.resume_text,
        [
            {
                'question': answer.question,
                'answer': answer.answer,
                'score': answer.score,
                'feedback': answer.feedback,
                'improvements': answer.improvements,
            }
            for answer in answers
        ]
    )

    return render_template(
        'results.html',
        draft=draft,
        answers=answers,
        average_score=average_score,
        strengths=strengths,
        weaknesses=weaknesses,
        improvements=improvements
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

    active_draft = get_interview_draft(
        current_user.id
    )

    interview_count = Interview.query.filter_by(
        user_id=current_user.id
    ).count()

    return render_template(
        'dashboard.html',
        user=current_user,
        active_draft=active_draft,
        interview_count=interview_count
    )

# =========================
# INTERVIEW
# =========================

@app.route('/interview', methods=['GET', 'POST'])
@login_required
def interview():

    draft = get_interview_draft(
        current_user.id
    )

    if request.method == 'GET':

        if request.args.get('new') == '1' and draft:

            db.session.delete(draft)

            db.session.commit()

            draft = None

        return render_interview_setup_page(
            selected_role=draft.role if draft else None,
            role_description=draft.role_description if draft else '',
            resume_text=draft.resume_text if draft else '',
            resume_filename=draft.resume_filename if draft else '',
            active_draft=draft,
            total_questions=draft.total_questions if draft else DEFAULT_SESSION_QUESTIONS
        )

    selected_role = request.form.get(
        'role',
        ROLE_OPTIONS[0]
    )

    role_description = request.form.get(
        'role_description',
        ''
    ).strip()

    resume_text = request.form.get(
        'resume_text',
        ''
    ).strip()

    total_questions = normalize_total_questions(
        request.form.get('total_questions')
    )

    uploaded_resume_text, resume_filename = extract_resume_text(
        request.files.get('resume_file')
    )

    if uploaded_resume_text:

        resume_text = uploaded_resume_text

    elif request.files.get('resume_file') and request.files.get('resume_file').filename:

        flash('Resume upload supports .pdf, .txt, .md, or .csv files. You can also paste resume text below.')

        return render_interview_setup_page(
            selected_role=selected_role,
            role_description=role_description,
            resume_text=resume_text,
            resume_filename=resume_filename,
            active_draft=draft,
            total_questions=total_questions
        )

    if not role_description:

        flash('Please add a role description before starting the mock interview')

        return render_interview_setup_page(
            selected_role=selected_role,
            role_description=role_description,
            resume_text=resume_text,
            resume_filename=resume_filename or (draft.resume_filename if draft else ''),
            active_draft=draft,
            total_questions=total_questions
        )

    session_id = str(uuid4())

    question = generate_interview_question(
        selected_role,
        role_description,
        0,
        resume_text
    )

    save_interview_draft(
        current_user.id,
        selected_role,
        role_description,
        question,
        '',
        0,
        resume_text=resume_text,
        resume_filename=resume_filename or (draft.resume_filename if draft else ''),
        total_questions=total_questions,
        session_id=session_id,
        completed=False
    )

    return redirect(url_for('mock_interview'))


@app.route('/mock-interview', methods=['GET', 'POST'])
@login_required
def mock_interview():

    draft = get_interview_draft(
        current_user.id
    )

    if not draft or not draft.role_description:

        flash('Set up the role and description before starting the mock interview')

        return redirect(url_for('interview'))

    if not draft.session_id:

        draft.session_id = str(uuid4())
        draft.total_questions = normalize_total_questions(draft.total_questions)
        draft.completed = False
        db.session.commit()

    if request.method == 'GET':

        if draft.completed:

            return redirect(url_for('interview_results'))

        return render_mock_interview_page(
            selected_role=draft.role,
            role_description=draft.role_description,
            resume_text=draft.resume_text,
            resume_filename=draft.resume_filename,
            question=draft.question,
            question_number=draft.question_number,
            answer=draft.answer,
            feedback=draft.feedback,
            score=draft.score,
            improvements=draft.improvements,
            answer_suggestion=draft.answer_suggestion,
            saved_progress=True,
            total_questions=draft.total_questions
        )

    selected_role = request.form.get(
        'role',
        draft.role or ROLE_OPTIONS[0]
    )

    role_description = request.form.get(
        'role_description',
        draft.role_description or ''
    )

    resume_text = request.form.get(
        'resume_text',
        draft.resume_text or ''
    )

    resume_filename = request.form.get(
        'resume_filename',
        draft.resume_filename or ''
    )

    question = request.form.get(
        'question',
        draft.question or ''
    )

    question_number = request.form.get(
        'question_number',
        str(draft.question_number or 0)
    )

    answer = request.form.get(
        'answer',
        ''
    )

    feedback = request.form.get('feedback') or None
    improvements = request.form.get('improvements') or None
    answer_suggestion = request.form.get('answer_suggestion') or None
    score = request.form.get('score') or None

    try:
        question_number = int(question_number)
    except ValueError:
        question_number = 0

    try:
        score = int(score) if score is not None else None
    except ValueError:
        score = None

    action = request.form.get('action')
    total_questions = normalize_total_questions(
        draft.total_questions
    )

    if action == 'save_exit':

        save_interview_draft(
            current_user.id,
            selected_role,
            role_description,
            question,
            answer,
            question_number,
            feedback,
            improvements,
            score,
            resume_text=resume_text,
            resume_filename=resume_filename,
            answer_suggestion=answer_suggestion,
            total_questions=total_questions,
            completed=False
        )

        flash('Interview progress saved')

        return redirect(url_for('dashboard'))

    if action in ('generate_question', 'generate_questions'):

        if question.strip():

            question_number += 1

        question = generate_interview_question(
            selected_role,
            role_description,
            question_number,
            resume_text
        )

        save_interview_draft(
            current_user.id,
            selected_role,
            role_description,
            question,
            '',
            question_number,
            resume_text=resume_text,
            resume_filename=resume_filename,
            total_questions=total_questions,
            completed=False
        )

        return render_mock_interview_page(
            selected_role=selected_role,
            role_description=role_description,
            resume_text=resume_text,
            resume_filename=resume_filename,
            question=question,
            question_number=question_number,
            saved_progress=True,
            total_questions=total_questions
        )

    question = question.strip()
    answer = answer.strip()

    if not answer:

        flash('Please enter an answer before submitting')

        save_interview_draft(
            current_user.id,
            selected_role,
            role_description,
            question,
            answer,
            question_number,
            feedback,
            improvements,
            score,
            resume_text=resume_text,
            resume_filename=resume_filename,
            answer_suggestion=answer_suggestion,
            total_questions=total_questions,
            completed=False
        )

        return render_mock_interview_page(
            selected_role=selected_role,
            role_description=role_description,
            resume_text=resume_text,
            resume_filename=resume_filename,
            question=question,
            question_number=question_number,
            answer=answer,
            feedback=feedback,
            score=score,
            improvements=improvements,
            answer_suggestion=answer_suggestion,
            saved_progress=True,
            total_questions=total_questions
        )

    feedback, score, improvements = evaluate_interview_answer(
        selected_role,
        question,
        answer,
        role_description,
        resume_text
    )

    answer_suggestion = generate_answer_suggestion(
        selected_role,
        role_description,
        question,
        resume_text
    )

    new_interview = Interview(
        role=selected_role,
        question=question,
        answer=answer,
        feedback=feedback,
        score=score,
        improvements=improvements,
        answer_suggestion=answer_suggestion,
        session_id=draft.session_id,
        question_number=question_number,
        user_id=current_user.id
    )

    db.session.add(new_interview)

    answered_count = Interview.query.filter_by(
        user_id=current_user.id,
        session_id=draft.session_id
    ).count()

    if answered_count >= total_questions:

        save_interview_draft(
            current_user.id,
            selected_role,
            role_description,
            question,
            answer,
            question_number,
            feedback=feedback,
            improvements=improvements,
            score=score,
            resume_text=resume_text,
            resume_filename=resume_filename,
            answer_suggestion=answer_suggestion,
            total_questions=total_questions,
            session_id=draft.session_id,
            completed=True
        )

        return redirect(url_for('interview_results'))

    next_question_number = question_number + 1

    next_question = generate_interview_question(
        selected_role,
        role_description,
        next_question_number,
        resume_text
    )

    save_interview_draft(
        current_user.id,
        selected_role,
        role_description,
        next_question,
        '',
        next_question_number,
        resume_text=resume_text,
        resume_filename=resume_filename,
        total_questions=total_questions,
        session_id=draft.session_id,
        completed=False
    )

    return render_mock_interview_page(
        selected_role=selected_role,
        role_description=role_description,
        resume_text=resume_text,
        resume_filename=resume_filename,
        question=next_question,
        question_number=next_question_number,
        saved_progress=True,
        total_questions=total_questions
    )


@app.route('/interview-results')
@login_required
def interview_results():

    draft = get_interview_draft(
        current_user.id
    )

    if not draft or not draft.session_id:

        flash('No completed interview results found')

        return redirect(url_for('dashboard'))

    answers = get_session_answers(
        current_user.id,
        draft.session_id
    )

    if not answers:

        flash('No completed interview results found')

        return redirect(url_for('dashboard'))

    if not draft.completed and len(answers) < normalize_total_questions(draft.total_questions):

        flash('Complete all session questions before viewing results')

        return redirect(url_for('mock_interview'))

    return render_results_page(
        draft,
        answers
    )

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

        ensure_database_schema()

    app.run(debug=True)
