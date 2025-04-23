from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
import redis

from .models import Group, GroupTask, UserGroupRelation
from .serializers import GroupTaskSerializer

from django.core.exceptions import ObjectDoesNotExist


redis_db = redis.Redis(host='localhost', port=6379, db=0)


class GroupConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.group_id = self.scope["url_route"]["kwargs"]["group_id"]
        self.group_name = f"group_{self.group_id}"

        user = self.scope["user"]
        self.redis_key = f"u:{user.id}"

        if user.is_authenticated:
            async_to_sync(self.channel_layer.group_add) (
                self.group_name,
                self.channel_name
            )
            self.accept()

            self.send_json({
                "event": f"{user.id}_{user.username}_connected"
            })

            new_value = redis_db.incrby(self.redis_key, 1)
            if new_value == 1:
                async_to_sync(self.channel_layer.group_send)(
                    "admin_broadcast",
                    {
                        "type": "admin.online_status",
                        "user": {
                            "id": user.id,
                            "username": user.username,
                        },
                        "online": True
                    }
                )
                redis_db.expire(self.redis_key, 86400)
        else:
            self.close()

    def disconnect(self, code):
        async_to_sync(self.channel_layer.group_discard) (self.group_name, self.channel_name)

        if redis_db.exists(self.redis_key):
            new_value = redis_db.decrby(self.redis_key, 1)

            if new_value <= 0:
                redis_db.delete(self.redis_key)
                async_to_sync(self.channel_layer.group_send)(
                    "admin_broadcast",
                    {
                        "type": "admin.online_status",
                        "id": self.scope["user"].id,
                        "online": False
                    }
                )

    def receive_json(self, content, **kwargs):
        user = self.scope["user"]
        try:
            group = Group.objects.get(id=self.group_id)
        except ObjectDoesNotExist:
            self.send_json({
                "error": f"Group with id {self.group_id} does not exist."
            })
            return

        if not UserGroupRelation.objects.filter(user=user, group=group).exists():
            self.send_json({
                "error": "You are not a member of this group."
            })
            return

        command = content.get("command")
        data = content.get("data", {})

        if command == "create":
            serializer = GroupTaskSerializer(data=data, context={"request": None})

            if serializer.is_valid():
                serializer.save(state=0, group=group)
                # self.send_json({
                #     "success": "Group task created successfully.",
                #     "task": serializer.data
                # })

                async_to_sync(self.channel_layer.group_send)(
                    self.group_name,
                    {
                        "type": "group.task_created",
                        "task": serializer.data
                    }
                )
            else:
                self.send_json({
                    "error": "Invalid data.",
                    "details": serializer.errors
                })

        elif command == "update":
            task_id = data["id"]
            try:
                task = GroupTask.objects.get(id=task_id)
            except ObjectDoesNotExist:
                self.send_json({"error": f"Task with id {task_id} does not exist."})
                return

            serializer = GroupTaskSerializer(task, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                # self.send_json({
                #     "success": "Task updated successfully.",
                #     "task": serializer.data
                # })

                async_to_sync(self.channel_layer.group_send)(
                    self.group_name,
                    {
                        "type": "group.task_updated",
                        "task": serializer.data
                    }
                )
            else:
                self.send_json({
                    "error": "Invalid data.",
                    "details": serializer.errors
                })

        elif command == "delete":
            task_id = data
            try:
                task = GroupTask.objects.get(id=task_id)
            except ObjectDoesNotExist:
                self.send_json({"error": f"Task with id {task_id} does not exist."})
                return

            task.delete()

            # self.send_json({
            #     "success": f"Task with id {task_id} was deleted."
            # })

            async_to_sync(self.channel_layer.group_send)(
                self.group_name,
                {
                    "type": "group.task_deleted",
                    "task_id": task_id
                }
            )

        elif command == "complete":
            task_id = data
            try:
                task = GroupTask.objects.get(id=task_id)
            except ObjectDoesNotExist:
                self.send_json({"error": f"Task with id {task_id} does not exist."})
                return

            if task.state != 0:
                self.send_json({"error": f"Task with id {task_id} cannot be completed."})
                return

            serializer = GroupTaskSerializer(task, data={ "state": 1}, partial=True)
            if serializer.is_valid():
                serializer.save()

                # self.send_json({
                #     "success": f"Task with id {task_id} was completed."
                # })

                async_to_sync(self.channel_layer.group_send)(
                    self.group_name,
                    {
                        "type": "group.task_completed",
                        "task_id": task_id
                    }
                )
            else:
                self.send_json({
                    "error": "Failed to update task state.",
                    "details": serializer.errors
                })

        elif command == "expire":
            task_id = data
            try:
                task = GroupTask.objects.get(id=task_id)
            except ObjectDoesNotExist:
                self.send_json({"error": f"Task with id {task_id} does not exist."})
                return

            if task.state != 0:
                self.send_json({"error": f"Task with id {task_id} cannot be expired."})
                return

            serializer = GroupTaskSerializer(task, data={ "state": 2}, partial=True)
            if serializer.is_valid():
                serializer.save()

                # self.send_json({
                #     "success": f"Task with id {task_id} was expired."
                # })

                async_to_sync(self.channel_layer.group_send)(
                    self.group_name,
                    {
                        "type": "group.task_expired",
                        "task_id": task_id
                    }
                )
            else:
                self.send_json({
                    "error": "Failed to update task state.",
                    "details": serializer.errors
                })

    def group_task_created(self, event):
        self.send_json({
            "event": "task_created",
            "task": event["task"]
        })

    def group_task_updated(self, event):
        self.send_json({
            "event": "task_updated",
            "task": event["task"]
        })

    def group_task_deleted(self, event):
        self.send_json({
            "event": "task_deleted",
            "task_id": event["task_id"]
        })

    def group_task_completed(self, event):
        self.send_json({
            "event": "task_completed",
            "task_id": event["task_id"]
        })

    def group_task_expired(self, event):
        self.send_json({
            "event": "task_expired",
            "task_id": event["task_id"]
        })


class AdminConsumer(JsonWebsocketConsumer):
    def connect(self):
        if self.scope["user"].is_authenticated and self.scope["user"].is_staff:
            async_to_sync(self.channel_layer.group_add)(
                "admin_broadcast",
                self.channel_name
            )
            self.accept()
        else:
            self.close()

    def disconnect(self, code):
        async_to_sync(self.channel_layer.group_discard)(
            "admin_broadcast",
            self.channel_name
        )

    def admin_online_status(self, event):
        if event["online"]:
            message = {
                "event": "user_in",
                "user": event["user"],
            }
        else:
            message = {
                "event": "user_out",
                "id": event["id"],
            }
        self.send_json(message)