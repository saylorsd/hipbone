from django.contrib import admin
from .models import UserLoginActivity

@admin.register(UserLoginActivity)
class UserLoginActivityAdmin(admin.ModelAdmin):
    list_display = ['user', 'login_datetime', 'login_IP', 'user_agent_info']
