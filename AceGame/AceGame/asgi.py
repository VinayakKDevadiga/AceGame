import os,django
# from django.core.asgi import get_asgi_application
# from channels.routing import ProtocolTypeRouter, URLRouter
# from channels.auth import AuthMiddlewareStack
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AceGame.settings')  # adjust if project name is different
django.setup()  

# import AceGame.routing  # Make sure this file exists and has `websocket_urlpatterns`

# from channels.sessions import SessionMiddlewareStack

# # application = ProtocolTypeRouter({
# #     "http": get_asgi_application(),
# #     "websocket": AuthMiddlewareStack(
# #         URLRouter(
# #             AceGame.routing.websocket_urlpatterns
# #         )
# #     ),
# # })

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from Account.utils import JWTAuthMiddleware
import AceGame.routing  # or wherever your websocket_urlpatterns live

# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "AceGame.settings")
# django.setup()

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": JWTAuthMiddleware(
        AuthMiddlewareStack(
            URLRouter(
                AceGame.routing.websocket_urlpatterns
            )
        )
    ),
})
