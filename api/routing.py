from django.urls import path, re_path

from .consumers import GroupConsumer, AdminConsumer

ws_urlpatterns = [
    re_path(r'ws/groups/(?P<group_id>\d+)/$', GroupConsumer.as_asgi()),
    path('ws/online/', AdminConsumer.as_asgi()),
]
