from rest_framework import permissions
from core.models import Parent, Mentor

class IsParent(permissions.BasePermission):
    """
    Custom permission to only allow parents to access their children's data
    """
    def has_permission(self, request, view):
        return Parent.objects.filter(user=request.user).exists()

class IsMentor(permissions.BasePermission):
    """
    Custom permission to only allow verified mentors
    """
    def has_permission(self, request, view):
        return Mentor.objects.filter(user=request.user, is_verified=True).exists()

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it
    """
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user