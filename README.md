<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AceGame – Real-Time Card Game</title>

<style>
    body {
        font-family: 'Segoe UI', sans-serif;
        margin: 0;
        background: #0f172a;
        color: #e2e8f0;
    }

    .container {
        max-width: 1000px;
        margin: auto;
        padding: 20px;
    }

    h1, h2 {
        color: #38bdf8;
    }

    .card {
        background: #1e293b;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }

    .badge {
        display: inline-block;
        padding: 6px 12px;
        margin: 5px;
        border-radius: 20px;
        background: #334155;
        font-size: 14px;
    }

    .highlight {
        color: #22c55e;
    }

    code {
        display: block;
        background: #020617;
        padding: 12px;
        border-radius: 8px;
        margin-top: 10px;
        color: #38bdf8;
        overflow-x: auto;
    }

    .grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 15px;
    }

    .feature {
        background: #334155;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
    }

    footer {
        text-align: center;
        margin-top: 40px;
        opacity: 0.6;
    }
</style>
</head>

<body>

<div class="container">

    <h1>🂡 AceGame</h1>
    <p class="highlight">
        Real-time multiplayer card game built with Django, WebSockets & Redis
    </p>

    <div class="card">
        <h2>📌 About</h2>
        <p>
            AceGame is inspired by real-world Ace card gameplay and provides a platform 
            to play with players online in real-time. It ensures smooth gameplay using 
            WebSockets and Redis-powered state management.
        </p>
    </div>

    <div class="card">
        <h2>🚀 Features</h2>
        <div class="grid">
            <div class="feature">🎮 Real-time multiplayer</div>
            <div class="feature">⚡ Low latency WebSockets</div>
            <div class="feature">🧠 Redis state management</div>
            <div class="feature">🏠 Room-based gameplay</div>
            <div class="feature">🔐 Authentication</div>
            <div class="feature">📡 Live updates</div>
        </div>
    </div>

    <div class="card">
        <h2>🏗️ Tech Stack</h2>
        <div class="badge">Django</div>
        <div class="badge">Django Channels</div>
        <div class="badge">WebSockets</div>
        <div class="badge">Redis</div>
        <div class="badge">SQLite</div>
        <div class="badge">HTML / CSS / JS</div>
    </div>

    <div class="card">
        <h2>⚙️ Installation</h2>

        <p><strong>1. Clone Repository</strong></p>
        <code>
git clone https://github.com/yourusername/acegame.git
cd acegame
        </code>

        <p><strong>2. Create Virtual Environment</strong></p>
        <code>
python -m venv venv
source venv/bin/activate
venv\Scripts\activate
        </code>

        <p><strong>3. Install Dependencies</strong></p>
        <code>
pip install -r requirements.txt
        </code>

        <p><strong>4. Start Redis</strong></p>
        <code>
redis-server
        </code>
    </div>

    <div class="card">
        <h2>▶️ Run Project</h2>

        <p><strong>Run Migrations</strong></p>
        <code>python manage.py migrate</code>

        <p><strong>Start Server</strong></p>
        <code>python manage.py runserver</code>

        <p><strong>Run ASGI (WebSockets)</strong></p>
        <code>daphne acegame.asgi:application</code>
    </div>

    <div class="card">
        <h2>🎮 How It Works</h2>
        <ul>
            <li>Users join a room</li>
            <li>WebSocket connection established</li>
            <li>Redis syncs game state</li>
            <li>Players perform actions</li>
            <li>Updates broadcast in real-time</li>
        </ul>
    </div>

    <footer>
        <p>Built with ❤️ using Django & WebSockets</p>
    </footer>

</div>

</body>
</html>
