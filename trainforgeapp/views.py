from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from .models import UserDetail, Client, Exercise, ClientPlan, PlanExercise, Appointment, Subscription, UserExercise
from django.contrib.auth.models import User #built-in User model
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
# We do not need separate login view, login view is built-in fxn from django.


from django.core.paginator import Paginator
from django.db.models import Q, Prefetch
from .forms import ClientDetailForm, ClientPlanForm, AppClientDetailForm, AppointmentForm, UserExerciseForm


from django.utils import timezone
from datetime import date, time, timedelta
from django.views.decorators.http import require_POST
# timezone: The current date and time of the default region
# timedelta: Perform addition or subtraction operations between dates or times
# time: A specific time of day


from typing import List
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from django.conf import settings
import markdown
from django.utils.safestring import mark_safe

class AINoteSuggestions(BaseModel):
    # This defines a list of strings
    suggestions: List[str] = Field(description="List of AI-generated weekly training notes alternatives")

class AIExercisePlanSuggestions(BaseModel):
    ex_p_sug: List[list[str]] = Field(description="1个nested list, 它内部的每一个'[]'都代表一个运动项目，内部'[]'中有四个数据, 分别为运动项目名称, frequency[纯正整数(datatype: int)], repetition(纯正整数(datatype: int), 以及description[文本、数字、特殊符号的组合(datatype: str)]")



def index(request):
    return render(request, "index.html")

def signup(request):
    if request.method == 'POST':
        fname = request.POST.get('userfn')
        lname = request.POST.get('userln')
        email = request.POST.get('user_email')
        pw = request.POST.get('user_pw')
        c_pw = request.POST.get('user_con_pw')
        terms = request.POST.get('terms_agree')

        if User.objects.filter(username=email).exists():
            messages.error(request, 'This email address already registered.')
            return render(request, 'registration/signup.html')
        
        if pw != c_pw:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'registration/signup.html')

        if not terms:
            messages.error(request, 'You must agree to the terms and conditions.')
            return render(request, 'registration/signup.html')
        
        user = User.objects.create_user(
            password=pw,
            is_superuser=0,
            username=email,
            first_name=fname,
            last_name=lname,
            email=email,
            is_staff=0,
            is_active=1,
        )

        user_detail = UserDetail.objects.create(
            user=user,
            role='trainer',
            is_term_accepted=True,
        )

        Subscription.objects.create(
            user=user_detail
        )

        # Initialize UserExercise
        exercise_item = Exercise.objects.all()
        for i in exercise_item:
            UserExercise.objects.create(
                exercise=i,
                user=user_detail,
                exercise_name_copy=i.name)
       
        return redirect('login')
        
    return render(request, "registration/signup.html")


def _archive_past_appointments(trainer, today_date=None):
    """Archive completed appointments while retaining their calendar history."""
    today_date = today_date or timezone.localdate()
    Appointment.objects.filter(
        client__user=trainer,
        client__is_archived=False,
        date__lt=today_date,
        is_archived=False,
    ).update(
        is_archived=True,
        archive_source=Appointment.ARCHIVE_SOURCE_AUTO,
    )


def _selected_week_start(raw_week, today_date=None):
    """Return the Monday for a supplied ISO date, falling back to this week."""
    today_date = today_date or timezone.localdate()
    selected_date = today_date
    if raw_week:
        try:
            selected_date = date.fromisoformat(raw_week)
        except ValueError:
            pass
    return selected_date - timedelta(days=selected_date.weekday())


@login_required
def all_clients(request):
    user_details = get_object_or_404(UserDetail, user=request.user, role='trainer')
    user_info = user_details.user
    today_date = timezone.localdate()

    _archive_past_appointments(user_details, today_date)

    clients = Client.objects.filter(user=user_details, is_archived=False)
    client_plans = ClientPlan.objects.filter(client__in=clients, is_archived=False) # 'a__in=b' is same as 'a in []'  
    
    user_exercises = UserExercise.objects.filter(user=user_details)
    plan_exercises = PlanExercise.objects.filter(client_plan__in=client_plans, user_exercise__in=user_exercises, is_archived=False) 
    
    # searching
    search_query = request.GET.get("search", "")
    if search_query:
        clients = clients.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )

    clients = list(clients.prefetch_related(
        Prefetch(
            "appointment_set",
            queryset=Appointment.objects.order_by("date", "starting_time", "pk"),
            to_attr="schedule_appointments",
        )
    ))
    for client in clients:
        appointments = client.schedule_appointments
        upcoming_appointments = [
            appointment for appointment in appointments
            if appointment.date and appointment.date >= today_date and not appointment.is_archived
        ]
        automatic_history = [
            appointment for appointment in appointments
            if appointment.date and appointment.date < today_date
            and appointment.archive_source == Appointment.ARCHIVE_SOURCE_AUTO
        ]
        client.latest_appointment = (
            upcoming_appointments[0]
            if upcoming_appointments
            else automatic_history[-1] if automatic_history else None
        )

    context = {
        "user_details": user_details,
        "user_info": user_info,
        "clients": clients,
        "client_plans": client_plans,
        "user_exercises": user_exercises,
        "plan_exercises": plan_exercises,
    }
    return render(request, "all_clients.html", context)



@login_required
def delete_client(request, pk):
    client_user = get_object_or_404(UserDetail, user=request.user, role='trainer')
    client = get_object_or_404(Client, pk=pk, user=client_user)
    client_plan = get_object_or_404(ClientPlan, client=client, is_archived=False)  # find 1 instance only
    plan_exercise = PlanExercise.objects.filter(client_plan=client_plan, is_archived=False) # find 1 more instances
    appointment = Appointment.objects.filter(client=client, is_archived=False)

    if request.method == "POST":
        for i in appointment:
            i.is_archived = True
            i.archive_source = Appointment.ARCHIVE_SOURCE_MANUAL
            i.save(update_fields=["is_archived", "archive_source"])
        for j in plan_exercise:
            j.is_archived = True
            j.save()
        client_plan.is_archived = True
        client_plan.save()
        client.is_archived = True
        client.save()

        messages.success(request, "The client have been deleted successfully.")
        return redirect("all_clients")
    
    return render(request, "client_delete.html", {"client": client})



@login_required
def add_client(request):
    client_user = get_object_or_404(UserDetail, user=request.user, role='trainer')
    all_exercise_items = UserExercise.objects.filter(user=client_user, is_archived=False)

    if request.method == "POST":
        client_detail_form = ClientDetailForm(request.POST)
        client_plan_form = ClientPlanForm(request.POST)
        preferred_exercise = request.POST.getlist("preferred_ex")

        if not preferred_exercise:
            messages.error(request, 'You must select at least 1 exercise you plan to do.')
        else:
            if client_detail_form.is_valid() and client_plan_form.is_valid():
                client_detail = client_detail_form.save(commit=False) # do not store in db for now
                client_detail.user = client_user
                client_detail.save()

                client_plan = client_plan_form.save(commit=False)
                client_plan.client = client_detail
                client_plan.save()

                for i in preferred_exercise:
                    user_exercise = get_object_or_404(UserExercise, user=client_user, exercise_name_copy=i)
                    PlanExercise.objects.create(
                        client_plan=client_plan,
                        user_exercise=user_exercise,
                        frequency='',
                        repetition='',
                        description='',
                        progress=0)
                
                messages.success(request, "Client details have been created successfully.")
                return redirect("customize_plan", pk=client_detail.pk)

    else:
        client_detail_form = ClientDetailForm()
        client_plan_form = ClientPlanForm()
    return render(request, "add_client.html", {"all_exercise_items":all_exercise_items, "client_detail_form": client_detail_form, "client_plan_form": client_plan_form})



@login_required
def edit_client(request, pk):
    client_user = get_object_or_404(UserDetail, user=request.user, role='trainer')
    client = get_object_or_404(Client, user=client_user, pk=pk)
    client_plan = get_object_or_404(ClientPlan, client=client, is_archived=False)

    if request.method == "POST":
        client_detail_form = ClientDetailForm(request.POST, instance=client)
        client_plan_form = ClientPlanForm(request.POST, instance=client_plan)

        if client_detail_form.is_valid() and client_plan_form.is_valid():
            client_detail_form.save()
            client_plan_form.save()
            messages.success(request, "Client details have been updated successfully.")
            return redirect("customize_plan", pk=client.pk)
    
    else:
        client_detail_form = ClientDetailForm(instance=client)
        client_plan_form = ClientPlanForm(instance=client_plan)

    return render(request, "add_client.html", {"client_detail_form": client_detail_form, "client_plan_form": client_plan_form, "client":client, "client_plan":client_plan })



@login_required
def customize_plan(request, pk): # create/update plan
    client_user = get_object_or_404(UserDetail, user=request.user, role='trainer')
    client = get_object_or_404(Client, pk=pk, user=client_user)
    client_plan = get_object_or_404(ClientPlan, client=client, is_archived=False)  # find 1 instance only
    plan_exercise = PlanExercise.objects.filter(client_plan=client_plan, is_archived=False) # find 1 more instances 

    if request.method == "POST":
        for i in plan_exercise:
            i.frequency = request.POST.get(f"frequency_{i.id}", "")
            i.repetition = request.POST.get(f"repetition_{i.id}", "")
            i.description = request.POST.get(f"description_{i.id}", "")
            i.progress = request.POST.get(f"progress_{i.id}", 0)
            i.save()

        messages.success(request, "Training Plan and Plan Exercise have been updated successfully.")
        return redirect("appointment", pk=client.pk)

    return render(request, "customize_plan.html", {"plan_exercise": plan_exercise, "client": client})



@login_required
def appointment(request, pk):
    client_user = get_object_or_404(UserDetail, user=request.user, role='trainer')
    client = get_object_or_404(Client, pk=pk, user=client_user)
    today_date = timezone.localdate()
    app_info = Appointment.objects.filter(client=client, is_archived=False, date__gte=today_date)

    if request.method == "POST":
        app_client_detail_form = AppClientDetailForm(request.POST, instance=client) # edit
        appointment_form = AppointmentForm(request.POST)

        if app_client_detail_form.is_valid() and appointment_form.is_valid():
            app_client_detail_form.save()
            messages.success(request, "The client's preferred appointment time have been created/updated successfully.")
            
            # determine whether there is a null/none value for start/end time in actual app
            time_slot_check = appointment_form.cleaned_data.get("starting_time")
            date_check = appointment_form.cleaned_data.get("date")

            if time_slot_check and date_check:
                if date_check < today_date:
                    messages.error(request, "Your appointment request has been declined because the appointment date can't be earlier than today's date.")

                elif not app_info:
                    app = appointment_form.save(commit=False) 
                    app.client = client
                    app.save()
                    messages.success(request, "Your appointment has been successfully scheduled.")
                else:
                    messages.error(request, "Your appointment request has been declined because each client is permitted only ONE active appointment.")

            return redirect("all_clients")
    
    else:
        app_client_detail_form = AppClientDetailForm(instance=client)
        appointment_form = AppointmentForm()
        
    return render(request, "appointment.html", {'client':client, 'app_client_detail_form':app_client_detail_form, 'appointment_form':appointment_form})



@login_required
def edit_appointment(request, pk):
    client_user = get_object_or_404(UserDetail, user=request.user, role='trainer')
    client = get_object_or_404(Client, user=client_user, pk=pk)
    today_date = timezone.localdate()
    app_info = Appointment.objects.filter(client=client, is_archived=False, date__gte=today_date)

    if request.method == "POST":
        app_client_detail_form = AppClientDetailForm(request.POST, instance=client) # edit
        appointment_form = AppointmentForm(request.POST)

        if app_client_detail_form.is_valid() and appointment_form.is_valid():
            app_client_detail_form.save()
            messages.success(request, "The client's preferred appointment time have been created/updated successfully.")
            
            # determine whether there is a null/none value for start/end time in actual app
            time_slot_check = appointment_form.cleaned_data.get("starting_time")
            date_check = appointment_form.cleaned_data.get("date")

            if time_slot_check and date_check:
                if date_check < today_date:
                    messages.error(request, "Your appointment request has been declined because the appointment date can't be earlier than today's date.")

                elif not app_info:
                    app = appointment_form.save(commit=False) 
                    app.client = client
                    app.save()
                    messages.success(request, "Your appointment has been successfully scheduled.")
                else:
                    messages.error(request, "Your appointment request has been declined because each client is permitted only ONE active appointment.")

            return redirect("all_clients")
    
    else:
        app_client_detail_form = AppClientDetailForm(instance=client)
        appointment_form = AppointmentForm()

    return render(request, "appointment.html", {'client':client, 'app_client_detail_form':app_client_detail_form, 'appointment_form':appointment_form})



@login_required
def exercise_item(request): # list and create the exercise items
    client_user = get_object_or_404(UserDetail, user=request.user, role='trainer')
    all_exercise_items = UserExercise.objects.filter(user=client_user, is_archived=False)
    if request.method == "POST":
        user_exercise_form = UserExerciseForm(request.POST)
        if user_exercise_form.is_valid():
            user_exercise = user_exercise_form.save(commit=False) 
            user_exercise.user = client_user
            user_exercise.save()

            messages.success(request, "The new exercise have been created successfully.")
            return redirect("exercise_item")
    
    else:
        user_exercise_form = UserExerciseForm()
    return render(request, "exercise_item.html", {'all_exercise_items':all_exercise_items, 'user_exercise_form':user_exercise_form})



@login_required
def edit_exercise_item(request, pk):
    client_user = get_object_or_404(UserDetail, user=request.user, role='trainer')
    exercise_item = get_object_or_404(UserExercise, pk=pk, user=client_user, is_archived=False)

    if request.method == "POST":
        user_exercise_form = UserExerciseForm(request.POST, instance=exercise_item)

        if user_exercise_form.is_valid():
            user_exercise_form.save()
            messages.success(request, "Your exercise item have been updated successfully.")
            return redirect("exercise_item")
    
    else:
        user_exercise_form = UserExerciseForm(instance=exercise_item)

    return render(request, "edit_exercise_item.html", {"user_exercise_form": user_exercise_form, "exercise_item":exercise_item})



@login_required
def delete_exercise_item(request, pk):
    client_user = get_object_or_404(UserDetail, user=request.user, role='trainer')
    exercise_item = get_object_or_404(UserExercise, pk=pk, user=client_user, is_archived=False)
    
    # Determine whether this item, to be deleted, is currently in use
    plan_exercise = PlanExercise.objects.filter(user_exercise=pk, is_archived=False)

    if request.method == "POST":

        if not plan_exercise:
            exercise_item.is_archived = True
            exercise_item.save()
            messages.success(request, "The exercise have been deleted successfully.")
        else:
            messages.error(request, "The deletion request was rejected")
            messages.error(request, "This exercise cannot be deleted because it has already been selected by a client or included in an active training plan.")
        return redirect("exercise_item")
    
    return render(request, "delete_exercise_item.html")



@login_required
def schedule(request):
    today_date = timezone.localdate()
    client_user = get_object_or_404(UserDetail, user=request.user, role='trainer')
    _archive_past_appointments(client_user, today_date)

    week_start = _selected_week_start(request.GET.get("week"), today_date)
    week_end = week_start + timedelta(days=6)
    current_week = [week_start + timedelta(days=offset) for offset in range(7)]
    time_slot = [(time(hour, 0), time(hour + 1, 0)) for hour in range(8, 20)]

    appointments = Appointment.objects.filter(
        client__user=client_user,
        client__is_archived=False,
        date__range=(week_start, week_end),
    ).filter(
        Q(date__gte=today_date, is_archived=False)
        | Q(date__lt=today_date, archive_source=Appointment.ARCHIVE_SOURCE_AUTO)
    ).select_related("client").order_by("date", "starting_time", "pk")

    return render(request, "schedule.html", {
        "appointments": appointments,
        "current_week": current_week,
        "time_slot": time_slot,
        "today": today_date,
        "selected_week_start": week_start,
        "previous_week_start": week_start - timedelta(days=7),
        "next_week_start": week_start + timedelta(days=7),
    })


@login_required
@require_POST
def archive_appointment(request, pk):
    today_date = timezone.localdate()
    trainer = get_object_or_404(UserDetail, user=request.user, role="trainer")
    appointment = get_object_or_404(
        Appointment,
        pk=pk,
        client__user=trainer,
        client__is_archived=False,
        is_archived=False,
        date__gte=today_date,
    )
    appointment.is_archived = True
    appointment.archive_source = Appointment.ARCHIVE_SOURCE_MANUAL
    appointment.save(update_fields=["is_archived", "archive_source"])

    messages.success(request, "The appointment has been archived.")
    week_start = _selected_week_start(request.GET.get("week"), today_date)
    return redirect(f"{reverse('schedule')}?week={week_start.isoformat()}")



def additional_login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        
        # Authentication
        if user is None:
            messages.error(request, "Your email or password was incorrect.")
            return render(request, "registration/login.html")

        # Authorization
        client_user = UserDetail.objects.filter(user=user).first()
        # no use .first(): query a set of object (even 1 obj only) or return a empty set
        # use .first(): query 1 object or return a none
        if (not client_user) or (client_user.role != "trainer") or (client_user.is_archived):
            messages.error(request, "Your account does not have permission to access the Trainforge.")
            return render(request, "registration/login.html")
        
        login(request, user)
        return redirect("all_clients")
    return render(request, "registration/login.html")


@login_required
def suggest_ai_note(request, client_id):
    client_user = get_object_or_404(UserDetail, user=request.user, role='trainer')
    client = get_object_or_404(Client, id=client_id, user=client_user)
    client_plan = get_object_or_404(ClientPlan, client=client, is_archived=False)
    plan_exercises = PlanExercise.objects.filter(client_plan=client_plan, is_archived=False)

    c_weight = f"Current weight: {client.current_weight}" 
    t_weight = f"Target weight: {client.target_weight}" 
    start_date = f"Training plan start date: {client_plan.start_date}" 
    end_date = f"Training plan end date: {client_plan.end_date}"
    plan_exercise_spec = "Preferred (selected) planning exercises: "

    if client.goal_description:
        training_goal = "Training goal: " + client.goal + ', ' + client.goal_description
    else:
        training_goal = "Training goal: " + client.goal

    for i in plan_exercises:
        plan_exercise_spec += f"exercise item: {i.user_exercise.exercise_name_copy}\n"
        plan_exercise_spec += f"frequency: {i.frequency}\n"
        plan_exercise_spec += f"repetition: {i.repetition}\n"
        plan_exercise_spec += f"description: {i.description or 'not provided'}\n\n"

    # Define the structured output parser using your schema
    parser = JsonOutputParser(pydantic_object=AINoteSuggestions)

    # Define the prompt
    prompt = PromptTemplate(
        template=(
            "You are a professional personal trainer.\n"
            "Your objective is to draw on your professional expertise and teaching experience to create a tailored weekly exercise plan for the following client.\n"
            "Generate 3 training note alternatives based on the client information below.\n\n"
            "{format_instructions}\n\n"
            "client_information: \n"
            "{c_weight}\n"
            "{t_weight}\n"
            "{start_date}\n"
            "{end_date}\n"
            "{plan_exercise_spec}\n"
            "{training_goal}\n"               
        ),
        input_variables=["c_weight", "t_weight", "start_date", "end_date", "plan_exercise_spec", "training_goal"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    # Set up the chain
    llm = ChatOpenAI(
        api_key=settings.OPENAI_API_KEY,
        model="gpt-5.4-mini",
        temperature=0.7,
    )
    chain = prompt | llm | parser

    try:
        result = chain.invoke({"c_weight":c_weight , "t_weight":t_weight , "start_date":start_date , "end_date":end_date ,
                                "plan_exercise_spec":plan_exercise_spec , "training_goal": training_goal})
        suggestions = result["suggestions"]
    except Exception:
        suggestions = []

    # Return ONLY the partial template — HTMX will insert it into the page
    return render(request, "partials/_note_suggestions.html", {
        "suggestions": suggestions,
        "client":client,
        "plan":client_plan,
    })


@login_required
def select_ai_note(request, client_id):
    new_note = request.POST.get("newnote")
    client_user = get_object_or_404(UserDetail, user=request.user, role='trainer')
    client = get_object_or_404(Client, id=client_id, user=client_user)
    client_plan = get_object_or_404(ClientPlan, client=client, is_archived=False)

    client_plan.weekly_notes = new_note
    client_plan.save()

    # Return the updated bio section — HTMX replaces the old one
    return render(request, "partials/_note_section.html", {
        "client": client,
        "plan": client_plan,
    })





@login_required
def suggest_ai_plan_customization(request, client_id):
    client_user = get_object_or_404(UserDetail, user=request.user, role='trainer')
    client = get_object_or_404(Client, id=client_id, user=client_user)
    client_plan = get_object_or_404(ClientPlan, client=client, is_archived=False)
    plan_exercise = PlanExercise.objects.filter(client_plan=client_plan, is_archived=False)

    c_weight = f"Current weight: {client.current_weight}" 
    t_weight = f"Target weight: {client.target_weight}" 
    start_date = f"Training plan start date: {client_plan.start_date}" 
    end_date = f"Training plan end date: {client_plan.end_date}"

    if client.goal_description:
        training_goal = "Training goal: " + client.goal + ', ' + client.goal_description
    else:
        training_goal = "Training goal: " + client.goal

    detailed_plan = []
    for pex in plan_exercise:
        detailed_plan.append([pex.user_exercise.exercise_name_copy, pex.frequency or 'not provided', pex.repetition or 'not provided', pex.description or 'not provided'])

    # Define the structured output parser using your schema
    parser = JsonOutputParser(pydantic_object=AIExercisePlanSuggestions)

    # Define the prompt
    prompt = PromptTemplate(
        template=(  
            "你现在是一位拥有丰富教学经验的健身教练，你的任务是根据学员提供的信息来生成针对于该学员的健身计划，该计划要让学员在按照这个运动频率、重复次数锻炼之后可以在这个计划周期结束时完成目标。\n"
            "{format_instructions}\n\n"
            "以下内容是该学员的信息：\n"
            "{c_weight}\n"
            "{t_weight}\n"
            "{start_date}\n"
            "{end_date}\n"
            "{training_goal}\n"
            "以下内容是该学员选择的运动项目：\n"
            "{detailed_plan}\n"
            "最外层的'[]'中的每一个'[]'代表该学员选择的运动项目，每个运动项目'[]'中有四个数据，从左到右依次是运动项目的名称，学员计划该项目的 frequency，repetition，以及description，即教练针对该项目给学员的一些notes和健身指导。 \n"
            "每个运动项目'[]'中右边3个数据可能是not provided或者是不符合实际的，你的任务就是先分析该学员的所有信息，然后根据学员的实际情况，生成个性化健身计划，返回值也是'[]'这样的形式，外部是一个'[]'，它内部的每一个'[]'都代表一个运动项目，内部'[]'中有四个数据，分别为运动项目名称(你不用更改)，frequency(你需要更改)，repetition(你需要更改)，以及description(你需要更改) \n"
            "frequency，repetition，以及description主要是你要改动的。frequency和repetition必须纯是正整数(datatype: int)，无需任何单位，description是文本、数字、特殊符号的组合(datatype: str) \n"
            "你的所有回复必须是英文"
        ),
        input_variables=["c_weight", "t_weight", "start_date", "end_date", "detailed_plan", "training_goal"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    # Set up the chain
    llm = ChatOpenAI(
        api_key=settings.OPENAI_API_KEY,
        model="gpt-5.4-mini",
        temperature=0.7,
    )
    chain = prompt | llm | parser

    try:
        result = chain.invoke({"c_weight":c_weight , "t_weight":t_weight , "start_date":start_date , "end_date":end_date ,
                                "detailed_plan":detailed_plan , "training_goal": training_goal})
        ex_p_sug = result["ex_p_sug"]

        # 数据库中抓取数据赋值给新变量，让AI生成的数据覆盖新变量中的数据
        for original_data, generated_data in zip(plan_exercise, ex_p_sug):
            original_data.frequency = generated_data[1]
            original_data.repetition = generated_data[2]
            original_data.description = generated_data[3]

    except Exception as e:
        print(e)
        ex_p_sug = []

    return render(request, "customize_plan.html", {
        "client":client,
        "plan_exercise": plan_exercise
    })
