from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField
from flask_session import Session
from wtforms.validators import DataRequired, Length
from werkzeug.security import generate_password_hash, check_password_hash
from utils import generate_project_idea, login_required, validate_input
from datetime import datetime, timedelta
import os
import secrets
import markdown
from markupsafe import Markup
import bleach
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_limiter.errors import RateLimitExceeded
from flask_migrate import Migrate
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
import uuid
import redis

app = Flask(__name__)

# Configuration
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config["SESSION_TYPE"] = "redis"
app.config["SESSION_REDIS"] = redis.from_url(os.getenv("REDIS_URL"))

if not app.config['SECRET_KEY']:
    raise ValueError("No SECRET_KEY set for Flask application")

db = SQLAlchemy(app)
migrate = Migrate(app, db)
Session(app)

@app.before_request
def warm_db():
    if request.endpoint in ('static', None) or request.path == '/favicon.ico':
        return
    
    try:
        db.session.execute(text("SELECT 1"))
    except OperationalError:
        app.logger.warning("Database is waking up or unreachable")

# Forms
class RegisterForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=1, max=100)])
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=50)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class GenerateForm(FlaskForm):
    topic = StringField('Topic', validators=[DataRequired(), Length(max=200)])
    submit = SubmitField('Generate')

class EditForm(FlaskForm):
    topic = StringField('Topic', validators=[DataRequired(), Length(max=200)])
    content = TextAreaField('Content', validators=[DataRequired()])
    submit = SubmitField('Save Changes')

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    project_ideas = db.relationship('ProjectIdea', backref='user', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Username: {self.username}>"

class ProjectIdea(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    topic = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    chat_messages = db.relationship("ChatMessage", backref="project", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"Project Idea: {self.topic}"
    
class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project_idea.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    role = db.Column(db.String(10), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)


REDIS_URL = os.getenv("REDIS_URL")
limiter = Limiter(get_remote_address, app=app, default_limits=["200 per day", "50 per hour"], storage_uri=REDIS_URL)

@app.errorhandler(RateLimitExceeded)
def ratelimit_handler(e):
    return jsonify({
        "error": "Too many requests. Please slow down",
        "message": str(e.description)
    }), 429

def get_current_user():
    user_id = session.get('user_id')
    if user_id:
        try:
            return User.query.get(user_id)
        except:
            return None
    return None

# Routes
@app.route('/')
def index():
    return render_template("index.html")

@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def register():
    if session.get('user_id'):
        return redirect(url_for('index'))
    form = RegisterForm()
    if form.validate_on_submit():
        name = bleach.clean(form.name.data.strip(), tags=['p', 'strong', 'em'], strip=True)
        username = bleach.clean(form.username.data.strip(), tags=['p', 'strong', 'em'], strip=True)
        password = form.password.data

        # Additional validation
        errors = validate_input({'name': name, 'username': username, 'password': password}, ['name', 'username', 'password'])

        try:
            if User.query.filter_by(username=username).first():
                errors.append("Username already taken")
        except OperationalError:
            flash("Our database just woke up. Please try again.", "warning")
            return redirect(url_for('login'))

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("register.html", form=form)

        try:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            new_user = User(name=name, username=username, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash("Registered successfully. Please log in.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            db.session.rollback()
            flash("An error occurred while creating your account.", "danger")
            return render_template("register.html", form=form)
    
    return render_template("register.html", form=form)

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    session.permanent = True
    if session.get('user_id'):
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        username = bleach.clean(form.username.data.strip(), tags=['p', 'strong', 'em'], strip=True)
        password = form.password.data

        errors = validate_input({'username': username, 'password': password}, ['username', 'password'])
        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("login.html", form=form)
        
        try:
            user = User.query.filter_by(username=username).first()
            if user and check_password_hash(user.password, password):
                session["user_id"] = user.id
                session["username"] = user.username
                flash(f"Welcome back, {user.name}", "success")
                return redirect(url_for("get_generate"))
            else:
                flash("Invalid username or password", "danger")
                return render_template("login.html", form=form)
        except OperationalError:
            flash("Our database just woke up. Please try again.", "warning")
            return redirect(url_for('login'))
    
    return render_template("login.html", form=form)

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("index"))

@app.route("/history")
@login_required
def history():
    user_id = session.get("user_id")
    projects = ProjectIdea.query.filter_by(user_id=user_id).order_by(ProjectIdea.timestamp.desc()).all()

    history_data = []
    for project in projects:
        history_data.append({
            "id": project.id,
            "topic": project.topic,
            "content": project.content[:200] + "..." if len(project.content) > 200 else project.content,
            "timestamp": project.timestamp.strftime("%Y-%m-%d %H:%M")
        })

    return jsonify(history_data)

@app.route("/generate", methods=["GET"])
@login_required
def get_generate():
    return render_template("generate.html")

@app.route("/chat", methods=["POST"])
@login_required
def chat():
    user_id = session.get("user_id")
    data = request.get_json()
    message_text = bleach.clean(data.get("message", ""), tags=['p', 'strong', 'em'], strip=True)
    project_id = data.get("project_id")
    if not project_id or not ProjectIdea.query.filter_by(id=project_id, user_id=user_id).first():
        return jsonify({"error": "Invalid or missing project id"}), 400

    user_msg = ChatMessage(
        user_id=user_id,
        project_id=project_id,
        role="user",
        content=message_text
    )
    db.session.add(user_msg)
    db.session.commit()

    conversation = ChatMessage.query.filter_by(user_id=user_id, project_id=project_id).order_by(ChatMessage.timestamp.asc()).all()
    messages_for_llm = [
        {"role": msg.role, "content": msg.content}
        for msg in conversation[-10:]
    ]

    ai_reply = generate_project_idea(messages_for_llm)

    ai_msg = ChatMessage(
        user_id=user_id,
        project_id=project_id,
        role="assistant",
        content=ai_reply
    )
    db.session.add(ai_msg)
    db.session.commit()

    chat_history = [
        {
            "role": msg.role,
            "content": msg.content,
            "timestamp": msg.timestamp.strftime("%Y-%m-%d %H:%M")
        }
        for msg in conversation
    ]
    return jsonify({"reply": ai_reply, "history": chat_history})

@app.route("/create_project", methods=["POST"])
@login_required
def create_project():
    user_id = session.get("user_id")
    data = request.get_json()
    topic = bleach.clean(data.get("topic", ""))
    content = bleach.clean(data.get("content", ""))
    new_project = ProjectIdea(user_id=user_id, topic=topic, content=content)
    db.session.add(new_project)
    db.session.commit()
    return jsonify({"id": new_project.id})

@app.route('/health')
def health():
    try:
        db.session.execute(text("SELECT 1"))
        return "OK", 200
    except:
        return "Database unreachable", 500

if __name__ == "__main__":
    app.run(debug=True)