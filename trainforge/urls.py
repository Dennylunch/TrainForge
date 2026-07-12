"""
URL configuration for trainforge project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from trainforgeapp import views

urlpatterns = [
    path("", views.index, name="root"),
    path("trainforge/", include("trainforgeapp.urls")),
    path("trainforge/admin/", admin.site.urls),

    path("trainforge/accounts/login/", views.additional_login_view, name="login" ),
    path("trainforge/accounts/", include("django.contrib.auth.urls")), 
]

# path("trainforge/accounts/", include("django.contrib.auth.urls")) 
# built-in login sigup view, password check