from flask import Flask, render_template, url_for, redirect, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length
from werkzeug.security import generate_password_hash, check_password_hash
from utils import generate_project_idea, login_required, validate_input
from datetime import datetime
import os
import secrets
import markdown
from markupsafe import Markup
import bleach

app = Flask(__name__)

# Configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(basedir, 'genproj.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", secrets.token_hex(16))

if not app.config['SECRET_KEY']:
    raise ValueError("No SECRET_KEY set for Flask application")

db = SQLAlchemy(app)

# Forms
class RegisterForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=1, max=100)])
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=50)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Submit')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class GenerateForm(FlaskForm):
    topic = StringField('Topic', validators=[DataRequired(), Length(max=200)])
    submit = SubmitField('Generate')

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
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

with app.app_context():
    db.create_all()

# Routes
@app.route('/')
def index():
    return render_template("index.html")

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        name = bleach.clean(form.name.data.strip(), tags=['p', 'strong', 'em'], strip=True)
        username = bleach.clean(form.username.data.strip(), tags=['p', 'strong', 'em'], strip=True)
        password = form.password.data

        # Additional validation
        errors = validate_input({'name': name, 'username': username, 'password': password}, ['name', 'username', 'password'])
        if User.query.filter_by(username=username).first():
            errors.append("Username already taken")

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
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = bleach.clean(form.username.data.strip(), tags=['p', 'strong', 'em'], strip=True)
        password = form.password.data

        errors = validate_input({'username': username, 'password': password}, ['username', 'password'])
        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("login.html", form=form)

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["username"] = user.username
            flash(f"Welcome back, {user.name}", "success")
            return redirect(url_for("generate"))
        else:
            flash("Invalid username or password", "danger")
            return render_template("login.html", form=form)
    
    return render_template("login.html", form=form)

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("index"))

@app.route('/generate', methods=['GET', 'POST'])
@login_required
def generate():
    form = GenerateForm()
    idea = None
    topic = None
    if form.validate_on_submit():
        topic = bleach.clean(form.topic.data.strip(), tags=['p', 'strong', 'em'], strip=True)
        try:
            prompt = f"Give me a coding project idea about {topic}."
            idea = generate_project_idea(prompt)
            if idea and not idea.startswith("Error"):
                new_idea = ProjectIdea(user_id=session["user_id"], topic=topic, content=idea)
                db.session.add(new_idea)
                db.session.commit()
            else:
                flash("Failed to generate project idea", "danger")
                idea = None
        except Exception as e:
            flash("Error occurred while generating project idea", "danger")
            idea = None

    history = ProjectIdea.query.filter_by(user_id=session["user_id"]).order_by(ProjectIdea.timestamp.desc()).all()
    rendered_idea = Markup(markdown.markdown(idea)) if idea else None
    return render_template("generate.html", form=form, idea=rendered_idea, topic=topic, history=history)

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

if __name__ == "__main__":
    app.run(debug=True)