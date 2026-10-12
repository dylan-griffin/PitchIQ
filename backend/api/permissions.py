from rest_framework.permissions import BasePermission
from .models import Role

class HasRole(BasePermission):
    allowed_roles: tuple = ()

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role in self.allowed_roles)

class IsPitcher(HasRole):
    allowed_roles = (Role.PITCHER,)

class IsAdminRole(HasRole):
    allowed_roles = (Role.ADMIN,)

class IsStaffRole(HasRole):
    allowed_roles = (Role.MANAGER, Role.ADMIN)