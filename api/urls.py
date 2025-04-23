from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

group_viewset_router = DefaultRouter()
group_viewset_router.register(r'groups', views.GroupViewSet, basename='group')

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("my-profile/", views.UserRUDView.as_view(), name="manage_user"),
    path("tasks/", views.UserTaskCreateView.as_view(), name="create_user_task"),
    path("tasks/<int:pk>/", views.UserTaskRUDView.as_view(), name="manage_user_task"),
    path("", include(group_viewset_router.urls)),
    path("groups/<int:group_id>/member/<int:user_id>/", views.GroupMembershipView.as_view(), name="manage_group_members"),
    path("groups/<int:id>/tasks/", views.GroupTaskCreateView.as_view(), name="create_group_task"),
    path("group-tasks/<int:pk>/", views.GroupTaskRUDView.as_view(), name="manage_group_tasks"),
    path("online/", views.OnlineUsersView.as_view(), name="online_users")
]
