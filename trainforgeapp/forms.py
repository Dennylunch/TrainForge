from django import forms
from .models import Client, ClientPlan, Appointment, UserExercise

class ClientDetailForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['gender', 'first_name', 'last_name', 'date_of_birth', 'email', 'current_weight', 'target_weight', 'goal', 'goal_description']

class ClientPlanForm(forms.ModelForm):
    class Meta:
        model = ClientPlan
        fields = ['start_date', 'end_date']

class AppClientDetailForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['preferred_app_time_notes']

class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['date', 'starting_time', 'purpose']
    

class UserExerciseForm(forms.ModelForm):
    class Meta:
        model = UserExercise
        fields = ["exercise_name_copy"]