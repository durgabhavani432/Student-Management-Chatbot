from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),

    # User management (A2)
    path('users/', views.admin_users, name='admin_users'),
    path('users/add/', views.admin_add_user, name='admin_add_user'),
    path('users/<int:user_id>/delete/', views.admin_delete_user, name='admin_delete_user'),
    path('users/<int:user_id>/toggle/', views.admin_toggle_user, name='admin_toggle_user'),

    # FAQ management (A3)
    path('faqs/', views.admin_faqs, name='admin_faqs'),
    path('faqs/add/', views.admin_faq_add, name='admin_faq_add'),
    path('faqs/<int:faq_id>/edit/', views.admin_faq_edit, name='admin_faq_edit'),
    path('faqs/<int:faq_id>/delete/', views.admin_faq_delete, name='admin_faq_delete'),

    # Chat monitoring (A4)
    path('chatlogs/', views.admin_chatlogs, name='admin_chatlogs'),

    # Feedback (A5)
    path('feedback/', views.admin_feedback, name='admin_feedback'),

    # Analytics & Reporting (A6)
    path('analytics/', views.admin_analytics, name='admin_analytics'),
    path('analytics/export/', views.admin_export_csv, name='admin_export_csv'),

    # Model Management (A7)
    path('model-management/', views.admin_model_management, name='admin_model_management'),

    # Security & Backup (A8)
    path('security/', views.admin_security, name='admin_security'),

    # Notifications (A9)
    path('notifications/', views.admin_notifications, name='admin_notifications'),
    path('notifications/<int:notif_id>/delete/', views.admin_notification_delete, name='admin_notification_delete'),

    # System Maintenance (A10)
    path('maintenance/', views.admin_maintenance, name='admin_maintenance'),

    # Fee Management
    path('fees/', views.admin_fees, name='admin_fees'),
    path('fees/add/', views.admin_fee_add, name='admin_fee_add'),
    path('fees/<int:fee_id>/edit/', views.admin_fee_edit, name='admin_fee_edit'),
    path('fees/<int:fee_id>/delete/', views.admin_fee_delete, name='admin_fee_delete'),
    path('fees/<int:fee_id>/mark-paid/', views.admin_fee_mark_paid, name='admin_fee_mark_paid'),
    path('fees/alert/', views.admin_fee_alert, name='admin_fee_alert'),

    # Enrollment Management
    path('enrollments/', views.admin_enrollments, name='admin_enrollments'),
    path('enrollments/add/', views.admin_enrollment_add, name='admin_enrollment_add'),
    path('enrollments/<int:enroll_id>/edit/', views.admin_enrollment_edit, name='admin_enrollment_edit'),
    path('enrollments/<int:enroll_id>/delete/', views.admin_enrollment_delete, name='admin_enrollment_delete'),
    path('enrollments/alert/', views.admin_enrollment_alert, name='admin_enrollment_alert'),

    # Appointment Management
    path('appointments/', views.admin_appointments, name='admin_appointments'),
    path('appointments/<int:appt_id>/', views.admin_appointment_action, name='admin_appointment_action'),
]


