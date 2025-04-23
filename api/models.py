from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    username = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    sex = models.BooleanField(choices=[(True, "Male"), (False, "Female")])
    birth_date = models.DateField()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "sex", "birth_date"]

    def __str__(self):
        return f"ID:{self.id:>3} | {self.username} | {self.email}"


class Group(models.Model):
    name = models.CharField(max_length=63)

    def __str__(self):
        return f"ID:{self.id:>3} | {self.name}"


class UserGroupRelation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_groups")
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="group_users")
    # maybe add date_joined or/and is_admin later

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "group"], name="unique_user_group")
        ]

    def __str__(self):
        return f"ID:{self.id:>3} | {self.user.username} - {self.group.name}"


class Task(models.Model):
    name = models.CharField(max_length=63)
    description = models.TextField(blank=True, null=True)
    deadline = models.DateTimeField()
    state = models.PositiveSmallIntegerField(choices=[(0, 'uncompleted'), (1, 'completed'), (2, 'expired')], default=0)

    class Meta:
        abstract = True
        ordering = ["deadline"]


class UserTask(Task):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tasks")

    class Meta(Task.Meta):
        indexes = [models.Index(fields=["deadline"])]

    def __str__(self):
        return f"ID:{self.id:>3} | {self.name} | User:{self.user.username}"


class GroupTask(Task):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="tasks")

    class Meta(Task.Meta):
        indexes = [models.Index(fields=["deadline"])]

    def __str__(self):
        return f"ID:{self.id:>3} | {self.name} | Group:{self.group.name}"
