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
