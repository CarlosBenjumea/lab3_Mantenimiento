from django.contrib.auth import get_user_model
from rest_framework import serializers

from billing.models import Provider

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "password",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save(update_fields=["password"])
        return user


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "password",
            "first_name",
            "last_name",
            "email",
        ]
        read_only_fields = ["id"]

    def validate_first_name(self, value):
        if value == None or value == "":
            raise serializers.ValidationError('First name is required')
        return value
    
    # añadimos validación del last name
    def validate_last_name(self, value):
        if value is None or value == "":
            raise serializers.ValidationError("Last name is required.")
        return value

    def validate(self, attrs):
        errors = {}

        if attrs.get("first_name") in (None, ""):
            errors["first_name"] = "First name is required."
        if attrs.get("last_name") in (None, ""):
            errors["last_name"] = "Last name is required."

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user



    