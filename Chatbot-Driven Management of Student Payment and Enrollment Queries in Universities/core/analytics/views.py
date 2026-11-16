from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Avg, Count
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from users.models import FAQ, ChatLog, Feedback
from chatbot.models import ChatSession, ChatMessage
from notifications.models import Notification
import json
import os
from django.conf import settings

User = get_user_model()

FAQ_JSON_PATH = os.path.join(settings.BASE_DIR, 'knowledge_base', 'faq.json')

def _sync_faq_json():
    """Helper to dump all FAQ objects into faq.json for the Chatbot NLP engine"""
    import re
    faq_data = {}
    for faq in FAQ.objects.all():
        # Build keywords from both the intent and the actual question text
        combined_text = f"{faq.intent.replace('_', ' ')} {faq.question}"
        # Remove punctuation and split
        clean_text = re.sub(r'[^\w\s]', '', combined_text).lower()
        keys = clean_text.split()
        
        # Filter out common stop words
        stop_words = {'a', 'an', 'the', 'is', 'are', 'what', 'how', 'when', 'why', 'where', 'to', 'do', 'of', 'in', 'for', 'on', 'with'}
        generated_keywords = [kw for kw in keys if kw not in stop_words and len(kw) > 1]
        
        # Pull explicit custom keywords chosen by the admin
        explicit_keys = [k.strip().lower() for k in (faq.keywords or '').split(',') if k.strip()]
        
        # Combine them safely, avoiding duplicates
        keywords = list(set(generated_keywords + explicit_keys))
        
        faq_data[faq.intent] = {
            "keywords": keywords,
            "response": faq.answer
        }
    
    os.makedirs(os.path.dirname(FAQ_JSON_PATH), exist_ok=True)
    with open(FAQ_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(faq_data, f, indent=2)


def admin_required(view_func):
    """Decorator: only allow users with role == 'admin'."""
    @login_required(login_url='/admin-login/')
    def wrapper(request, *args, **kwargs):
        if request.user.role != 'admin' and not request.user.is_superuser:
            return redirect('admin_login')
        return view_func(request, *args, **kwargs)
    return wrapper


# ============================
# A6: ANALYTICS DASHBOARD
# ============================
@admin_required
def admin_dashboard(request):
    total_students = User.objects.filter(role='student').count()
    total_sessions = ChatLog.objects.values('user').distinct().count()
    total_messages = ChatLog.objects.count()
    avg_rating = Feedback.objects.aggregate(avg=Avg('rating'))['avg'] or 0

    # Most asked intents (from ChatLog messages grouped roughly)
    recent_logs = ChatLog.objects.select_related('user').order_by('-timestamp')[:20]

    ctx = {
        'total_students': total_students,
        'total_sessions': total_sessions,
        'total_messages': total_messages,
        'avg_rating': round(avg_rating, 1),
        'recent_logs': recent_logs,
    }
    return render(request, 'admin_dashboard.html', ctx)


# ============================
# A2: USER MANAGEMENT
# ============================
@admin_required
def admin_users(request):
    students = User.objects.filter(role='student').order_by('-date_joined')
    return render(request, 'admin_users.html', {'students': students})


@admin_required
@require_POST
def admin_delete_user(request, user_id):
    student = get_object_or_404(User, id=user_id, role='student')
    student.delete()
    return redirect('admin_users')


@admin_required
@require_POST
def admin_toggle_user(request, user_id):
    student = get_object_or_404(User, id=user_id, role='student')
    student.is_active = not student.is_active
    student.save()
    return redirect('admin_users')


# ============================
# A3: FAQ / CONTENT MANAGEMENT
# ============================
@admin_required
def admin_faqs(request):
    faqs = FAQ.objects.all().order_by('intent')
    return render(request, 'admin_faqs.html', {'faqs': faqs})


@admin_required
def admin_faq_add(request):
    error = ''
    if request.method == 'POST':
        intent = request.POST.get('intent', '').strip()
        question = request.POST.get('question', '').strip()
        answer = request.POST.get('answer', '').strip()
        keywords = request.POST.get('keywords', '').strip()
        if not intent or not question or not answer:
            error = 'All fields (Intent, Question, Answer) are required.'
        else:
            FAQ.objects.create(intent=intent, question=question, answer=answer, keywords=keywords)
            _sync_faq_json()
            return redirect('admin_faqs')
    return render(request, 'admin_faq_form.html', {'error': error, 'action': 'Add'})


@admin_required
def admin_faq_edit(request, faq_id):
    faq = get_object_or_404(FAQ, id=faq_id)
    error = ''
    if request.method == 'POST':
        faq.intent = request.POST.get('intent', '').strip()
        faq.question = request.POST.get('question', '').strip()
        faq.answer = request.POST.get('answer', '').strip()
        faq.keywords = request.POST.get('keywords', '').strip()
        if not faq.intent or not faq.question or not faq.answer:
            error = 'All fields (Intent, Question, Answer) are required.'
        else:
            faq.save()
            _sync_faq_json()
            return redirect('admin_faqs')
    return render(request, 'admin_faq_form.html', {'faq': faq, 'error': error, 'action': 'Edit'})


@admin_required
@require_POST
def admin_faq_delete(request, faq_id):
    faq = get_object_or_404(FAQ, id=faq_id)
    faq.delete()
    _sync_faq_json()
    return redirect('admin_faqs')


# ============================
# A4: MONITOR CHAT SESSIONS
# ============================
@admin_required
def admin_chatlogs(request):
    search = request.GET.get('q', '').strip()
    logs = ChatLog.objects.select_related('user').order_by('-timestamp')
    if search:
        logs = logs.filter(
            user__username__icontains=search
        ) | logs.filter(message__icontains=search)
    return render(request, 'admin_chatlogs.html', {'logs': logs, 'search': search})


# ============================
# A5: FEEDBACK REVIEW
# ============================
@admin_required
def admin_feedback(request):
    feedbacks = Feedback.objects.select_related('user', 'chat_log').order_by('-created_at')
    avg = feedbacks.aggregate(avg=Avg('rating'))['avg'] or 0
    return render(request, 'admin_feedback.html', {
        'feedbacks': feedbacks,
        'avg_rating': round(avg, 1)
    })


# ============================
# NOTIFICATIONS MANAGEMENT (admin side)
# ============================
@admin_required
def admin_notifications(request):
    error = ''
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        message = request.POST.get('message', '').strip()
        notif_type = request.POST.get('notif_type', 'general')
        # Broadcast to all students (user=None)
        if not title or not message:
            error = 'Title and message are required.'
        else:
            Notification.objects.create(
                user=None,
                title=title,
                message=message,
                notif_type=notif_type
            )
            return redirect('admin_notifications')

    notifications = Notification.objects.order_by('-created_at')
    return render(request, 'admin_notifications.html', {
        'notifications': notifications,
        'error': error
    })


@admin_required
@require_POST
def admin_notification_delete(request, notif_id):
    notif = get_object_or_404(Notification, id=notif_id)
    notif.delete()
    return redirect('admin_notifications')


# ============================
# A2 ADD: ADD STUDENT (admin creates student account)
# ============================
@admin_required
def admin_add_user(request):
    error = ''
    success = ''
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()

        if not name or not username or not email or not password:
            error = 'All fields are required.'
        elif User.objects.filter(username=username).exists():
            error = 'Username already taken.'
        elif User.objects.filter(email=email).exists():
            error = 'Email already registered.'
        else:
            User.objects.create_user(
                username=username, password=password,
                email=email, first_name=name, role='student'
            )
            success = f'Student "{username}" created successfully!'
    return render(request, 'admin_add_user.html', {'error': error, 'success': success})


# ============================
# A6 ANALYTICS & REPORTING  (charts + CSV export)
# ============================
@admin_required
def admin_analytics(request):
    from django.utils import timezone
    from datetime import timedelta

    # Daily messages – last 14 days
    today = timezone.now().date()
    days = [(today - timedelta(days=i)) for i in range(13, -1, -1)]
    daily_counts = []
    for d in days:
        c = ChatLog.objects.filter(timestamp__date=d).count()
        daily_counts.append(c)
    day_labels = [d.strftime('%b %d') for d in days]

    # Top 10 most asked messages (naive grouping by message text)
    from django.db.models import Count
    top_questions = (
        ChatLog.objects.values('message')
        .annotate(cnt=Count('id'))
        .order_by('-cnt')[:10]
    )

    # Rating distribution
    rating_dist = {}
    for i in range(1, 6):
        rating_dist[str(i)] = Feedback.objects.filter(rating=i).count()

    total_students = User.objects.filter(role='student').count()
    total_messages = ChatLog.objects.count()
    avg_rating = Feedback.objects.aggregate(avg=Avg('rating'))['avg'] or 0

    ctx = {
        'day_labels': day_labels,
        'daily_counts': daily_counts,
        'top_questions': top_questions,
        'rating_dist': rating_dist,
        'total_students': total_students,
        'total_messages': total_messages,
        'avg_rating': round(avg_rating, 1),
    }
    return render(request, 'admin_analytics.html', ctx)


@admin_required
def admin_export_csv(request):
    import csv
    from django.http import HttpResponse
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="chatbot_report.csv"'
    writer = csv.writer(response)
    writer.writerow(['#', 'Student', 'Question', 'Bot Response', 'Rating', 'Timestamp'])
    logs = ChatLog.objects.select_related('user').order_by('-timestamp')
    for i, log in enumerate(logs, 1):
        rating = ''
        try:
            rating = log.feedback.rating
        except Exception:
            pass
        writer.writerow([i, log.user.username, log.message, log.response, rating, log.timestamp.strftime('%Y-%m-%d %H:%M')])
    return response


# ============================
# A7 MODEL MANAGEMENT  (retrain / sync)
# ============================
@admin_required
def admin_model_management(request):
    success = ''
    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action == 'retrain':
            _sync_faq_json()
            success = 'Model knowledge base re-synced successfully! The chatbot now uses the latest FAQ data.'

    faq_count = FAQ.objects.count()
    log_count = ChatLog.objects.count()
    feedback_count = Feedback.objects.count()
    avg_rating = Feedback.objects.aggregate(avg=Avg('rating'))['avg'] or 0

    # Check if faq.json exists and get its modification time
    import datetime
    last_sync = 'Never'
    if os.path.exists(FAQ_JSON_PATH):
        mtime = os.path.getmtime(FAQ_JSON_PATH)
        last_sync = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')

    ctx = {
        'faq_count': faq_count,
        'log_count': log_count,
        'feedback_count': feedback_count,
        'avg_rating': round(avg_rating, 1),
        'last_sync': last_sync,
        'success': success,
    }
    return render(request, 'admin_model_management.html', ctx)


# ============================
# A8 SECURITY & BACKUP
# ============================
@admin_required
def admin_security(request):
    from django.http import HttpResponse
    from django.core import serializers as dj_serializers

    if request.method == 'POST' and request.POST.get('action') == 'backup':
        # Export all key models as JSON
        from users.models import User as UserModel, FAQ as FAQModel, ChatLog as ChatLogModel, Feedback as FeedbackModel
        from notifications.models import Notification as NotifModel
        all_objects = list(UserModel.objects.all()) + list(FAQModel.objects.all()) + \
                      list(ChatLogModel.objects.all()) + list(FeedbackModel.objects.all()) + \
                      list(NotifModel.objects.all())
        data = dj_serializers.serialize('json', all_objects, indent=2)
        response = HttpResponse(data, content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="chatbot_backup.json"'
        return response

    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    admin_count = User.objects.filter(role='admin').count()
    student_count = User.objects.filter(role='student').count()

    from django.utils import timezone
    from datetime import timedelta
    recent_students = User.objects.filter(
        role='student', date_joined__gte=timezone.now() - timedelta(days=7)
    ).order_by('-date_joined')[:5]

    ctx = {
        'total_users': total_users,
        'active_users': active_users,
        'admin_count': admin_count,
        'student_count': student_count,
        'recent_students': recent_students,
    }
    return render(request, 'admin_security.html', ctx)


# ============================
# A10 SYSTEM MAINTENANCE
# ============================
@admin_required
def admin_maintenance(request):
    import sys
    import django
    import platform

    total_faqs = FAQ.objects.count()
    total_logs = ChatLog.objects.count()
    total_feedback = Feedback.objects.count()
    total_students = User.objects.filter(role='student').count()
    total_notifications = Notification.objects.count()

    ctx = {
        'python_version': sys.version.split()[0],
        'django_version': django.__version__,
        'os_info': platform.system() + ' ' + platform.release(),
        'db_engine': 'MySQL',
        'total_faqs': total_faqs,
        'total_logs': total_logs,
        'total_feedback': total_feedback,
        'total_students': total_students,
        'total_notifications': total_notifications,
        'chatbot_status': 'Online',
    }
    return render(request, 'admin_maintenance.html', ctx)


# ============================
# FEE MANAGEMENT (Admin)
# ============================
@admin_required
def admin_fees(request):
    from users.models import FeeRecord
    search = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')
    fees = FeeRecord.objects.select_related('student').order_by('due_date')
    if search:
        fees = fees.filter(
            student__username__icontains=search
        ) | FeeRecord.objects.select_related('student').filter(
            description__icontains=search
        )
    if status_filter:
        fees = fees.filter(status=status_filter)

    total_due = sum(f.amount_due for f in fees)
    total_paid_sum = sum(f.amount_paid for f in fees)
    overdue_count = FeeRecord.objects.filter(status='overdue').count()
    pending_count = FeeRecord.objects.filter(status='pending').count()

    ctx = {
        'fees': fees,
        'search': search,
        'status_filter': status_filter,
        'total_due': total_due,
        'total_paid_sum': total_paid_sum,
        'overdue_count': overdue_count,
        'pending_count': pending_count,
        'students': User.objects.filter(role='student').order_by('username'),
    }
    return render(request, 'admin_fees.html', ctx)


@admin_required
def admin_fee_add(request):
    from users.models import FeeRecord
    error = ''
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        fee_type = request.POST.get('fee_type', 'tuition')
        description = request.POST.get('description', '').strip()
        amount_due = request.POST.get('amount_due', 0)
        due_date = request.POST.get('due_date', '')
        semester = request.POST.get('semester', '').strip()
        academic_year = request.POST.get('academic_year', '').strip()
        notes = request.POST.get('notes', '').strip()

        if not student_id or not description or not due_date or not amount_due:
            error = 'Student, description, amount, and due date are required.'
        else:
            student = get_object_or_404(User, id=student_id, role='student')
            FeeRecord.objects.create(
                student=student, fee_type=fee_type, description=description,
                amount_due=amount_due, due_date=due_date,
                semester=semester, academic_year=academic_year, notes=notes
            )
            # Auto-create notification for student
            Notification.objects.create(
                user=student,
                title=f'New Fee Record: {description}',
                message=f'A new fee of ₹{amount_due} has been added for {description}. Due date: {due_date}.',
                notif_type='tuition'
            )
            return redirect('admin_fees')

    students = User.objects.filter(role='student').order_by('username')
    fee_types = FeeRecord.FEE_TYPE_CHOICES
    return render(request, 'admin_fee_form.html', {
        'error': error, 'students': students, 'fee_types': fee_types, 'action': 'Add'
    })


@admin_required
def admin_fee_edit(request, fee_id):
    from users.models import FeeRecord
    fee = get_object_or_404(FeeRecord, id=fee_id)
    error = ''
    if request.method == 'POST':
        fee.fee_type = request.POST.get('fee_type', fee.fee_type)
        fee.description = request.POST.get('description', fee.description).strip()
        fee.amount_due = request.POST.get('amount_due', fee.amount_due)
        fee.amount_paid = request.POST.get('amount_paid', fee.amount_paid)
        fee.due_date = request.POST.get('due_date', fee.due_date)
        fee.semester = request.POST.get('semester', fee.semester).strip()
        fee.academic_year = request.POST.get('academic_year', fee.academic_year).strip()
        fee.status = request.POST.get('status', fee.status)
        fee.notes = request.POST.get('notes', fee.notes).strip()
        payment_date = request.POST.get('payment_date', '')
        fee.payment_date = payment_date if payment_date else None
        if not fee.description or not fee.due_date:
            error = 'Description and due date are required.'
        else:
            fee.save()
            return redirect('admin_fees')
    students = User.objects.filter(role='student').order_by('username')
    fee_types = FeeRecord.FEE_TYPE_CHOICES
    status_choices = FeeRecord.STATUS_CHOICES
    return render(request, 'admin_fee_form.html', {
        'fee': fee, 'error': error, 'students': students,
        'fee_types': fee_types, 'status_choices': status_choices, 'action': 'Edit'
    })


@admin_required
@require_POST
def admin_fee_delete(request, fee_id):
    from users.models import FeeRecord
    fee = get_object_or_404(FeeRecord, id=fee_id)
    fee.delete()
    return redirect('admin_fees')


@admin_required
@require_POST
def admin_fee_mark_paid(request, fee_id):
    from users.models import FeeRecord
    from django.utils import timezone
    fee = get_object_or_404(FeeRecord, id=fee_id)
    fee.status = 'paid'
    fee.amount_paid = fee.amount_due
    fee.payment_date = timezone.now().date()
    fee.save()
    Notification.objects.create(
        user=fee.student,
        title='Fee Payment Confirmed ✅',
        message=f'Your payment of ₹{fee.amount_due} for "{fee.description}" has been confirmed. Thank you!',
        notif_type='tuition'
    )
    return redirect('admin_fees')


@admin_required
@require_POST
def admin_fee_alert(request):
    """Send fee deadline alerts to students with pending/overdue fees."""
    from users.models import FeeRecord
    target = request.POST.get('target', 'all')  # 'all', 'overdue', 'pending'
    custom_msg = request.POST.get('message', '').strip()

    if target == 'overdue':
        fees = FeeRecord.objects.filter(status='overdue').select_related('student')
    elif target == 'pending':
        fees = FeeRecord.objects.filter(status='pending').select_related('student')
    else:
        fees = FeeRecord.objects.filter(status__in=['pending', 'overdue']).select_related('student')

    seen = set()
    count = 0
    for fee in fees:
        if fee.student_id not in seen:
            seen.add(fee.student_id)
            msg = custom_msg or f'You have an outstanding fee of ₹{fee.amount_due} for "{fee.description}" due on {fee.due_date}. Please pay on time.'
            Notification.objects.create(
                user=fee.student,
                title='⚠️ Fee Deadline Reminder',
                message=msg,
                notif_type='tuition'
            )
            count += 1
    return JsonResponse({'status': 'ok', 'count': count, 'message': f'Alerts sent to {count} student(s).'})


# ============================
# ENROLLMENT MANAGEMENT (Admin)
# ============================
@admin_required
def admin_enrollments(request):
    from users.models import EnrollmentRecord
    search = request.GET.get('q', '').strip()
    enrollments = EnrollmentRecord.objects.select_related('student').order_by('-created_at')
    if search:
        enrollments = enrollments.filter(
            student__username__icontains=search
        ) | EnrollmentRecord.objects.select_related('student').filter(
            program__icontains=search
        )

    ctx = {
        'enrollments': enrollments,
        'search': search,
        'students': User.objects.filter(role='student').order_by('username'),
    }
    return render(request, 'admin_enrollments.html', ctx)


@admin_required
def admin_enrollment_add(request):
    from users.models import EnrollmentRecord
    error = ''
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        program = request.POST.get('program', '').strip()
        course_name = request.POST.get('course_name', '').strip()
        semester = request.POST.get('semester', '').strip()
        academic_year = request.POST.get('academic_year', '').strip()
        enrollment_date = request.POST.get('enrollment_date', '')
        enrollment_deadline = request.POST.get('enrollment_deadline', '') or None
        status = request.POST.get('status', 'pending')
        notes = request.POST.get('notes', '').strip()

        if not student_id or not program or not semester or not enrollment_date:
            error = 'Student, program, semester, and enrollment date are required.'
        else:
            student = get_object_or_404(User, id=student_id, role='student')
            EnrollmentRecord.objects.create(
                student=student, program=program, course_name=course_name,
                semester=semester, academic_year=academic_year,
                enrollment_date=enrollment_date, enrollment_deadline=enrollment_deadline,
                status=status, notes=notes
            )
            Notification.objects.create(
                user=student,
                title=f'Enrollment Update: {program}',
                message=f'Your enrollment for {program} ({semester}) has been updated. Status: {status.upper()}.',
                notif_type='enrollment'
            )
            return redirect('admin_enrollments')

    students = User.objects.filter(role='student').order_by('username')
    from users.models import EnrollmentRecord as ER
    status_choices = ER.STATUS_CHOICES
    return render(request, 'admin_enrollment_form.html', {
        'error': error, 'students': students, 'status_choices': status_choices, 'action': 'Add'
    })


@admin_required
def admin_enrollment_edit(request, enroll_id):
    from users.models import EnrollmentRecord
    enrollment = get_object_or_404(EnrollmentRecord, id=enroll_id)
    error = ''
    if request.method == 'POST':
        enrollment.program = request.POST.get('program', enrollment.program).strip()
        enrollment.course_name = request.POST.get('course_name', enrollment.course_name).strip()
        enrollment.semester = request.POST.get('semester', enrollment.semester).strip()
        enrollment.academic_year = request.POST.get('academic_year', enrollment.academic_year).strip()
        enrollment.enrollment_date = request.POST.get('enrollment_date', enrollment.enrollment_date)
        deadline = request.POST.get('enrollment_deadline', '')
        enrollment.enrollment_deadline = deadline if deadline else None
        enrollment.status = request.POST.get('status', enrollment.status)
        enrollment.notes = request.POST.get('notes', enrollment.notes).strip()
        if not enrollment.program or not enrollment.semester:
            error = 'Program and semester are required.'
        else:
            enrollment.save()
            Notification.objects.create(
                user=enrollment.student,
                title='Enrollment Record Updated',
                message=f'Your enrollment for {enrollment.program} ({enrollment.semester}) has been updated. Status: {enrollment.status.upper()}.',
                notif_type='enrollment'
            )
            return redirect('admin_enrollments')
    students = User.objects.filter(role='student').order_by('username')
    status_choices = EnrollmentRecord.STATUS_CHOICES
    return render(request, 'admin_enrollment_form.html', {
        'enrollment': enrollment, 'error': error, 'students': students,
        'status_choices': status_choices, 'action': 'Edit'
    })


@admin_required
@require_POST
def admin_enrollment_delete(request, enroll_id):
    from users.models import EnrollmentRecord
    enrollment = get_object_or_404(EnrollmentRecord, id=enroll_id)
    enrollment.delete()
    return redirect('admin_enrollments')


@admin_required
@require_POST
def admin_enrollment_alert(request):
    """Send enrollment deadline reminders."""
    from users.models import EnrollmentRecord
    from django.utils import timezone
    custom_msg = request.POST.get('message', '').strip()
    enrollments = EnrollmentRecord.objects.filter(
        status__in=['pending', 'enrolled']
    ).select_related('student')

    seen = set()
    count = 0
    for e in enrollments:
        if e.student_id not in seen:
            seen.add(e.student_id)
            deadline_info = f' Deadline: {e.enrollment_deadline}.' if e.enrollment_deadline else ''
            msg = custom_msg or f'Reminder: Your enrollment for {e.program} ({e.semester}) is {e.status}.{deadline_info}'
            Notification.objects.create(
                user=e.student,
                title='📋 Enrollment Date Reminder',
                message=msg,
                notif_type='enrollment'
            )
            count += 1
    return JsonResponse({'status': 'ok', 'count': count, 'message': f'Alerts sent to {count} student(s).'})


# ============================
# APPOINTMENT MANAGEMENT (Admin)
# ============================
@admin_required
def admin_appointments(request):
    from users.models import AppointmentRequest
    status_filter = request.GET.get('status', '')
    search = request.GET.get('q', '').strip()
    appts = AppointmentRequest.objects.select_related('student').order_by('-created_at')
    if status_filter:
        appts = appts.filter(status=status_filter)
    if search:
        appts = appts.filter(student__username__icontains=search)

    pending_count = AppointmentRequest.objects.filter(status='pending').count()
    ctx = {
        'appointments': appts,
        'status_filter': status_filter,
        'search': search,
        'pending_count': pending_count,
        'status_choices': AppointmentRequest.STATUS_CHOICES,
    }
    return render(request, 'admin_appointments.html', ctx)


@admin_required
def admin_appointment_action(request, appt_id):
    from users.models import AppointmentRequest
    appt = get_object_or_404(AppointmentRequest, id=appt_id)
    error = ''
    if request.method == 'POST':
        action = request.POST.get('action', '')
        admin_notes = request.POST.get('admin_notes', '').strip()
        confirmed_date = request.POST.get('confirmed_date', '') or None
        confirmed_time = request.POST.get('confirmed_time', '') or None

        if action == 'confirm':
            appt.status = 'confirmed'
            appt.admin_notes = admin_notes
            appt.confirmed_date = confirmed_date
            appt.confirmed_time = confirmed_time
            appt.save()
            Notification.objects.create(
                user=appt.student,
                title='✅ Appointment Confirmed',
                message=f'Your {appt.get_mode_display()} appointment for "{appt.get_topic_display()}" has been confirmed. Date: {confirmed_date or appt.preferred_date} at {confirmed_time or appt.preferred_time}. {admin_notes}',
                notif_type='general'
            )
        elif action == 'cancel':
            appt.status = 'cancelled'
            appt.admin_notes = admin_notes
            appt.save()
            Notification.objects.create(
                user=appt.student,
                title='❌ Appointment Cancelled',
                message=f'Your appointment for "{appt.get_topic_display()}" has been cancelled. Reason: {admin_notes or "No reason provided."}',
                notif_type='general'
            )
        elif action == 'complete':
            appt.status = 'completed'
            appt.admin_notes = admin_notes
            appt.save()
            Notification.objects.create(
                user=appt.student,
                title='✔️ Appointment Completed',
                message=f'Your appointment for "{appt.get_topic_display()}" has been marked as completed. {admin_notes}',
                notif_type='general'
            )
        return redirect('admin_appointments')

    return render(request, 'admin_appointment_detail.html', {'appt': appt, 'error': error})
