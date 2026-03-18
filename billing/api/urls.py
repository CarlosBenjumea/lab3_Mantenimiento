from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProviderViewSet, BarrelViewSet, InvoiceViewSet

router = DefaultRouter()
router.register(r"providers", ProviderViewSet, basename="provider")
router.register(r"barrels", BarrelViewSet, basename="barrel")
router.register(r"invoices", InvoiceViewSet, basename="invoice")

urlpatterns = [
    path("", include(router.urls)),
]
