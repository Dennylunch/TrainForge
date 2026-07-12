from django.contrib.auth.models import User
from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone




class UserDetail(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE) 
    role = models.CharField(max_length=100, default="trainer")
    is_term_accepted = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f"{self.role}: {self.user.first_name} {self.user.last_name}"


class Client(models.Model):
    user = models.ForeignKey(UserDetail, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    email = models.EmailField(max_length=100)
    current_weight = models.IntegerField(blank=True, null=True)
    target_weight = models.IntegerField(blank=True, null=True)
    goal = models.CharField(max_length=100)
    goal_description = models.CharField(max_length=100, blank=True)
    preferred_app_time_notes = models.CharField(max_length=100, blank=True, null=True)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    @property
    def age(self):
        if self.date_of_birth:
            current_year = timezone.now().year
            current_year -= self.date_of_birth.year
            return current_year
        else:
            return "None"
    
    @property
    def gender_label(self):
        if self.gender == 'Male':
            return 'bi bi-gender-male'
        elif self.gender == 'Female':
            return 'bi bi-gender-female'


    def __str__(self):
        return f"Client: {self.first_name} {self.last_name}"


class Subscription(models.Model):
    user = models.OneToOneField(UserDetail, on_delete=models.CASCADE) 
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return f"Subscription: {self.user.user.first_name} {self.user.user.last_name}"


class Exercise(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"Exercise: {self.name}"


class UserExercise(models.Model):
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, blank=True, null=True)
    user = models.ForeignKey(UserDetail, on_delete=models.CASCADE) 
    exercise_name_copy = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    is_archived = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.user.first_name} {self.user.user.last_name}'s exercise item: {self.exercise_name_copy}"


class ClientPlan(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    is_archived = models.BooleanField(default=False)
    weekly_notes = models.TextField(blank=False, default="Click the AI suggestion button to create a personalised weekly plan summary for this client.")

    @property
    def status(self):
        if timezone.now().date() < self.start_date and timezone.now().date() < self.end_date:
            return "NOT START"
        elif timezone.now().date() >= self.start_date and timezone.now().date() <= self.end_date:
            return "RUN"
        elif timezone.now().date() > self.start_date and timezone.now().date() > self.end_date:
            return "COMPLETED"
    
    @property
    def overall_progress(self):
        if self.end_date <= self.start_date:
            return 0
        else:
            total = (self.end_date - self.start_date).days + 1
            if (timezone.now().date() - self.start_date).days >= total:
                return 100
            elif (timezone.now().date() - self.start_date).days < 0:
                return 0
            else:
                days = ((timezone.now().date() - self.start_date).days + 1) / total
                return int(days*100)

    def __str__(self):
        return f"{self.client.first_name} {self.client.last_name}'s exercise plan"


class PlanExercise(models.Model):
    client_plan = models.ForeignKey(ClientPlan, on_delete=models.CASCADE)
    user_exercise = models.ForeignKey(UserExercise, on_delete=models.CASCADE)
    frequency = models.CharField(max_length=100, blank=True, null=True)
    repetition = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(max_length=500, blank=True, null=True)
    is_archived = models.BooleanField(default=False)
    progress = models.IntegerField(validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ])

    def __str__(self):
        return f"{self.client_plan.client.first_name} {self.client_plan.client.last_name}'s plan: {self.user_exercise.exercise_name_copy}"


class Appointment(models.Model):
    # constants
    ARCHIVE_SOURCE_AUTO = "auto"
    ARCHIVE_SOURCE_MANUAL = "manual"
    ARCHIVE_SOURCE_LEGACY = "legacy"
    ARCHIVE_SOURCE_CHOICES = [
        (ARCHIVE_SOURCE_AUTO, "Automatically archived"),
        (ARCHIVE_SOURCE_MANUAL, "Manually archived"),
        (ARCHIVE_SOURCE_LEGACY, "Legacy archived"),
    ]


    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    date = models.DateField(blank=True, null=True)
    starting_time = models.TimeField(blank=True, null=True)
    purpose = models.TextField(max_length=100, blank=True)
    is_archived = models.BooleanField(default=False)
    archive_source = models.CharField(max_length=10, choices=ARCHIVE_SOURCE_CHOICES, blank=True, null=True)
    status = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    @property
    def latest_app_t(self):
        if not self.is_archived:
            return f"{self.date} {self.starting_time} (Duration: 1 hr)"
        else:
            return "None"


    def __str__(self):
        return f"Appointment: {self.client.user.user.first_name} {self.client.user.user.last_name} & {self.client.first_name} {self.client.last_name} at {self.date}"


