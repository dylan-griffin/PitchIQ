from rest_framework import serializers
from .models import PitcherOuting
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User

## For registering or creating a new user
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "role"]
        read_only_fields = ["id", "role"]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

## For getting an authenticated user's information
class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "team"]
        read_only_fields = fields

## Generating a JWT token
class RoleTokenSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        return token

class PitcherOutingSerializer(serializers.ModelSerializer):
    pitcher_username = serializers.CharField(source="pitcher.username", read_only=True)

    class Meta:
        model = PitcherOuting
        fields = [
            "id",
            "pitcher",
            "pitcher_username",
            "outing_type",
            "date",
            "pitch_count",
            "avg_velocity",
            "rest_days",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]