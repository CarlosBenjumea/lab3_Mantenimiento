from __future__ import annotations

from decimal import Decimal
from django.db import models, transaction
from django.core.validators import MinValueValidator


class Provider(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField()
    tax_id = models.CharField(max_length=64)

    def __str__(self) -> str:
        return f"{self.name} ({self.tax_id})"

    def has_barrels_to_bill(self) -> bool:
        return self.barrels.filter(billed=False).exists()


class Barrel(models.Model):
    provider = models.ForeignKey(Provider, related_name="barrels", on_delete=models.CASCADE)
    number = models.CharField(max_length=64)
    oil_type = models.CharField(max_length=128)
    liters = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    billed = models.BooleanField(default=False)

    class Meta:
        unique_together = ("provider", "number")

    def __str__(self) -> str:
        return f"Barrel {self.number} ({self.oil_type})"


class Invoice(models.Model):
    provider = models.ForeignKey(Provider, related_name="invoices", on_delete=models.CASCADE)
    invoice_no = models.CharField(max_length=64, unique=True)
    issued_on = models.DateField()

    def __str__(self) -> str:
        return self.invoice_no

    @transaction.atomic
    def add_line_for_barrel(
        self,
        barrel: Barrel,
        liters: int,
        unit_price_per_liter: Decimal,
        description: str,
    ) -> "InvoiceLine":
        if liters <= 0:
            raise ValueError("liters must be > 0")
        if unit_price_per_liter <= 0:
            raise ValueError("unit_price must be > 0")

        # añadimos un if que asegura que el barrir viene del mismo proveedor  
        if barrel.provider_id != self.provider_id:
            raise ValueError("barrel provider must match invoice provider")

        # Business rule from the prompt:
        if barrel.liters != liters:
            raise ValueError("liters must equal barrel.liters to bill the full barrel")

        new_line = InvoiceLine.objects.create(
            invoice=self,
            barrel=barrel,
            liters=liters,
            unit_price=unit_price_per_liter,
            description=description,
        )
        barrel.billed = True
        barrel.save(update_fields=["billed"])
        return new_line


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, related_name="lines", on_delete=models.CASCADE)
    barrel = models.ForeignKey(Barrel, related_name="invoice_lines", on_delete=models.PROTECT)
    liters = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    description = models.CharField(max_length=255)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])

    def __str__(self) -> str:
        return f"Line {self.id} ({self.liters} L @ {self.unit_price})"
