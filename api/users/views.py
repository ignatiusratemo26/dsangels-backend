from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import UserPreference, ConceptNote, User
from core.serializers import UserPreferenceSerializer

class UserPreferenceView(APIView):
    """
    Get or update user preferences
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        try:
            # Get or create preferences
            preferences, created = UserPreference.objects.get_or_create(
                user=request.user,
                defaults={
                    'color_theme': 'default',
                    'avatar_choice': 'default',
                    'sound_enabled': True,
                    'ui_preferences': {}
                }
            )
            
            # Get user's saved concepts
            saved_concepts = []
            if 'saved_concepts' in preferences.ui_preferences:
                saved_concepts = preferences.ui_preferences['saved_concepts']
            
            # Prepare the response data
            data = {
                'id': preferences.id,
                'color_theme': preferences.color_theme,
                'avatar_choice': preferences.avatar_choice,
                'sound_enabled': preferences.sound_enabled,
                'saved_concepts': saved_concepts,
                'theme_preference': preferences.ui_preferences.get('theme_preference', 'light'),
                'email_notifications': preferences.ui_preferences.get('email_notifications', True),
            }
            
            return Response(data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def put(self, request):
        try:
            # Get or create preferences
            preferences, created = UserPreference.objects.get_or_create(
                user=request.user,
                defaults={
                    'color_theme': 'default',
                    'avatar_choice': 'default',
                    'sound_enabled': True,
                    'ui_preferences': {}
                }
            )
            
            # Update fields
            if 'color_theme' in request.data:
                preferences.color_theme = request.data['color_theme']
                
            if 'avatar_choice' in request.data:
                preferences.avatar_choice = request.data['avatar_choice']
                
            if 'sound_enabled' in request.data:
                preferences.sound_enabled = request.data['sound_enabled']
                
            # Handle ui_preferences as a nested structure
            ui_prefs = preferences.ui_preferences or {}
            
            if 'theme_preference' in request.data:
                ui_prefs['theme_preference'] = request.data['theme_preference']
                
            if 'email_notifications' in request.data:
                ui_prefs['email_notifications'] = request.data['email_notifications']
                
            preferences.ui_preferences = ui_prefs
            preferences.save()
            
            return Response({
                'id': preferences.id,
                'color_theme': preferences.color_theme,
                'avatar_choice': preferences.avatar_choice,
                'sound_enabled': preferences.sound_enabled,
                'saved_concepts': ui_prefs.get('saved_concepts', []),
                'theme_preference': ui_prefs.get('theme_preference', 'light'),
                'email_notifications': ui_prefs.get('email_notifications', True),
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SavedConceptToggleView(APIView):
    """
    Toggle a concept as saved/unsaved for the user
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            concept_id = request.data.get('concept_id')
            saved = request.data.get('saved', True)
            
            if not concept_id:
                return Response(
                    {'error': 'concept_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Check if concept exists
            try:
                concept = ConceptNote.objects.get(id=concept_id)
            except ConceptNote.DoesNotExist:
                return Response(
                    {'error': 'Concept not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
                
            # Get or create user preferences
            preferences, created = UserPreference.objects.get_or_create(
                user=request.user,
                defaults={
                    'color_theme': 'default',
                    'avatar_choice': 'default',
                    'sound_enabled': True,
                    'ui_preferences': {}
                }
            )
            
            # Update saved concepts
            ui_prefs = preferences.ui_preferences or {}
            saved_concepts = ui_prefs.get('saved_concepts', [])
            
            if saved and concept_id not in saved_concepts:
                saved_concepts.append(concept_id)
            elif not saved and concept_id in saved_concepts:
                saved_concepts.remove(concept_id)
                
            ui_prefs['saved_concepts'] = saved_concepts
            preferences.ui_preferences = ui_prefs
            preferences.save()
            
            return Response({
                'success': True,
                'saved': saved,
                'concept_id': concept_id,
                'saved_concepts': saved_concepts
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )