from django.urls import path
from .views import UserPreferenceView, SavedConceptToggleView

urlpatterns = [
    path('preferences/', UserPreferenceView.as_view(), name='user_preferences'),
    path('saved-concepts/toggle/', SavedConceptToggleView.as_view(), name='toggle_saved_concept'),
]