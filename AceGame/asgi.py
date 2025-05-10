import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path
# Import your consumers here (e.g., chat consumers for WebSockets)
# from myapp.consumers import MyConsumer
from AceGame.consumers import ChatConsumer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AceGame.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter([
            path('ws/chat/', ChatConsumer.as_asgi()),  # WebSocket URL
        ])
    ),
})
