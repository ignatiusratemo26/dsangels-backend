from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q

from .models import Content, Challenge, ConceptNote, AgeGroup
from .serializers import (
    ContentSerializer, 
    ChallengeSerializer, 
    ConceptNoteSerializer,
    AgeGroupSerializer
)
from ai_engine.difficulty_adjuster import adjust_content_difficulty
from ai_engine.content_generator import generate_themed_explanation


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class BaseContentViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet for content-related models with common functionality
    """
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    def get_permissions(self):
        """
        Override to allow unauthenticated access to list and retrieve actions
        """
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticatedOrReadOnly()]
        return super().get_permissions()

    @action(detail=True, methods=['post'])
    def report_issue(self, request, pk=None):
        """
        Report an issue with content
        """
        content = self.get_object()
        # Save the reported issue
        # This is a placeholder for actual implementation
        return Response({"message": f"Issue reported for {content.__class__.__name__} #{content.id}"})


class ContentViewSet(BaseContentViewSet):
    """
    ViewSet for main Content model
    """
    queryset = Content.objects.all()
    serializer_class = ContentSerializer
    search_fields = ['title', 'description']
    ordering_fields = ['title', 'created_at', 'difficulty_base']

    def get_queryset(self):
        """
        Filter content based on age group, content type, and difficulty
        """
        queryset = Content.objects.all()
        
        # Filter by age group
        age_group_id = self.request.query_params.get('age_group')
        if age_group_id:
            queryset = queryset.filter(age_group_id=age_group_id)
        
        # Filter by content type
        content_type = self.request.query_params.get('content_type')
        if content_type:
            queryset = queryset.filter(content_type=content_type)
        
        # Filter by difficulty range
        min_difficulty = self.request.query_params.get('min_difficulty')
        max_difficulty = self.request.query_params.get('max_difficulty')
        if min_difficulty:
            queryset = queryset.filter(difficulty_base__gte=min_difficulty)
        if max_difficulty:
            queryset = queryset.filter(difficulty_base__lte=max_difficulty)
        
        # Filter by offline availability
        offline_available = self.request.query_params.get('offline_available')
        if offline_available is not None:
            queryset = queryset.filter(is_offline_available=(offline_available.lower() == 'true'))
        
        # Search in title and description
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )
        
        return queryset

    @action(detail=True, methods=['get'])
    def adapt_difficulty(self, request, pk=None):
        """
        Adapt content difficulty based on user level
        """
        content = self.get_object()
        target_difficulty = request.query_params.get('difficulty', '3')
        
        # Use AI engine to adapt content difficulty
        adapted_content = adjust_content_difficulty(
            content=content,
            target_difficulty=int(target_difficulty)
        )
        
        return Response(adapted_content)

    @action(detail=False, methods=['get'])
    def recommended(self, request):
        """
        Get recommended content for the current user
        """
        user = request.user
        # This would integrate with recommendation.py from the ai_engine
        # For now, just return age-appropriate content
        try:
            age_group = user.age_group_id
            queryset = self.get_queryset().filter(age_group_id=age_group)[:5]
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        except:
            return Response({"error": "Could not determine appropriate content"}, 
                           status=status.HTTP_400_BAD_REQUEST)


class ChallengeViewSet(BaseContentViewSet):
    """
    ViewSet for Challenge model
    """
    queryset = Challenge.objects.all()
    serializer_class = ChallengeSerializer
    search_fields = ['title', 'description', 'problem_statement']
    ordering_fields = ['title', 'points', 'difficulty_level']

    def get_queryset(self):
        """
        Filter challenges by content id, difficulty level, theme
        """
        queryset = Challenge.objects.all()
        
        # Filter by parent content
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
        
        # Filter by points range
        min_points = self.request.query_params.get('min_points')
        max_points = self.request.query_params.get('max_points')
        if min_points:
            queryset = queryset.filter(points__gte=min_points)
        if max_points:
            queryset = queryset.filter(points__lte=max_points)
        
        return queryset

    @action(detail=True, methods=['get'])
    def hints(self, request, pk=None):
        """
        Get hints for a challenge
        """
        challenge = self.get_object()
        # Return all hints for the challenge
        hints = challenge.hint_set.all().order_by('sequence_number')
        from core.serializers import HintSerializer
        serializer = HintSerializer(hints, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def submit_solution(self, request, pk=None):
        """
        Submit a solution for a challenge
        """
        challenge = self.get_object()
        submitted_code = request.data.get('code', '')
        
        # This is where you'd validate the submitted code against test cases
        # For now, just save the submission
        submission = challenge.submission_set.create(
            user=request.user,
            submitted_code=submitted_code,
            is_correct=False,  # This would be determined by actual evaluation
            attempts=challenge.submission_set.filter(user=request.user).count() + 1
        )
        
        # Return a basic response
        return Response({
            "submission_id": submission.id,
            "is_correct": submission.is_correct,
            "attempts": submission.attempts,
            "feedback": {"message": "Solution received! Evaluation pending."}
        })


class ConceptNoteViewSet(BaseContentViewSet):
    """
    ViewSet for ConceptNote model
    """
    queryset = ConceptNote.objects.all()
    serializer_class = ConceptNoteSerializer
    search_fields = ['title', 'explanation']
    ordering_fields = ['title', 'reading_level']

    def get_queryset(self):
        """
        Filter concept notes by content id, reading level
        """
        queryset = ConceptNote.objects.all()
        
        # Filter by parent content
        content_id = self.request.query_params.get('content_id')
        if content_id:
            queryset = queryset.filter(content_id=content_id)
        
        # Filter by reading level
        reading_level = self.request.query_params.get('reading_level')
        if reading_level:
            queryset = queryset.filter(reading_level=reading_level)
        
        return queryset

    @action(detail=True, methods=['get'])
    def themed_explanation(self, request, pk=None):
        """
        Get a themed explanation for the concept note
        """
        concept_note = self.get_object()
        theme = request.query_params.get('theme', 'default')
        
        # Use the AI engine to generate a themed explanation
        themed_explanation = generate_themed_explanation(
            concept=concept_note.title,
            base_explanation=concept_note.explanation,
            theme=theme,
            age_level=concept_note.reading_level
        )
        
        return Response({
            "concept": concept_note.title,
            "themed_explanation": themed_explanation,
            "theme": theme
        })


class AgeGroupViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for AgeGroup model (read-only)
    """
    queryset = AgeGroup.objects.all()
    serializer_class = AgeGroupSerializer
    permission_classes = [permissions.AllowAny]