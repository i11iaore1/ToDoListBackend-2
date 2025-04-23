import os

from django.core.asgi import get_asgi_application

from channels.routing import ProtocolTypeRouter, URLRouter

from api.middleware import JWTAuthMiddlewareStack
from api.routing import ws_urlpatterns

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ToDoListProject.settings')

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': JWTAuthMiddlewareStack(
        URLRouter(ws_urlpatterns)
    )
})