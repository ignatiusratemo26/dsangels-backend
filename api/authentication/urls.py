from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, LoginView, LogoutView,
    UserProfileView, ChangePasswordView, 
    ParentRegistrationView, MentorRegistrationView
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('register/parent/', ParentRegistrationView.as_view(), name='register_parent'),
    path('register/mentor/', MentorRegistrationView.as_view(), name='register_mentor'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', UserProfileView.as_view(), name='user_profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
]