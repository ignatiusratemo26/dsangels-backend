from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ContentListCreateView,
    ContentDetailView,
    ChallengeListCreateView,
    ChallengeDetailView,
    ConceptNoteListCreateView,
    ConceptNoteDetailView,
    ContentRecommendationView,
    GenerateHintView,
    ContentDifficultyAdjustmentView,
    PopularContentView,
    ThemedExplanationView,

)

router = DefaultRouter()

urlpatterns = [
    # Standard RESTful endpoints
    path('', ContentListCreateView.as_view(), name='content-list'),
    path('<int:pk>/', ContentDetailView.as_view(), name='content-detail'),
    path('challenges/', ChallengeListCreateView.as_view(), name='challenge-list'),
    path('challenges/<int:pk>/', ChallengeDetailView.as_view(), name='challenge-detail'),
    path('concept-notes/', ConceptNoteListCreateView.as_view(), name='concept-note-list'),
    path('concept-notes/<int:pk>/', ConceptNoteDetailView.as_view(), name='concept-note-detail'),
    

    # AI-powered endpoints
    path('recommendations/', ContentRecommendationView.as_view(), name='content-recommendations'),
    path('challenges/<int:challenge_id>/generate-hint/', GenerateHintView.as_view(), name='generate-hint'),
    path('themed-explanation/', ThemedExplanationView.as_view(), name='themed-explanation'),
    path('<int:content_id>/adjust-difficulty/', ContentDifficultyAdjustmentView.as_view(), name='adjust-content-difficulty'),
    path('popular/', PopularContentView.as_view(), name='popular-content'),
    
    # Include router URLs
    path('', include(router.urls)),
]