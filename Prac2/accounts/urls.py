from django.contrib.auth.views import LogoutView
from django.urls import path
from .views import UserLoginView, profile, register

app_name = 'accounts'

urlpatterns = [
    path('register/', register, name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', profile, name='profile'),
]
