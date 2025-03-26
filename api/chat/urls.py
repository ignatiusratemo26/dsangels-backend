from django.urls import path
from .views import ChatMessageView

urlpatterns = [
    path('send-message/', ChatMessageView.as_view(), name='chat-message'),
]