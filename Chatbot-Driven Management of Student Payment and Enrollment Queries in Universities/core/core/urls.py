from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('users.urls')),
    path('admin-panel/', include('analytics.urls')),
    path('notifications/', include('notifications.urls')),
]
