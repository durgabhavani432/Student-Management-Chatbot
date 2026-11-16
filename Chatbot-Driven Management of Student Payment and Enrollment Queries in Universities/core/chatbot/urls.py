from django.urls import path
from . import views

urlpatterns = [
    path("ui/", views.chatbot_ui),
    path("ask/", views.ask_question),
]
