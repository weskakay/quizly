from rest_framework.permissions import BasePermission


class IsQuizOwner(BasePermission):
    """Only the user who created a quiz may see or change it."""

    message = 'This quiz belongs to another user.'

    def has_object_permission(self, request, view, obj):
        """Compares the owner of the quiz with the logged in user."""
        return obj.owner_id == request.user.id
