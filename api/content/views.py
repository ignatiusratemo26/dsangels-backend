from rest_framework import generics, permissions, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404

from core.models import Content, Challenge, ConceptNote, AgeGroup, UserProgress, Hint
from core.serializers import (
    ContentSerializer, 
    ChallengeSerializer, 
    ConceptNoteSerializer, 
    HintSerializer,
    AgeGroupSerializer,

    ContentDetailSerializer
)
from ai_engine.content_generator import (
    generate_themed_explanation,
    generate_hint,
    adapt_content_difficulty
)
from ai_engine.recommendation import get_personalized_recommendations


class ContentListCreateView(generics.ListCreateAPIView):
    """
    List all content or create new content
    """
    serializer_class = ContentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['title', 'difficulty_base', 'created_at']
    
    def get_queryset(self):
        """
        Filter content based on query parameters
        """
        queryset = Content.objects.all()
        
        # Filter by age group
        age_group = self.request.query_params.get('age_group')
        if age_group:
            queryset = queryset.filter(age_group_id=age_group)
        
        # Filter by content type
        content_type = self.request.query_params.get('content_type')
        if content_type:
            queryset = queryset.filter(content_type=content_type)
        
        # Filter by difficulty level
        difficulty = self.request.query_params.get('difficulty')
        if difficulty:
            queryset = queryset.filter(difficulty_base=difficulty)
            
        # Filter for offline availability
        offline = self.request.query_params.get('offline')
        if offline:
            queryset = queryset.filter(is_offline_available=(offline.lower() == 'true'))
            
        return queryset
    
    def perform_create(self, serializer):
        serializer.save()


class ContentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a content instance
    """
    queryset = Content.objects.all()
    serializer_class = ContentDetailSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        # Track that this content was viewed by the user
        if request.user.is_authenticated:
            # Get or create progress record for this content
            progress, created = UserProgress.objects.get_or_create(
                user=request.user,
                content=instance,
                defaults={'completion_percentage': 0}
            )
            
            # Update last viewed timestamp
            if not created:
                progress.save(update_fields=['started_at'])
        
        return Response(serializer.data)


class ChallengeListCreateView(generics.ListCreateAPIView):
    """
    List all challenges or create a new challenge
    """
    serializer_class = ChallengeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        """
        Filter challenges based on query parameters
        """
        queryset = Challenge.objects.all()
        
        # Filter by content ID
        content_id = self.request.query_params.get('content_id')
        if content_id:
            queryset = queryset.filter(content_id=content_id)
            
        # Filter by difficulty level
        difficulty = self.request.query_params.get('difficulty')
        if difficulty:
            queryset = queryset.filter(difficulty_level=difficulty)
            
        # Filter by theme
        theme = self.request.query_params.get('theme')
        if theme:
            queryset = queryset.filter(theme__icontains=theme)
            
        return queryset
    
    def perform_create(self, serializer):
        serializer.save()


class ChallengeDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a challenge instance
    """
    queryset = Challenge.objects.all()
    serializer_class = ChallengeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        # Track that this challenge was viewed by the user
        if request.user.is_authenticated:
            # Get or create progress record for this challenge
            progress, created = UserProgress.objects.get_or_create(
                user=request.user,
                challenge=instance,
                defaults={'completion_percentage': 0}
            )
            
            # Update last viewed timestamp
            if not created:
                progress.save(update_fields=['started_at'])
        
        return Response(serializer.data)


class ConceptNoteListCreateView(generics.ListCreateAPIView):
    """
    List all concept notes or create a new concept note
    """
    serializer_class = ConceptNoteSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        """
        Filter concept notes based on query parameters
        """
        queryset = ConceptNote.objects.all()
        
        # Filter by content ID
        content_id = self.request.query_params.get('content_id')
        if content_id:
            queryset = queryset.filter(content_id=content_id)
            
        # Filter by reading level
        reading_level = self.request.query_params.get('reading_level')
        if reading_level:
            queryset = queryset.filter(reading_level=reading_level)
            
        return queryset
    
    def perform_create(self, serializer):
        serializer.save()


class ConceptNoteDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a concept note instance
    """
    queryset = ConceptNote.objects.all()
    serializer_class = ConceptNoteSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class HintListCreateView(generics.ListCreateAPIView):
    """
    List all hints for a challenge or create a new hint
    """
    serializer_class = HintSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        """
        Filter hints based on challenge ID
        """
        challenge_id = self.kwargs.get('challenge_id')
        return Hint.objects.filter(challenge_id=challenge_id).order_by('sequence_number')
    
    def perform_create(self, serializer):
        challenge_id = self.kwargs.get('challenge_id')
        challenge = get_object_or_404(Challenge, pk=challenge_id)
        serializer.save(challenge=challenge)


class HintDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a hint instance
    """
    serializer_class = HintSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        challenge_id = self.kwargs.get('challenge_id')
        return Hint.objects.filter(challenge_id=challenge_id)


class AgeGroupListView(generics.ListAPIView):
    """
    List all age groups
    """
    queryset = AgeGroup.objects.all()
    serializer_class = AgeGroupSerializer
    permission_classes = [permissions.AllowAny]


class ContentRecommendationView(APIView):
    """
    Provide personalized content recommendations for a user
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Get parameters for recommendation
        count = int(request.query_params.get('count', 5))
        content_type = request.query_params.get('content_type')
        
        # Get recommendations from AI engine
        recommendations = get_personalized_recommendations(
            user_id=user.id,
            count=count,
            content_type=content_type
        )
        
        # Fetch content objects based on recommendations
        content_ids = [rec['content_id'] for rec in recommendations]
        contents = Content.objects.filter(id__in=content_ids)
        
        # Serialize and return
        serializer = ContentSerializer(contents, many=True)
        return Response(serializer.data)


class GenerateHintView(APIView):
    """
    Generate a hint for a challenge using AI
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, challenge_id):
        challenge = get_object_or_404(Challenge, pk=challenge_id)
        
        # Get user's current progress
        user_progress, _ = UserProgress.objects.get_or_create(
            user=request.user,
            challenge=challenge,
            defaults={'completion_percentage': 0}
        )
        
        # Extract user code or attempt from request
        user_attempt = request.data.get('attempt', '')
        hint_level = request.data.get('hint_level', 1)
        
        # Generate hint using AI engine
        hint_text = generate_hint(
            challenge_id=challenge_id,
            user_id=request.user.id,
            user_attempt=user_attempt,
            hint_level=hint_level
        )
        
        # Create a new hint object (optional)
        hint = Hint.objects.create(
            challenge=challenge,
            content=hint_text,
            sequence_number=hint_level,
            is_ai_generated=True
        )
        
        # Return the generated hint
        serializer = HintSerializer(hint)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ThemedExplanationView(APIView):
    """
    Generate themed explanations for concepts using AI
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        # Extract parameters from request
        concept = request.data.get('concept')
        theme = request.data.get('theme')
        age_group_id = request.data.get('age_group_id')
        
        if not concept or not theme:
            return Response(
                {'error': 'Both concept and theme are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Get age group
        age_group = get_object_or_404(AgeGroup, pk=age_group_id) if age_group_id else None
        
        # Generate themed explanation using AI
        explanation = generate_themed_explanation(
            concept=concept,
            theme=theme,
            age_group=age_group.name if age_group else None
        )
        
        return Response({
            'concept': concept,
            'theme': theme,
            'explanation': explanation,
            'age_group': age_group.name if age_group else None
        })


class ContentDifficultyAdjustmentView(APIView):
    """
    Adapt content difficulty based on user's learning level
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, content_id):
        content = get_object_or_404(Content, pk=content_id)
        user = request.user
        
        # Get parameters
        target_difficulty = request.data.get('target_difficulty')
        if not target_difficulty:
            return Response(
                {'error': 'Target difficulty is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Adapt content using AI
        adapted_content = adapt_content_difficulty(
            content_id=content_id,
            user_id=user.id,
            target_difficulty=target_difficulty
        )
        
        return Response({
            'original_content_id': content_id,
            'difficulty_level': target_difficulty,
            'adapted_content': adapted_content
        })


class PopularContentView(generics.ListAPIView):
    """
    List most popular content based on user engagement
    """
    serializer_class = ContentSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        # Define time period from query params (default to last 30 days)
        days = int(self.request.query_params.get('days', 30))
        
        # Get popular content based on user progress entries
        queryset = Content.objects.annotate(
            view_count=Count('userprogress')
        ).order_by('-view_count')
        
        # Apply additional filters
        content_type = self.request.query_params.get('content_type')
        if content_type:
            queryset = queryset.filter(content_type=content_type)
            
        # Limit results
        limit = int(self.request.query_params.get('limit', 10))
        return queryset[:limit]