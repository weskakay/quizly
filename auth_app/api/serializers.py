from django.contrib.auth.models import User
from rest_framework import serializers


class RegistrationSerializer(serializers.ModelSerializer):
    """Validates the sign-up data and creates a new user."""

    confirmed_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'confirmed_password']
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True, 'allow_blank': False},
        }

    def validate_email(self, value):
        """Rejects an email address that is already taken."""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('This email is already in use.')
        return value

    def validate(self, data):
        """Checks that both passwords match."""
        if data['password'] != data['confirmed_password']:
            raise serializers.ValidationError(
                {'confirmed_password': 'Passwords do not match.'}
            )
        return data

    def create(self, validated_data):
        """Creates the user with a hashed password."""
        validated_data.pop('confirmed_password')
        return User.objects.create_user(**validated_data)

    def to_representation(self, instance):
        """Answers with a short confirmation instead of the user data."""
        return {'detail': 'User created successfully!'}
