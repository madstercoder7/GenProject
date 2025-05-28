from flask import Flask, render_template, url_for, redirect, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from utils import generate_project_idea, login_required, validate_input
from datetime import datetime
import os
import secrets

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(basedir, 'genproj.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", secrets.token_hex(16))

db = SQLAlchemy(app)

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
    if request.method == 'POST':
        name = request.form.get("name").strip()
        username = request.form.get("username").strip()
        password = request.form.get("password")

        # Validation
        errors = validate_input(request.form, ['name', 'username', 'password'])

        if len(password) < 6:
            errors.append("Password must be at least 6 characters long")
        
        if len(username) < 3:
            errors.append("Username must be at least 3 characters long")

        if len(username) > 50:
            errors.append("Username must be less than 50 characters")
        
        if User.query.filter_by(username=username).first():
            errors.append("Username already taken")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("register.html", name=name, username=username)
        
        try:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            new_user = User(name=name, username=username, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash("Registered successfully. Please log in.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            db.session.rollback()
            flash("An error occured while creating your account. Please try again.", "danger")
            return render_template("register.html", name=name, username=username)
        
    return render_template("register.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get("username").strip()
        password = request.form.get("password")

        # Validation 
        errors = validate_input(request.form, ['username', 'password'])

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("login.html", username=username)

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["username"] = user.username
            flash(f"Welcome back, {user.name}", "success")
            return redirect(url_for("generate"))
        else:
            flash("Invalid username and passsword", "danger")
            return render_template("login.html", username=username)
    
    return render_template("login.html")

@app.route('/logout')
def logout():
    username = session.get("username")
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("index"))

@app.route('/generate', methods=['GET', 'POST'])
@login_required
def generate():
    idea = None
    topic = None

    if request.method == 'POST':
        topic = request.form.get('topic').strip()

        if not topic:
            flash("Please enter a topic.", "warning")
            return redirect(url_for("generate"))
        
        if len(topic) > 200:
            flash("Topic must be less than 200 characters", "warning")
            return redirect(url_for("generate"))
        
        try:
            prompt = f"Give me a coding project idea about {topic}."
            idea = generate_project_idea(prompt)    

            if idea and not idea.startswith("Error"):
                # Save to database
                new_idea = ProjectIdea(user_id=session["user_id"], topic=topic, content=idea)
                db.session.add(new_idea)
                db.session.commit()
            else:
                flash("Failed to generate", "danger")
                idea = None
        except Exception as e:
            flash("Error occured while generating", "danger")
            idea = None

    # Get user history
    try:
        history = ProjectIdea.query.filter_by(user_id=session["user_id"]).order_by(ProjectIdea.timestamp.desc()).all()
    except Exception as e:
        history = []
        flash("Could not load history", "warning")

    return render_template("generate.html", idea=idea, topic=topic, history=history)

@app.route('/delete_idea/<int:idea_id>')
@login_required
def delete_idea(idea_id):
    try:
        idea = ProjectIdea.query.filter_by(id=idea_id, user_id=session["user_id"]).first()

        if idea:
            db.session.delete(idea)
            db.session.commit()
        else:
            flash("Project idea not found", "danger")

    except Exception as e:
        db.session.rollback()
        flash("Error deleting project idea", "danger")

    return redirect(url_for("generate"))

if __name__ == "__main__":
    app.run(debug=True)