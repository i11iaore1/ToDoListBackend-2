from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User, Group, UserTask, GroupTask

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "sex", "birth_date"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name"]


class UserTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserTask
        fields = ["id", "name", "description", "deadline", "state", "user"]
        extra_kwargs = {"user": {"read_only": True}}


class GroupTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupTask
        fields = ["id", "name", "description", "deadline", "state", "group"]
        extra_kwargs = {
            "group": {"read_only": True}
        }


class GroupDetailSerializer(serializers.ModelSerializer):
    members = serializers.SerializerMethodField()
    tasks = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ["id", "name", "members", "tasks"]

    def get_members(self, group):
        users = User.objects.filter(user_groups__group=group)
        return UserSerializer(users, many=True).data

    def get_tasks(self, group):
        tasks = group.tasks.all()
        return GroupTaskSerializer(tasks, many=True).data


class LoginResponseSerializer(serializers.Serializer):
    user = UserSerializer()
    groups = GroupSerializer(many=True)
    tasks = UserTaskSerializer(many=True)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        user = User.objects.filter(email=email).first()
        if not user or not user.check_password(password):
            raise serializers.ValidationError("Invalid email or password")

        return super().validate(attrs)

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        token["email"] = user.email
        token["username"] = user.username
        token["sex"] = user.sex
        token["birth_date"] = str(user.birth_date)

        return token