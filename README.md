🧩 Social Media Dashboard
A Django-based web application that integrates Reddit and Discord, allowing users to manage and view social media activity from a single dashboard.

🚀 Features
User registration and login

Reddit integration via PRAW (fetch posts)

Discord integration (bot or placeholder messages)

Profile management with social media credentials

Unified dashboard to display Reddit and Discord content

🛠️ Tech Stack
Django

PRAW (Reddit API)

discord.py (Discord Bot API)

Bootstrap or TailwindCSS (for UI)

📦 Setup Instructions
Clone the repository
git clone https://github.com/yourusername/social-media-dashboard.git
cd social-media-dashboard

Create and activate virtual environment
python -m venv venv
source venv/bin/activate (Windows: venv\Scripts\activate)

Install dependencies
pip install -r requirements.txt

Apply migrations
python manage.py migrate

Run the development server
python manage.py runserver

Visit the app
http://localhost:8000/

🔐 Notes
Add your Reddit and Discord credentials through the profile page after login.

For Discord integration, create a bot via the Discord Developer Portal, enable necessary intents, and invite it to your server.

Use .env or Django settings.py to securely manage sensitive data.
