# AceGame
Project that is based in real world ace game and provides flexibility to play with players online.
🂡 AceGame – Real-Time Card Game

AceGame is a real-time multiplayer card game built using Django, WebSockets, and Redis. It enables players to join game rooms, play cards live, and experience seamless real-time interactions.

🚀 Features
🎮 Real-time multiplayer gameplay<br>
⚡ WebSocket-based communication (low latency)
🧠 Game state management using Redis
🏠 Room-based game sessions
🔐 User authentication (Django Auth)
📡 Live updates for player actions
📱 Responsive UI (optional if you added frontend)
🏗️ Tech Stack
Backend: Django, Django Channels
Realtime Layer: WebSockets
Message Broker / Cache: Redis
Database: SQLite (depending on your setup)
Frontend: HTML/CSS/JS and Django templates
================================================================


⚙️ Installation
1. Clone the repository
git clone https://github.com/yourusername/acegame.git
cd acegame

2. Create virtual environment
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows

3. Install dependencies
pip install -r requirements.txt

4. Setup Redis
Make sure Redis is installed and running:
redis-server


▶️ Running the Project
Run migrations
python manage.py migrate

Start Django server
python manage.py runserver

Run ASGI server (for WebSockets)
daphne acegame.asgi:application
