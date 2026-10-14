from django.utils import timezone

from rest_framework import viewsets, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView


from .models import PitcherOuting
from .permissions import IsStaffRole
from .serializers import PitcherOutingSerializer, MeSerializer, RegisterSerializer, RoleTokenSerializer, PitcherDailyCheckIn


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    return Response({"status": "ok"})

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

class LoginView(TokenObtainPairView):
    serializer_class = RoleTokenSerializer

class MeView(generics.RetrieveAPIView):
    serializer_class = MeSerializer

    def get_object(self):
        return self.request.user

class PitcherOutingViewSet(viewsets.ModelViewSet):
    queryset = PitcherOuting.objects.select_related("pitcher")
    serializer_class = PitcherOutingSerializer
    permission_classes = [IsStaffRole]
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
