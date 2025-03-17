
# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from .models import (
    User, UserActivity, AgeGroup, Parent, Mentor, Content, Challenge,
    ConceptNote, Hint, Badge, BadgeRequirement, UserProgress,
    UserPreference, Submission, ForumTopic, ForumPost, Comment,
    RoleModel, MentorConnection
)

# Unregister the default Group model
admin.site.unregister(Group)

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'username', 'is_active', 'is_staff', 'date_joined')
    search_fields = ('email', 'username')
    ordering = ('-date_joined',)
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Personal info', {'fields': ('display_name', 'date_of_birth', 'age_group')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'activity_type', 'timestamp', 'is_achievement', 'is_milestone')
    list_filter = ('activity_type', 'is_achievement', 'is_milestone')
    search_fields = ('user__username', 'activity_type')

@admin.register(AgeGroup)
class AgeGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'min_age', 'max_age')
    search_fields = ('name',)

@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ('user', 'name')

@admin.register(Mentor)
class MentorAdmin(admin.ModelAdmin):
    list_display = ('user', 'expertise', 'is_verified')
    list_filter = ('is_verified',)

@admin.register(Content)
class ContentAdmin(admin.ModelAdmin):
    list_display = ('title', 'content_type', 'age_group', 'created_at')
    search_fields = ('title',)
    list_filter = ('content_type', 'age_group')

@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ('title', 'points', 'difficulty_level', 'theme')
    search_fields = ('title', 'theme')

@admin.register(ConceptNote)
class ConceptNoteAdmin(admin.ModelAdmin):
    list_display = ('title', 'reading_level')

@admin.register(Hint)
class HintAdmin(admin.ModelAdmin):
    list_display = ('challenge', 'sequence_number', 'points_deduction')

@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ('name', 'points_value', 'is_achievement')
    list_filter = ('is_achievement',)

@admin.register(BadgeRequirement)
class BadgeRequirementAdmin(admin.ModelAdmin):
    list_display = ('badge', 'requirement_type', 'threshold')

@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'content', 'completion_percentage', 'points_earned')
    list_filter = ('completion_percentage',)

@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'color_theme', 'avatar_choice')

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'challenge', 'is_correct', 'attempts', 'submitted_at')
    list_filter = ('is_correct',)

@admin.register(ForumTopic)
class ForumTopicAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_by', 'created_at', 'is_pinned', 'is_closed')
    list_filter = ('is_pinned', 'is_closed')

@admin.register(ForumPost)
class ForumPostAdmin(admin.ModelAdmin):
    list_display = ('topic', 'created_by', 'created_at')

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('post', 'created_by', 'created_at')

@admin.register(RoleModel)
class RoleModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'field', 'country')
    search_fields = ('name', 'field')

@admin.register(MentorConnection)
class MentorConnectionAdmin(admin.ModelAdmin):
    list_display = ('mentor', 'mentee', 'status', 'created_at')
    list_filter = ('status',)
