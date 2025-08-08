from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField
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
from flask_socketio import SocketIO, emit, disconnect
import uuid

app = Flask(__name__)

# Configuration
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=5)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

if not app.config['SECRET_KEY']:
    raise ValueError("No SECRET_KEY set for Flask application")

db = SQLAlchemy(app)
migrate = Migrate(app, db)
socketio = SocketIO(app, cors_allowed_origins="*", manage_session=False)
chat_sessions = {}

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

    def __repr__(self):
        return f"Project Idea: {self.topic}"
    
# Chat sessions
class ChatSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), nullable=False, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    messages = db.relationship('ChatMessage', backref='chat_session', lazy=True, cascade='all, delete-orphan')

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), db.ForeignKey('chat_session.session_id'), nullable=False)
    message_type = db.Column(db.String(10), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)

with app.app_context():
    db.create_all()

REDIS_URL = os.getenv("REDIS_URL")
limiter = Limiter(get_remote_address, app=app, default_limits=["200 per day", "50 per hour"], storage_uri=REDIS_URL)
limiter.init_app(app)

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

@socketio.on("connect")
def handle_connect():
    user = get_current_user()
    if not user:
        disconnect()
        return False
    
    print(f"User {user.username} connected")
    emit("connected", {
        "message": f"Welcome back, {user.name}!👋",
        "timestamp": datetime.now().isoformat()
    })

@socketio.on("disconnect")
def handle_disconnect():
    user = get_current_user()
    if user:
        print(f"User {user.username} disconnected")

@socketio.on("join_chat")
def handle_join_chat(data):
    user = get_current_user()
    if not user:
        emit("error", {"message": "Authentication required"})
        return
    
    session_id = data.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())

    chat_session = ChatSession.query.filter_by(session_id=session_id, user_id=user.id).first()
    if not chat_session:
        chat_session = ChatSession(session_id=session_id, user_id=user.id)
        db.session.add(chat_session)
        db.session.commit()

    messages = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.timestamp.asc()).all()
    history = []
    for msg in messages:
        history.append({
            "type": msg.message_type,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat()
        })

    emit("chat_history", {
        "session_id": session_id,
        "messages": history
    })

@socketio.on("user_message")
def handle_user_message(data):
    user = get_current_user()
    if not user:
        emit("error", {"message": "Authentication required"})
        return
    
    session_id = data.get("session_id")
    user_message = data.get("message", "").strip()

    if not user_message or not session_id:
        emit("error", {"message": "Message and session ID required"})
        return
    
    if len(user_message) > 500:
        emit("error", {"message": "Message too long (max 500 characters)"})
        return
    
    clean_message = bleach.clean(user_message, tags=[], strip=True)

    try:
        user_msg = ChatMessage(
            session_id=session_id,
            message_type="use",
            content=clean_message
        )
        db.session.add(user_msg)

        emit("message_confirmed", {
            "type": "user",
            "content": clean_message,
            "timestamp": datetime.now().isoformat()
        })

        emit("bot_typing", {"typing": True})

        prompt = f"Give me a coding project idea about {clean_message}."
        bot_response = generate_project_idea(prompt)

        if not bot_response or bot_response.startswith("Error"):
            bot_response = "I'm having trouble generating a project idea right now. Could you try rephrasing your request or try a different topic?"

        bot_msg = ChatMessage(
            session_id=session_id,
            message_type="bot",
            content=bot_response
        )
        db.session.add(bot_msg)

        project_idea = ProjectIdea(
            user_id=user.id,
            topic=clean_message,
            content=bot_response
        )
        db.session.add(project_idea)
        db.session.commit()

        emit("bot_response", {
            "type": "bot",
            "content": bot_response,
            "timestamp": datetime.now().isoformat(),
            "project_id": project_idea.id
        })

    except Exception as e:
        db.session.rollback()
        print(f"Error processing message: {str(e)}")
        emit("bot_response", {
            "type": "bot",
            "content": "I'm experiencing some technical difficulties. Please try again in a moment.",
            "timestamp": datetime.now().isoformat(),
            "error": True
        })
    finally:
        emit("bot_typing", {"typing": False})

@socketio.on("regenerate_response")
def handle_regenerate(data):
    user = get_current_user()
    if not user:
        emit("error", {"message": "Authentication required"})
        return
    
    session_id = data.get("session_id")
    original_topic = data.get("topic", "")

    if not session_id or not original_topic:
        emit("error", {"message": "Session and topic required"})
        return
    
    try:
        emit("bot_typing", {"typing": True})

        prompt = f"Give me a different coding project idea about {original_topic}."
        bot_response = generate_project_idea(prompt)

        if not bot_response or bot_response.startswith("Error"):
            bot_response = "I'm having trouble generating alternative ideas. Please try a different topic"
        
        bot_msg = ChatMessage(
            session_id=session_id,
            message_type="bot",
            content=bot_response
        )
        db.session.add(bot_msg)
        db.session.commit()

        emit("bot_response", {
            "type": "bot",
            "content": bot_response,
            "timestamp": datetime.now().isoformat(),
            "regenerated": True
        })

    except Exception as e:
        print(f"Error regenerating response: {str(e)}")
        emit("bot_response", {
            "type": "bot",
            "content": "I couldnt generate an alternative idea. Please try again",
            "timestamp": datetime.now().isoformat(),
            "error": True
        })
    finally:
        emit("bot_tying", {"typing": False})

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
                return redirect(url_for("generate"))
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

@app.route("/chat")
@login_required
def chat():
    user = get_current_user()
    session_id = str(uuid.uuid4())

    recent_projects = ProjectIdea.query.filter_by(user_id=user.id).order_by(ProjectIdea.timestamp.desc()).limit(10).all()

    return render_template("chat.html", session_id=session_id, user=user, recent_projects=recent_projects)

@app.route('/generate', methods=['GET', 'POST'])
@login_required
@limiter.limit("20 per minute")
def generate():
    return redirect(url_for("chat"))

@app.route('/view/<int:idea_id>')
@login_required
def view_idea(idea_id):
    idea = ProjectIdea.query.get_or_404(idea_id)
    if idea.user_id != session["user_id"]:
        flash("You do not have permission to view this idea.", "danger")
        return redirect(url_for("generate"))
    form = GenerateForm()
    edit_form = EditForm()
    history = ProjectIdea.query.filter_by(user_id=session["user_id"]).order_by(ProjectIdea.timestamp.desc()).all()
    rendered_idea = Markup(markdown.markdown(idea.content))
    return render_template("generate.html", form=form, edit_form=edit_form, idea=rendered_idea, topic=idea.topic, history=history, active_idea=idea, editing=False)

@app.route('/edit/<int:idea_id>', methods=['GET', 'POST'])
@login_required
def edit_idea(idea_id):
    idea = ProjectIdea.query.get_or_404(idea_id)
    if idea.user_id != session["user_id"]:
        flash("You do not have permission to edit this idea.", "danger")
        return redirect(url_for("generate"))
    form = GenerateForm()
    edit_form = EditForm()
    history = ProjectIdea.query.filter_by(user_id=session["user_id"]).order_by(ProjectIdea.timestamp.desc()).all()
    
    if edit_form.validate_on_submit():
        idea.topic = bleach.clean(edit_form.topic.data.strip(), tags=['p', 'strong', 'em'], strip=True)
        idea.content = bleach.clean(edit_form.content.data.strip(), tags=['p', 'strong', 'em'], strip=True)
        db.session.commit()
        flash("Idea updated successfully!", "success")
        return redirect(url_for('view_idea', idea_id=idea.id))
    
    if request.method == 'GET':
        edit_form.topic.data = idea.topic
        edit_form.content.data = idea.content
    
    return render_template("generate.html", form=form, edit_form=edit_form, idea=None, topic=None, history=history, active_idea=idea, editing=True)

@app.route('/delete_idea/<int:idea_id>', methods=['POST'])
@login_required
def delete_idea(idea_id):
    try:
        idea = ProjectIdea.query.filter_by(id=idea_id, user_id=session["user_id"]).first()
        if idea:
            db.session.delete(idea)
            db.session.commit()
            flash("Project idea deleted successfully.", "success")
        else:
            flash("Project idea not found", "danger")
    except Exception as e:
        db.session.rollback()
        flash("Error deleting project idea", "danger")
    return redirect(url_for("generate"))

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


@app.route('/health')
def health():
    try:
        db.session.execute("SELECT 1")
        return "OK", 200
    except:
        return "Database unreachable", 500

if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
