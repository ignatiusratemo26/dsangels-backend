from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.conf import settings
from core.models import ChatHistory
from ai_engine.chat_service import generate_chat_response

class ChatMessageView(APIView):
    """
    API endpoint for chat messages
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        message = request.data.get('message', '')
        if not message.strip():
            return Response(
                {'error': 'Message cannot be empty'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get user data for context
        user = request.user
        user_data = {
            'display_name': user.display_name or user.username,
            'age_group': {
                'id': user.age_group.id if user.age_group else None,
                'name': user.age_group.name if user.age_group else 'General',
                'age_range': f"{user.age_group.min_age}-{user.age_group.max_age}" if user.age_group else '8-18'
            },
            'is_authenticated': True
        }
        
        # Get recent chat history
        chat_history = ChatHistory.objects.filter(user=user).order_by('-timestamp')[:10]
        user_data['chat_history'] = [
            {
                'message': chat.message,
                'is_user': chat.is_user,
                'timestamp': chat.timestamp.isoformat()
            }
            for chat in reversed(chat_history)
        ]
        
        # Store user message
        ChatHistory.objects.create(
            user=user,
            message=message,
            is_user=True
        )
        
        # Generate response
        response_data = generate_chat_response(message, user_data)
        
        # Store bot response
        if response_data.get('success', False):
            ChatHistory.objects.create(
                user=user,
                message=response_data['message'],
                is_user=False
            )
        
        return Response(response_data)