from django.contrib import admin
from .models import Provider, Barrel, Invoice, InvoiceLine

@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "tax_id")

@admin.register(Barrel)
class BarrelAdmin(admin.ModelAdmin):
    list_display = ("id", "provider", "number", "oil_type", "liters", "billed")
    list_filter = ("billed", "oil_type")
    search_fields = ("number", "oil_type", "provider__name")

class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("id", "provider", "invoice_no", "issued_on")
    inlines = [InvoiceLineInline]
