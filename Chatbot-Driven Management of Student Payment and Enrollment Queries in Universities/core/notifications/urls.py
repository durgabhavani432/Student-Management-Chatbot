from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notifications_list, name='list'),
    path('unread-count/', views.unread_count, name='unread_count'),
]
