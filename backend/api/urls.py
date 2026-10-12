from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import PitcherOutingViewSet, health, RegisterView, LoginView, MeView

router = DefaultRouter()
router.register(r"outings", PitcherOutingViewSet, basename="outing")

urlpatterns = [
    path("health/", health),
    path("auth/register/", RegisterView.as_view()),
    path("auth/login/", LoginView.as_view()),
    path("auth/refresh/", TokenRefreshView.as_view()),
    path("auth/me/", MeView.as_view()),
    path("", include(router.urls)),
]
