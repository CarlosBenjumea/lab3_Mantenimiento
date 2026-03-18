from decimal import Decimal
from django.db.models import Sum
from django.db.models.functions import Coalesce
from rest_framework import serializers
from ..models import Provider, Barrel, Invoice, InvoiceLine


class ProviderSerializer(serializers.ModelSerializer):
    billed_liters = serializers.SerializerMethodField()
    liters_to_bill = serializers.SerializerMethodField()

    def get_billed_liters(self, obj: Provider) -> int:
        return (
            obj.barrels.filter(billed=True).aggregate(
                total=Coalesce(Sum("liters"), 0)
            )["total"]
        )

    def get_liters_to_bill(self, obj: Provider) -> int:
        return (
            obj.barrels.filter(billed=False).aggregate(
                total=Coalesce(Sum("liters"), 0)
            )["total"]
        )

    class Meta:
        model = Provider
        fields = ["id", "name", "address", "tax_id", "billed_liters", "liters_to_bill"]


class BarrelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Barrel
        fields = ["id", "provider", "number", "oil_type", "liters", "billed"]
        read_only_fields = ["provider"]


class InvoiceLineNestedSerializer(serializers.ModelSerializer):
    # Requirement: return invoice lines WITHOUT the barrel object included.
    # We expose barrel_id only (not nested barrel details).
    barrel_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = InvoiceLine
        fields = ["id", "barrel_id", "liters", "description", "unit_price"]


class InvoiceLineCreateSerializer(serializers.ModelSerializer):
    liters = serializers.IntegerField(min_value=1)
    description = serializers.CharField(max_length=255)
    unit_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )

    class Meta:
        model = InvoiceLine
        fields = ["unit_price", "barrel", "liters", "description"]

    def create(self, validated_data: dict) -> InvoiceLine:
        invoice = self.context["invoice"]
        return invoice.add_line_for_barrel(
            barrel=validated_data["barrel"],
            liters=validated_data["liters"],
            unit_price_per_liter=validated_data["unit_price"],
            description=validated_data["description"],
        )


class InvoiceSerializer(serializers.ModelSerializer):
    lines = InvoiceLineNestedSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id",
            "provider",
            "invoice_no",
            "issued_on",
            "lines",
        ]
        read_only_fields = ["provider"]
