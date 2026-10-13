from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    health,
    PitcherOutingViewSet,
    PitcherDailyCheckInViewSet,
)


router = DefaultRouter()
router.register(r"outings", PitcherOutingViewSet, basename="outing")
router.register(r"daily-check-ins", PitcherDailyCheckInViewSet, basename="daily-check-in")

urlpatterns = [
    path("health/", health),
    path("", include(router.urls)),
]
