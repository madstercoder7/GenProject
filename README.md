# 🚀 GenProject — AI Project Idea Generator

GenProject is a Flask-based web app that uses AI to generate personalized project ideas instantly. Whether you're a student, hobbyist, or developer looking for your next big project, GenProject sparks inspiration with smart suggestions.

---

## 🌟 Features

- 🔐 User registration & login system
- 🤖 AI-genearated project ideas using Groq's LLaMA API
- 🧠 Personalized idea generation based on categories
- 🗂 Saves past ideas for each user
- 🌐 Animated landing page with SVG blobs
- ✨ Glassmorphism UI on login/register pages
- 🚦 Rate limiting via Redis to prevent abuse
- 🛠 Built with Flask, SQLAlchemy, PostgreSQL (Supabase), and Bootstrap

---

## 🏗 Tech Stack

| Layer            | Tools Used                              |
|------------------|-------------------------------------------|
| Backend          | Flask, Flask-Login, Flask-Limitier         |
| AI Integration   | Groq LLaMA API                            |
| Database         | SQLite (developmnent), PostgreSQL (production via Supabase) |
| Styling          | Bootstrap 5, Custom CSS, Animated SVGs   |
| Rate Limiting    | Redis (via Upstash)                      |

---

## ⚙️ Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/genproject.git
cd genproject

### 2. Setup Virtual Environment
python -m venv venv
# Activate:
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate

### 3. Install Python dependencies
pip install -r requirements.txt

### 4. Configure environment variables
GROQ_API_KEY=your_groq_api_key
DATABASE_URL=postgresql://your_supabase_url
REDIS_URL=redis://your_upstash_redis_url
SECRET_KEY=your_flask_secret_key

## Run the Flask App
flask run

# Contributing 
Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change

## Upcoming Features
- Converting to a chat style AI assistant
- Adding OAuth