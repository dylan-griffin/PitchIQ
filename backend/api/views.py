from rest_framework import viewsets
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated


from .models import PitcherOuting, PitcherDailyCheckIn
from .serializers import PitcherOutingSerializer, PitcherDailyCheckInSerializer


@api_view(["GET"])
def health(request):
    return Response({"status": "ok"})

class PitcherOutingViewSet(viewsets.ModelViewSet):
    queryset = PitcherOuting.objects.all()
    serializer_class = PitcherOutingSerializer
    filterset_fields = ["pitcher", "outing_type", "date"]

class PitcherDailyCheckInViewSet(viewsets.ModelViewSet):
    serializer_class = PitcherDailyCheckInSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PitcherDailyCheckIn.objects.filter(pitcher=self.request.user)

    def perform_create(self, serializer):
        today = timezone.localdate()
        already_checked_in  = PitcherDailyCheckIn.objects.filter(
            pitcher=self.request.user,
            date=today,).exists()

        if already_checked_in:
            raise ValidationError({"detail": "You have already already checked in."})

        serializer.save(
            pitcher=self.request.user,
            date=today,
        )
