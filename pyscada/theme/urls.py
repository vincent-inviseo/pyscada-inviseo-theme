from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(template_name="login-inviseo.html"),
        name="login_inviseo_view",
    ),
    path("", views.view_overview, name="view-overview-inviseo"),
    path("view/<link_title>/", views.view, name="main_view_inviseo"),
]
