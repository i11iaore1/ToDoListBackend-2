from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate
from rest_framework import generics, views, viewsets, serializers
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, Group, UserTask, GroupTask, UserGroupRelation
from .serializers import UserSerializer, GroupSerializer, UserTaskSerializer, GroupTaskSerializer, CustomTokenObtainPairSerializer, GroupDetailSerializer

import redis

redis_db = redis.Redis(host='localhost', port=6379, db=0)

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)

        return Response({
            "refresh": str(refresh),
            "access": access,
            "user": UserSerializer(user).data
        }, status=201)


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get("email")
        password = request.data.get("password")

        user = authenticate(email=email, password=password)
        if not user:
            raise serializers.ValidationError("Invalid email or password")

        response = super().post(request, *args, **kwargs)

        user_tasks = user.tasks.all()
        user_groups = Group.objects.filter(group_users__user=user)

        response.data.update({
            "user": UserSerializer(user).data,
            "groups": GroupSerializer(user_groups, many=True).data,
            "tasks": UserTaskSerializer(user_tasks, many=True).data
        })

        return response


class UserRUDView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def partial_update(self, request, *args, **kwargs):
        user = self.get_object()
        data = request.data.copy()

        new_password = data.pop("password", None)

        serializer = self.get_serializer(user, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        if new_password:
            user.set_password(new_password)
            user.save()

        return Response(self.get_serializer(user).data)


class GroupViewSet(viewsets.ModelViewSet):
    serializer_class = GroupSerializer
    permission_classes = [AllowAny]
    lookup_field = "id"

    def get_queryset(self):
        return Group.objects.filter(group_users__user=self.request.user)

    def get_serializer_class(self):
        if self.action == "retrieve":
            return GroupDetailSerializer
        return GroupSerializer

    def perform_create(self, serializer):
        group = serializer.save()
        UserGroupRelation.objects.create(user=self.request.user, group=group)


class GroupMembershipView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, group_id, user_id):
        group = get_object_or_404(Group, id=group_id)
        user = get_object_or_404(User, id=user_id)

        # if not UserGroupRelation.objects.filter(user=request.user, group=group).exists():
        #     return Response({"detail": "You are not a member of this group."}, status=403)

        if UserGroupRelation.objects.filter(user=request.user, group=group).exists():
            return Response({"detail": "You are already a member of this group."}, status=400)

        UserGroupRelation.objects.get_or_create(user=user, group=group)

        return Response({
            "id": group.id,
            "name": group.name
        }, status=200)

    def delete(self, request, group_id, user_id):
        group = get_object_or_404(Group, id=group_id)
        user = get_object_or_404(User, id=user_id)

        if not UserGroupRelation.objects.filter(user=request.user, group=group).exists():
            return Response({"detail": "You are not a member of this group."}, status=403)

        relation = UserGroupRelation.objects.filter(user=user, group=group).first()
        if relation:
            relation.delete()
            return Response({"detail": f"User {user.username} removed from group '{group.name}'."}, status=204)
        return Response({"detail": "User is not in the group."}, status=400)


class UserTaskCreateView(generics.CreateAPIView):
    serializer_class = UserTaskSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(user=user)


class UserTaskRUDView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = UserTaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserTask.objects.filter(user=self.request.user)


class GroupTaskCreateView(generics.CreateAPIView):
    serializer_class = GroupTaskSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        group_id = self.kwargs.get("id")
        group = get_object_or_404(Group, id=group_id)

        if not UserGroupRelation.objects.filter(user=self.request.user, group=group).exists():
            return Response({"detail": "You are not a member of this group."}, status=403)

        serializer.save(group=group)


class GroupTaskRUDView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = GroupTaskSerializer
    permission_classes = [IsAuthenticated]
    queryset = GroupTask.objects.all()

    def get_queryset(self):
        return GroupTask.objects.filter(group__group_users__user=self.request.user)


class OnlineUsersView(APIView):
    def get(self, request):
        user = self.request.user
        if not user.is_staff:
            return Response({"detail": "You are not an administrator."}, status=403)

        online_users = []
        for key in redis_db.scan_iter("u:*"):
            user_id = key.decode().split(":")[1]
            try:
                user = User.objects.get(id=user_id)
                online_users.append({
                    "id": user.id,
                    "username": user.username
                })
            except User.DoesNotExist:
                pass
        return Response(online_users, status=200)