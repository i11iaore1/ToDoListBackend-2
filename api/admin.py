from django.contrib import admin
from .models import User, Group, UserGroupRelation, UserTask, GroupTask

# email="admin@gmail.com"
# password="123"

admin.site.register(User)
admin.site.register(Group)
admin.site.register(UserGroupRelation)
admin.site.register(UserTask)
admin.site.register(GroupTask)
