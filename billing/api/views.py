from rest_framework import serializers, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import ProtectedError

from ..models import Provider, Barrel, Invoice
from .serializers import (
    ProviderSerializer,
    BarrelSerializer,
    InvoiceSerializer,
    InvoiceLineNestedSerializer,
    InvoiceLineCreateSerializer,
)
from .filters import InvoiceFilter


class ProviderViewSet(viewsets.ModelViewSet):
    serializer_class = ProviderSerializer
    queryset = Provider.objects.all().order_by("id")

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return self.queryset
        if user.provider_id is None:
            return Provider.objects.none()
        return self.queryset.filter(id=user.provider_id)

    def perform_create(self, serializer):
        if not self.request.user.is_superuser:
            raise PermissionDenied("Only superusers can create providers.")
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.is_superuser:
            raise PermissionDenied("Only superusers can delete providers.")
        super().perform_destroy(instance)


class BarrelViewSet(viewsets.ModelViewSet):
    serializer_class = BarrelSerializer
    queryset = Barrel.objects.select_related("provider").all().order_by("id")
    # Requirement: barrels endpoint without filters on billed/unbilled
    filter_backends = []

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return self.queryset
        if user.provider_id is None:
            return Barrel.objects.none()
        return self.queryset.filter(provider_id=user.provider_id)

    def perform_create(self, serializer):
        user = self.request.user
        if user.provider_id is None:
            raise PermissionDenied("User is not linked to any provider.")
        serializer.save(provider_id=user.provider_id)

    # añadimos un perform_destroy() que capture ProtectedError y devuelva un error HTTP manejado
    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise serializers.ValidationError(
                {"detail": "Cannot delete a barrel that is already linked to an invoice line."}
            )


class InvoiceViewSet(viewsets.ModelViewSet):
    serializer_class = InvoiceSerializer
    queryset = (
        Invoice.objects.select_related("provider")
        .prefetch_related("lines")
        .all()
        .order_by("-issued_on", "-id")
    )

    filter_backends = [DjangoFilterBackend]
    filterset_class = InvoiceFilter

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return self.queryset
        if user.provider_id is None:
            return Invoice.objects.none()
        return self.queryset.filter(provider_id=user.provider_id)

    def get_serializer_class(self):
        if self.action == "add_line":
            return InvoiceLineCreateSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        user = self.request.user
        if user.provider_id is None:
            raise PermissionDenied("User is not linked to any provider.")
        serializer.save(provider_id=user.provider_id)

    @extend_schema(
        request=InvoiceLineCreateSerializer,
        responses={201: InvoiceLineNestedSerializer},
    )
    @action(detail=True, methods=["post"], url_path="add-line")
    def add_line(self, request, *args, **kwargs):
        invoice = self.get_object()
        serializer = InvoiceLineCreateSerializer(
            data=request.data,
            context={"invoice": invoice},
        )
        serializer.is_valid(raise_exception=True)
        try:
            line = serializer.save()
        except ValueError as exc:
            raise serializers.ValidationError({"detail": str(exc)})

        output = InvoiceLineNestedSerializer(line)
        return Response(output.data, status=status.HTTP_201_CREATED)
