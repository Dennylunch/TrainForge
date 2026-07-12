from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("registration/signup/", views.signup, name="signup"),
    path("all_clients/", views.all_clients, name="all_clients"),
    path("all_clients/delete/<int:pk>/", views.delete_client, name="delete_client"),


    path("add_client/", views.add_client, name="add_client"),
    path("add_client/edit/<int:pk>/", views.edit_client, name="edit_client"),

    path("appointment/<int:pk>/", views.appointment, name="appointment"),
    path("appointment/edit/<int:pk>/", views.edit_appointment, name="edit_appointment"),

    path("customize_plan/<int:pk>/", views.customize_plan, name="customize_plan"),
    
    path("exercise_item/", views.exercise_item, name="exercise_item"),
    path("exercise_item/edit/<int:pk>/", views.edit_exercise_item, name="edit_exercise_item"),
    path("exercise_item/delete/<int:pk>/", views.delete_exercise_item, name="delete_exercise_item"),

    path("schedule/", views.schedule, name="schedule"),
    path("schedule/appointments/<int:pk>/archive/", views.archive_appointment, name="archive_appointment"),

    path("suggest_ai_note/<int:client_id>/", views.suggest_ai_note, name="suggest_ai_note"),
    path("select_ai_note/<int:client_id>/", views.select_ai_note, name="select_ai_note"),

    path("suggest_ai_plan_customization/<int:client_id>/", views.suggest_ai_plan_customization, name="suggest_ai_plan_customization"),
]


