from django.contrib import admin
from django.db.models import Avg
from .models import User, FAQ, ChatLog, Feedback


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'role', 'is_active', 'date_joined']
    list_filter = ['role', 'is_active']
    search_fields = ['username', 'email', 'first_name']


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ['intent', 'question', 'created_at']
    search_fields = ['intent', 'question', 'answer']


@admin.register(ChatLog)
class ChatLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'message', 'timestamp']
    list_filter = ['timestamp']
    search_fields = ['user__username', 'message']


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ['user', 'rating', 'comment', 'created_at']
    list_filter = ['rating']
