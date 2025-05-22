from flask import Flask, render_template, url_for, redirect, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from groq_utils import generate_project_idea

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///genproj.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'SECRET_KEY'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"{self.id} - {self.username}"


@app.route('/')
def index():
    return render_template("index.html")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get("name")
        username = request.form.get("username")
        password = request.form.get("password")

        if User.query.filter_by(username=username).first():
             flash("Username already taken", "danger")
             return redirect(url_for("register"))
        
        hashed_password = generate_password_hash(password)
        new_user = User(name=name, username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash("Registered successfully. Please log in.", "success")
        return redirect(url_for("login"))
    
    return render_template("register.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            flash("Logged in successfully!", "success")
            return redirect(url_for("generate"))
        else:
            flash("Invalid username and passsword", "danger")
    
    return render_template("login.html")

@app.route('/logout')
def logout():
    session.pop("user_id", None)
    flash("Logged out successfully.", "info")
    return redirect(url_for("index"))

@app.route('/generate', methods=['GET', 'POST'])
def generate():
    if "user_id" not in session:
        flash("Please log in to user the generator.", "warning")
        return redirect(url_for("login"))
    
    idea = None
    topic = None
    if request.method == 'POST':
        topic = request.form.get('topic')
        if not topic:
            flash("Please enter a topic.", "warning")
            return redirect(url_for("generate"))
        prompt = f"Give me a coding project idea about {topic}."
        idea = generate_project_idea(prompt)    
        if idea.startswith("Error"):
            flash(idea, "danger")
            idea = None

    return render_template("generate.html", idea=idea, topic=topic)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)