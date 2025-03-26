from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
import json
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

class UserActivity(models.Model):
    # Activity types for tracking different user interactions
    ACTIVITY_TYPES = (
        ('view', 'View'),
        ('complete', 'Complete'),
        ('start', 'Start'),
        ('search', 'Search'),
        ('like', 'Like'),
        ('share', 'Share'),
        ('comment', 'Comment'),
        ('login', 'Login'),
        ('signup', 'Sign Up'),
        ('points', 'Points Earned'),
        ('badge', 'Badge Earned'),
        ('forum_post', 'Forum Post'),
        ('other', 'Other')
    )
    
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Generic relation to any model (Content, Challenge, Badge, etc.)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Additional data as JSON (e.g., search terms, duration, points earned)
    data = models.JSONField(default=dict, blank=True)
    
    # Device and location info
    device_type = models.CharField(max_length=50, blank=True, null=True)
    browser = models.CharField(max_length=50, blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    session_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Flags for filtering
    is_achievement = models.BooleanField(default=False)  # Represents a significant achievement
    is_milestone = models.BooleanField(default=False)    # Represents a learning milestone
    
    class Meta:
        verbose_name_plural = "User Activities"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['activity_type']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.activity_type} - {self.timestamp}"
    
    @classmethod
    def log(cls, user, activity_type, content_object=None, **kwargs):
        """
        Helper method to easily log user activity
        
        Args:
            user: User object
            activity_type: Type of activity from ACTIVITY_TYPES
            content_object: Optional related object
            **kwargs: Additional data to store in the data field
        
        Returns:
            The created UserActivity instance
        """
        activity = cls(
            user=user,
            activity_type=activity_type
        )
        
        if content_object:
            activity.content_object = content_object
        
        # Add any other provided data
        if kwargs:
            activity.data = kwargs
        
        # Special handling for certain activity types
        if activity_type in ['complete', 'badge']:
            activity.is_achievement = True
            
        if activity_type == 'complete' and content_object and hasattr(content_object, 'is_milestone'):
            activity.is_milestone = content_object.is_milestone
            
        activity.save()
        return activity
    
class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        if not username:
            raise ValueError('Users must have a username')
        
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(username, email, password, **extra_fields)

class AgeGroup(models.Model):
    name = models.CharField(max_length=50)
    min_age = models.IntegerField()
    max_age = models.IntegerField()
    description = models.TextField()
    
    def __str__(self):
        return f"{self.name} ({self.min_age}-{self.max_age})"

class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(max_length=255, unique=True)
    display_name = models.CharField(max_length=150, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    age_group = models.ForeignKey(AgeGroup, on_delete=models.SET_NULL, null=True, related_name='users')
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        return self.display_name or self.username
    
    def get_short_name(self):
        return self.username
    
    def save(self, *args, **kwargs):
        if not self.display_name:
            self.display_name = self.username
        super().save(*args, **kwargs)

class Parent(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='parent_profile')
    name = models.CharField(max_length=255)
    
    def __str__(self):
        return self.name

class Mentor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='mentor_profile')
    expertise = models.CharField(max_length=255)
    bio = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False)
    
    def __str__(self):
        return self.user.email

class Content(models.Model):
    CONTENT_TYPES = (
        ('lesson', 'Lesson'),
        ('challenge', 'Challenge'),
        ('tutorial', 'Tutorial'),
        ('quiz', 'Quiz'),
    )
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    age_group = models.ForeignKey(AgeGroup, on_delete=models.CASCADE, related_name='contents')
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES)
    metadata = models.JSONField(default=dict)
    is_offline_available = models.BooleanField(default=False)
    difficulty_base = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title

class Challenge(models.Model):
    content = models.ForeignKey(Content, on_delete=models.CASCADE, related_name='challenges')
    title = models.CharField(max_length=255)
    description = models.TextField()
    problem_statement = models.TextField()
    expected_output = models.TextField()
    test_cases = models.JSONField(default=list)
    points = models.IntegerField(default=10)
    difficulty_level = models.IntegerField(default=1)
    theme = models.CharField(max_length=100, default='general')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title

class ConceptNote(models.Model):
    content = models.ForeignKey(Content, on_delete=models.CASCADE, related_name='concept_notes')
    title = models.CharField(max_length=255)
    explanation = models.TextField()
    theme_description = models.CharField(max_length=255)
    visual_aids = models.JSONField(default=dict)
    reading_level = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title

class Hint(models.Model):
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name='hints')
    hint_text = models.TextField()
    sequence_number = models.IntegerField()
    points_deduction = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['sequence_number']
    
    def __str__(self):
        return f"Hint {self.sequence_number} for {self.challenge.title}"

class Badge(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    image_url = models.CharField(max_length=255)
    points_value = models.IntegerField(default=0)
    is_achievement = models.BooleanField(default=True)
    users = models.ManyToManyField(User, related_name='badges', blank=True)
    
    def __str__(self):
        return self.name

class BadgeRequirement(models.Model):
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name='requirements')
    requirement_type = models.CharField(max_length=100)
    requirement_data = models.JSONField(default=dict)
    threshold = models.IntegerField()
    
    def __str__(self):
        return f"Requirement for {self.badge.name}"

class UserProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progresses')
    content = models.ForeignKey(Content, on_delete=models.CASCADE, related_name='user_progresses', null=True, blank=True)
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name='user_progresses', null=True, blank=True)
    completion_percentage = models.FloatField(default=0.0)
    points_earned = models.IntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    difficulty_level = models.IntegerField(default=1)
    
    def __str__(self):
        return f"Progress of {self.user.username} on {self.content.title}"
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(content__isnull=False) | Q(challenge__isnull=False),
                name="at_least_one_content_or_challenge"
            )
        ]

class UserPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')
    color_theme = models.CharField(max_length=50, default='default')
    avatar_choice = models.CharField(max_length=100, default='default')
    sound_enabled = models.BooleanField(default=True)
    ui_preferences = models.JSONField(default=dict)
    
    def __str__(self):
        return f"Preferences for {self.user.username}"

class Submission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name='submissions')
    submitted_code = models.TextField()
    is_correct = models.BooleanField(default=False)
    attempts = models.IntegerField(default=1)
    submitted_at = models.DateTimeField(auto_now_add=True)
    feedback = models.JSONField(default=dict)
    
    def __str__(self):
        return f"Submission by {self.user.username} for {self.challenge.title}"
    
    class Meta:
        ordering = ['-submitted_at']

# Add to your core/models.py file
class ForumTopic(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forum_topics')
    created_at = models.DateTimeField(auto_now_add=True)
    is_pinned = models.BooleanField(default=False)
    is_closed = models.BooleanField(default=False)
    
    def __str__(self):
        return self.title

class ForumPost(models.Model):
    topic = models.ForeignKey(ForumTopic, on_delete=models.CASCADE, related_name='posts')
    content = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forum_posts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Post by {self.created_by.username} in {self.topic.title}"

class Comment(models.Model):
    post = models.ForeignKey(ForumPost, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Comment by {self.created_by.username}"

class RoleModel(models.Model):
    name = models.CharField(max_length=255)
    bio = models.TextField()
    accomplishments = models.TextField()
    field = models.CharField(max_length=100)  # e.g., "AI Research", "Software Engineering"
    country = models.CharField(max_length=100)
    image = models.ImageField(upload_to='role_models/', blank=True, null=True)
    external_url = models.URLField(blank=True, null=True)
    
    def __str__(self):
        return self.name

class MentorConnection(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed')
    )
    
    mentor = models.ForeignKey(Mentor, on_delete=models.CASCADE, related_name='mentorships')
    mentee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mentee_connections')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    goals = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.mentee.username} -> {self.mentor.user.username} ({self.get_status_display()})"


