from rest_framework import serializers
from .models import (
    AgeGroup, Content, Challenge, ConceptNote, Hint,
    Badge, BadgeRequirement, UserProgress, UserPreference, Submission,
    ForumTopic, ForumPost, Comment, RoleModel, MentorConnection, UserActivity
)

class AgeGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgeGroup
        fields = ['id', 'name', 'min_age', 'max_age', 'description']

class HintSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hint
        fields = ['id', 'hint_text', 'sequence_number', 'points_deduction']

class ChallengeSerializer(serializers.ModelSerializer):
    hints = HintSerializer(many=True, read_only=True)
    
    class Meta:
        model = Challenge
        fields = [
            'id', 'title', 'description', 'problem_statement', 
            'expected_output', 'test_cases', 'points', 
            'difficulty_level', 'theme', 'hints'
        ]

class ConceptNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConceptNote
        fields = [
            'id', 'title', 'explanation', 'theme_description',
            'visual_aids', 'reading_level'
        ]

class ContentSerializer(serializers.ModelSerializer):
    challenges = ChallengeSerializer(many=True, read_only=True)
    concept_notes = ConceptNoteSerializer(many=True, read_only=True)
    age_group = AgeGroupSerializer(read_only=True)
    
    class Meta:
        model = Content
        fields = [
            'id', 'title', 'description', 'age_group', 'content_type',
            'metadata', 'is_offline_available', 'difficulty_base',
            'challenges', 'concept_notes', 'created_at', 'updated_at'
        ]
class ContentDetailSerializer(serializers.ModelSerializer):
    challenges = ChallengeSerializer(many=True, read_only=True)
    concept_notes = ConceptNoteSerializer(many=True, read_only=True)
    age_group = AgeGroupSerializer(read_only=True)
    
    class Meta:
        model = Content
        fields = [
            'id', 'title', 'description', 'age_group', 'content_type',
            'metadata', 'is_offline_available', 'difficulty_base',
            'challenges', 'concept_notes', 'created_at', 'updated_at'
        ]
        

class BadgeRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = BadgeRequirement
        fields = ['id', 'requirement_type', 'requirement_data', 'threshold']

class BadgeSerializer(serializers.ModelSerializer):
    requirements = BadgeRequirementSerializer(many=True, read_only=True)
    
    class Meta:
        model = Badge
        fields = [
            'id', 'name', 'description', 'image_url',
            'points_value', 'is_achievement', 'requirements'
        ]

class UserProgressSerializer(serializers.ModelSerializer):
    content = ContentSerializer(read_only=True)
    challenge = ChallengeSerializer(read_only=True)
    
    class Meta:
        model = UserProgress
        fields = [
            'id', 'content', 'challenge', 'completion_percentage',
            'points_earned', 'started_at', 'completed_at', 'difficulty_level'
        ]
        read_only_fields = ['id', 'started_at']

class UserPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreference
        fields = ['id', 'color_theme', 'avatar_choice', 'sound_enabled', 'ui_preferences']

class SubmissionSerializer(serializers.ModelSerializer):
    challenge = ChallengeSerializer(read_only=True)
    
    class Meta:
        model = Submission
        fields = [
            'id', 'challenge', 'submitted_code', 'is_correct',
            'attempts', 'submitted_at', 'feedback'
        ]
        read_only_fields = ['id', 'submitted_at', 'attempts']



from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType

class UserActivitySerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source='user.username')
    content_type_name = serializers.SerializerMethodField()
    content_name = serializers.SerializerMethodField()
    
    class Meta:
        model = UserActivity
        fields = [
            'id', 'user', 'username', 'activity_type', 'timestamp',
            'content_type_name', 'object_id', 'content_name',
            'data', 'device_type', 'browser', 'is_achievement', 'is_milestone'
        ]
        read_only_fields = ['user', 'timestamp']
    
    def get_content_type_name(self, obj):
        if obj.content_type:
            return obj.content_type.model
        return None
    
    def get_content_name(self, obj):
        """Try to get a meaningful name for the related object"""
        if obj.content_object:
            for attr in ['title', 'name', 'display_name', '__str__']:
                if hasattr(obj.content_object, attr):
                    if callable(getattr(obj.content_object, attr)):
                        return getattr(obj.content_object, attr)()
                    return getattr(obj.content_object, attr)
        return None



class ForumTopicSerializer(serializers.ModelSerializer):
    created_by_username = serializers.ReadOnlyField(source='created_by.username')
    post_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ForumTopic
        fields = ['id', 'title', 'description', 'created_by', 'created_by_username', 
                 'created_at', 'is_pinned', 'is_closed', 'post_count']
        read_only_fields = ['created_by']
    
    def get_post_count(self, obj):
        return obj.posts.count()

class ForumPostSerializer(serializers.ModelSerializer):
    created_by_username = serializers.ReadOnlyField(source='created_by.username')
    comment_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ForumPost
        fields = ['id', 'topic', 'content', 'created_by', 'created_by_username', 
                 'created_at', 'updated_at', 'comment_count']
        read_only_fields = ['created_by', 'topic']
    
    def get_comment_count(self, obj):
        return obj.comments.count()

class CommentSerializer(serializers.ModelSerializer):
    created_by_username = serializers.ReadOnlyField(source='created_by.username')
    
    class Meta:
        model = Comment
        fields = ['id', 'post', 'content', 'created_by', 'created_by_username', 'created_at']
        read_only_fields = ['created_by', 'post']

class RoleModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleModel
        fields = ['id', 'name', 'bio', 'accomplishments', 'field', 
                 'country', 'image', 'external_url']

class MentorConnectionSerializer(serializers.ModelSerializer):
    mentee_username = serializers.ReadOnlyField(source='mentee.username')
    mentor_name = serializers.ReadOnlyField(source='mentor.user.display_name')
    mentor_expertise = serializers.ReadOnlyField(source='mentor.expertise')
    
    class Meta:
        model = MentorConnection
        fields = ['id', 'mentor', 'mentee', 'mentee_username', 'mentor_name', 
                 'mentor_expertise', 'status', 'created_at', 'updated_at', 'goals']
        read_only_fields = ['mentee', 'created_at']