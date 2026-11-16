from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Notification


@login_required
def notifications_list(request):
    # Fetch notifications for this specific user + global (user=None) broadcasts
    notifs = Notification.objects.filter(user=request.user) | \
             Notification.objects.filter(user__isnull=True)
    notifs = notifs.order_by('-created_at')

    # Mark all as read when viewed
    notifs.filter(is_read=False).update(is_read=True)

    return render(request, 'notifications.html', {'notifications': notifs})


@login_required
def unread_count(request):
    count = (
        Notification.objects.filter(user=request.user, is_read=False).count() +
        Notification.objects.filter(user__isnull=True, is_read=False).count()
    )
    return JsonResponse({'count': count})
