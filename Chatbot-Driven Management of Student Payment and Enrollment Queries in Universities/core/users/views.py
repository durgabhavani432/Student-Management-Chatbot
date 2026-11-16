from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.contrib import messages

from .models import User, FAQ, ChatLog, Feedback, FeeRecord, EnrollmentRecord, AppointmentRequest
from nlp_engine.chatbot import get_bot_response


# =========================
# HOME PAGE
# =========================
def home(request):
    return render(request, 'home.html')


# =========================
# STUDENT REGISTER
# =========================
def student_register(request):
    error = ""
    if request.method == "POST":
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        if not name or not email or not username or not password or not confirm_password:
            error = "All fields are required."
        elif password != confirm_password:
            error = "Passwords do not match."
        elif User.objects.filter(username=username).exists():
            error = "Username already exists. Please choose another."
        elif User.objects.filter(email=email).exists():
            error = "Email already registered."
        else:
            User.objects.create_user(
                username=username,
                password=password,
                email=email,
                first_name=name,
                role='student'
            )
            return redirect('student_login')

    return render(request, 'student_register.html', {'error': error})


# =========================
# STUDENT LOGIN
# =========================
def student_login(request):
    error = ""
    if request.method == "POST":
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        user = authenticate(request, username=username, password=password)

        if user is not None and user.role == 'student':
            login(request, user)
            return redirect('chatbot')
        else:
            error = "Invalid credentials or not a student account."

    return render(request, 'student_login.html', {'error': error})


# =========================
# ADMIN REGISTER
# =========================
def admin_register(request):
    error = ""
    if request.method == "POST":
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        if not username or not password:
            error = "All fields are required."
        elif User.objects.filter(username=username).exists():
            error = "Username already exists."
        else:
            User.objects.create_user(username=username, password=password, role='admin')
            return redirect('admin_login')

    return render(request, 'admin_register.html', {'error': error})


# =========================
# ADMIN LOGIN
# =========================
def admin_login(request):
    error = ""
    if request.method == "POST":
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        user = authenticate(request, username=username, password=password)

        if user is not None and (user.role == 'admin' or user.is_superuser):
            login(request, user)
            return redirect('admin_dashboard')
        else:
            error = "Invalid credentials or not an admin account."

    return render(request, 'admin_login.html', {'error': error})


# =========================
# CHATBOT PAGE
# =========================
@login_required(login_url='/student-login/')
def chatbot(request):
    faqs = FAQ.objects.all()[:8]   # quick-click buttons
    
    # Pre-format the titles here to avoid needing custom template tags
    for faq in faqs:
        faq.formatted_intent = faq.intent.replace('_', ' ').title()
        
    return render(request, 'chatbot.html', {'faqs': faqs})


@login_required(login_url='/student-login/')
@require_POST
def chatbot_response(request):
    message = request.POST.get('message', '').strip()
    if not message:
        return JsonResponse({'reply': "Please type a question."})

    reply = get_bot_response(message)

    # Clean the reply if it comes back as a string representation of a list
    if hasattr(reply, 'startswith') and reply.startswith("['") and reply.endswith("']"):
        reply = reply[2:-2]
    elif hasattr(reply, 'startswith') and reply.startswith('["') and reply.endswith('"]'):
        reply = reply[2:-2]

    log = ChatLog.objects.create(
        user=request.user,
        message=message,
        response=reply
    )
    return JsonResponse({'reply': reply, 'log_id': log.id})


# =========================
# SEARCH HISTORY  (U5)
# =========================
@login_required(login_url='/student-login/')
def search_history(request):
    query = request.GET.get('q', '').strip()
    logs = ChatLog.objects.filter(user=request.user)
    if query:
        logs = logs.filter(Q(message__icontains=query) | Q(response__icontains=query))
    return render(request, 'search_history.html', {'logs': logs, 'query': query})


# =========================
# FEEDBACK  (U6)
# =========================
@login_required(login_url='/student-login/')
@require_POST
def submit_feedback(request):
    log_id = request.POST.get('log_id')
    rating = request.POST.get('rating', 5)
    comment = request.POST.get('comment', '')

    try:
        chat_log = ChatLog.objects.get(id=log_id, user=request.user)
        # Avoid duplicate feedback for same log
        Feedback.objects.update_or_create(
            chat_log=chat_log,
            defaults={
                'user': request.user,
                'rating': int(rating),
                'comment': comment
            }
        )
        return JsonResponse({'status': 'ok', 'message': 'Feedback saved!'})
    except ChatLog.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Invalid log.'}, status=404)


# =========================
# APP FEEDBACK  (General)
# =========================
@login_required(login_url='/student-login/')
def app_feedback(request):
    if request.method == "POST":
        rating = request.POST.get('rating', 5)
        comment = request.POST.get('comment', '')
        Feedback.objects.update_or_create(
            user=request.user,
            chat_log=None,
            defaults={'rating': int(rating), 'comment': comment}
        )
        return redirect('chatbot')
    
    existing = Feedback.objects.filter(user=request.user, chat_log=None).first()
    return render(request, 'app_feedback.html', {'existing': existing})


# =========================
# DELETE ACCOUNT  (U7 extended)
# =========================
@login_required(login_url='/student-login/')
def delete_account(request):
    if request.method == "POST":
        user = request.user
        logout(request)
        user.delete()
        return redirect('home')
    return render(request, 'delete_account.html')


# =========================
# LOGOUT
# =========================
def user_logout(request):
    logout(request)
    return redirect('home')


# =========================
# STUDENT PROFILE  (U9)
# =========================
@login_required(login_url='/student-login/')
def student_profile(request):
    user = request.user
    success = ''
    error = ''

    if request.method == 'POST':
        action = request.POST.get('action', 'profile')

        if action == 'profile':
            name = request.POST.get('name', '').strip()
            email = request.POST.get('email', '').strip()
            phone = request.POST.get('phone', '').strip()

            if not name or not email:
                error = 'Name and email are required.'
            elif User.objects.filter(email=email).exclude(pk=user.pk).exists():
                error = 'Email already in use by another account.'
            else:
                user.first_name = name
                user.email = email
                user.phone = phone
                user.save()
                success = 'Profile updated successfully!'

        elif action == 'password':
            old_pw = request.POST.get('old_password', '')
            new_pw = request.POST.get('new_password', '').strip()
            confirm_pw = request.POST.get('confirm_password', '').strip()

            if not user.check_password(old_pw):
                error = 'Current password is incorrect.'
            elif len(new_pw) < 6:
                error = 'New password must be at least 6 characters.'
            elif new_pw != confirm_pw:
                error = 'New passwords do not match.'
            else:
                user.set_password(new_pw)
                user.save()
                update_session_auth_hash(request, user)
                success = 'Password changed successfully!'

    total_chats = ChatLog.objects.filter(user=user).count()
    total_feedback = Feedback.objects.filter(user=user).count()

    return render(request, 'profile.html', {
        'user': user,
        'success': success,
        'error': error,
        'total_chats': total_chats,
        'total_feedback': total_feedback,
    })


# =========================
# MY FEE RECORDS  (Student view)
# =========================
@login_required(login_url='/student-login/')
def my_fees(request):
    fees = FeeRecord.objects.filter(student=request.user).order_by('due_date')
    total_due = sum(f.amount_due for f in fees)
    total_paid = sum(f.amount_paid for f in fees)
    total_balance = sum(f.balance for f in fees)
    overdue_count = fees.filter(status='overdue').count()
    return render(request, 'my_fees.html', {
        'fees': fees,
        'total_due': total_due,
        'total_paid': total_paid,
        'total_balance': total_balance,
        'overdue_count': overdue_count,
    })


# =========================
# MY ENROLLMENT RECORDS  (Student view)
# =========================
@login_required(login_url='/student-login/')
def my_enrollment(request):
    enrollments = EnrollmentRecord.objects.filter(student=request.user).order_by('-created_at')
    return render(request, 'my_enrollment.html', {'enrollments': enrollments})


# =========================
# APPOINTMENT BOOKING  (Student book/view/cancel)
# =========================
@login_required(login_url='/student-login/')
def book_appointment(request):
    error = ''
    success = ''
    if request.method == 'POST':
        topic = request.POST.get('topic', 'general')
        mode = request.POST.get('mode', 'in_person')
        preferred_date = request.POST.get('preferred_date', '')
        preferred_time = request.POST.get('preferred_time', '')
        description = request.POST.get('description', '').strip()
        if not preferred_date or not preferred_time:
            error = 'Please select a preferred date and time.'
        else:
            AppointmentRequest.objects.create(
                student=request.user,
                topic=topic,
                mode=mode,
                preferred_date=preferred_date,
                preferred_time=preferred_time,
                description=description,
            )
            success = 'Your appointment request has been submitted! Admin will confirm it soon.'

    appointments = AppointmentRequest.objects.filter(student=request.user)
    return render(request, 'book_appointment.html', {
        'appointments': appointments,
        'error': error,
        'success': success,
        'mode_choices': AppointmentRequest.MODE_CHOICES,
        'topic_choices': AppointmentRequest.TOPIC_CHOICES,
    })


@login_required(login_url='/student-login/')
@require_POST
def cancel_appointment(request, appt_id):
    appt = get_object_or_404(AppointmentRequest, id=appt_id, student=request.user)
    if appt.status == 'pending':
        appt.status = 'cancelled'
        appt.save()
    return redirect('book_appointment')