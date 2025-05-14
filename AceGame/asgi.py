import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path
# Import your consumers here (e.g., chat consumers for WebSockets)
# from myapp.consumers import MyConsumer


import Home.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'acegame.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            Home.routing.websocket_urlpatterns
        )
    ),
})
