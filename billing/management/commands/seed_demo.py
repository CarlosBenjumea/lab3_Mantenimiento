from datetime import date
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from billing.models import Provider, Barrel, Invoice


class Command(BaseCommand):
    help = "Seed demo data (providers, barrels, invoices)"

    def handle(self, *args, **options):
        User = get_user_model()
        Provider.objects.all().delete()

        p = Provider.objects.create(
            name="Acme Oils",
            address="123 Industrial Ave",
            tax_id="TAX-123",
        )
        b1 = Barrel.objects.create(provider=p, number="B-001", oil_type="Olive", liters=200, billed=False)
        b2 = Barrel.objects.create(provider=p, number="B-002", oil_type="Sunflower", liters=150, billed=False)

        inv = Invoice.objects.create(provider=p, invoice_no="INV-0001", issued_on=date.today())
        inv.add_line_for_barrel(barrel=b1, liters=200, unit_price_per_liter=Decimal("3.50"), description="Olive oil barrel B-001")

        demo_user, _ = User.objects.get_or_create(username="demo")
        demo_user.provider = p
        demo_user.is_staff = True
        demo_user.set_password("demo1234")
        demo_user.save()

        self.stdout.write(self.style.SUCCESS("Demo data created."))
