from django.contrib.auth import get_user_model
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .serializers import SignupSerializer, UserSerializer

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.select_related("provider").all().order_by("id")

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return self.queryset
        if user.provider_id is None:
            return User.objects.filter(id=user.id)
        return self.queryset.filter(provider_id=user.provider_id)

    def get_serializer_class(self):
        if self.action == "signup":
            return SignupSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        user = self.request.user
        if user.is_superuser:
            serializer.save()
            return
        if user.provider_id is None:
            raise PermissionDenied("User is not linked to any provider.")
        serializer.save(provider_id=user.provider_id)

    @action(
        detail=False,
        methods=["post"],
        url_path="signup",
        permission_classes=[AllowAny],
        authentication_classes=[],
    )
    def signup(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        output = UserSerializer(user, context={"request": request})
        return Response(output.data, status=status.HTTP_201_CREATED)
