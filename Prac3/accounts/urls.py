from django.contrib.auth.views import LogoutView
from django.urls import path

from .views import UserLoginView, profile, register, validate_username

app_name = 'accounts'

urlpatterns = [
    path('register/', register, name='register'),
    path('validate-username/', validate_username, name='validate_username'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', profile, name='profile'),
]
