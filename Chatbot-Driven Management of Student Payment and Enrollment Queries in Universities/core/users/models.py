from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('admin', 'Admin'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    phone = models.CharField(max_length=20, blank=True, null=True)
    student_id = models.CharField(max_length=30, blank=True, null=True, unique=True,
                                  help_text="University student ID (e.g. STU2024001)")
    program = models.CharField(max_length=100, blank=True, null=True,
                               help_text="e.g. B.Sc Software Engineering")


class FAQ(models.Model):
    intent = models.CharField(max_length=100)
    question = models.TextField()
    answer = models.TextField()
    keywords = models.CharField(max_length=255, blank=True, null=True,
                                help_text="Comma separated keywords")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return self.intent


class ChatLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_logs')
    message = models.TextField()
    response = models.TextField()
    confidence = models.FloatField(default=0.0)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username} — {self.timestamp:%Y-%m-%d %H:%M}"


class Feedback(models.Model):
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feedbacks')
    chat_log = models.OneToOneField(ChatLog, on_delete=models.CASCADE,
                                    related_name='feedback', null=True, blank=True)
    rating = models.IntegerField(choices=RATING_CHOICES, default=5)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} — {self.rating}★"


# =============================================
# FEE MANAGEMENT
# =============================================
class FeeRecord(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('partial', 'Partially Paid'),
        ('waived', 'Waived'),
    ]
    FEE_TYPE_CHOICES = [
        ('tuition', 'Tuition Fee'),
        ('exam', 'Exam Fee'),
        ('library', 'Library Fee'),
        ('transport', 'Transport Fee'),
        ('hostel', 'Hostel Fee'),
        ('other', 'Other'),
    ]
    student = models.ForeignKey(User, on_delete=models.CASCADE,
                                related_name='fee_records',
                                limit_choices_to={'role': 'student'})
    fee_type = models.CharField(max_length=20, choices=FEE_TYPE_CHOICES, default='tuition')
    description = models.CharField(max_length=200)
    amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    due_date = models.DateField()
    semester = models.CharField(max_length=30, blank=True, help_text="e.g. Sem 1 2024")
    academic_year = models.CharField(max_length=10, blank=True, help_text="e.g. 2024-25")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    payment_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_date']

    @property
    def balance(self):
        return self.amount_due - self.amount_paid

    def __str__(self):
        return f"{self.student.username} — {self.description} ({self.status})"


# =============================================
# ENROLLMENT MANAGEMENT
# =============================================
class EnrollmentRecord(models.Model):
    STATUS_CHOICES = [
        ('enrolled', 'Enrolled'),
        ('pending', 'Pending Approval'),
        ('dropped', 'Dropped'),
        ('completed', 'Completed'),
        ('suspended', 'Suspended'),
    ]
    student = models.ForeignKey(User, on_delete=models.CASCADE,
                                related_name='enrollment_records',
                                limit_choices_to={'role': 'student'})
    program = models.CharField(max_length=150, help_text="e.g. B.Sc Software Engineering")
    course_name = models.CharField(max_length=150, blank=True)
    semester = models.CharField(max_length=30, help_text="e.g. Semester 1")
    academic_year = models.CharField(max_length=10, help_text="e.g. 2024-25")
    enrollment_date = models.DateField()
    enrollment_deadline = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.username} — {self.program} ({self.semester})"


# =============================================
# APPOINTMENT BOOKING
# =============================================
class AppointmentRequest(models.Model):
    MODE_CHOICES = [
        ('in_person', 'In-Person Meeting'),
        ('chat', 'Chat / Messaging'),
        ('call', 'Phone Call'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
        ('rescheduled', 'Rescheduled'),
    ]
    TOPIC_CHOICES = [
        ('fee_query', 'Fee / Payment Query'),
        ('enrollment_query', 'Enrollment Query'),
        ('academic_issue', 'Academic Issue'),
        ('scholarship', 'Scholarship'),
        ('general', 'General Support'),
        ('other', 'Other'),
    ]
    student = models.ForeignKey(User, on_delete=models.CASCADE,
                                related_name='appointments',
                                limit_choices_to={'role': 'student'})
    topic = models.CharField(max_length=20, choices=TOPIC_CHOICES, default='general')
    mode = models.CharField(max_length=15, choices=MODE_CHOICES, default='in_person')
    preferred_date = models.DateField()
    preferred_time = models.TimeField()
    description = models.TextField(blank=True,
                                   help_text="Describe what you need help with")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True,
                                   help_text="Admin reply / confirmation notes")
    confirmed_date = models.DateField(null=True, blank=True)
    confirmed_time = models.TimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.username} — {self.get_topic_display()} ({self.status})"
