from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),

    # Student auth
    path('student-login/', views.student_login, name='student_login'),
    path('student-register/', views.student_register, name='student_register'),

    # Admin auth
    path('admin-login/', views.admin_login, name='admin_login'),
    path('admin-register/', views.admin_register, name='admin_register'),

    # Chatbot
    path('chatbot/', views.chatbot, name='chatbot'),
    path('chatbot-response/', views.chatbot_response, name='chatbot_response'),

    # Student features
    path('search-history/', views.search_history, name='search_history'),
    path('feedback/', views.submit_feedback, name='submit_feedback'),
    path('app-feedback/', views.app_feedback, name='app_feedback'),
    path('delete-account/', views.delete_account, name='delete_account'),
    path('profile/', views.student_profile, name='student_profile'),

    # Fee Records (Student)
    path('my-fees/', views.my_fees, name='my_fees'),

    # Enrollment (Student)
    path('my-enrollment/', views.my_enrollment, name='my_enrollment'),

    # Appointment Booking (Student)
    path('book-appointment/', views.book_appointment, name='book_appointment'),
    path('cancel-appointment/<int:appt_id>/', views.cancel_appointment, name='cancel_appointment'),

    # Logout
    path('logout/', views.user_logout, name='logout'),
]


