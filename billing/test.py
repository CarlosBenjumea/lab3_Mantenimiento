from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db.models import ProtectedError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from billing.models import Barrel, Invoice, InvoiceLine, Provider

User = get_user_model()

class Lab3BaseAPITestCase(APITestCase):
    def create_provider(self, name="Provider", tax_id="TAX-001", address="Main St 1"):
        return Provider.objects.create(name=name, tax_id=tax_id, address=address)

    def create_user(
        self,
        username="user",
        password="strongpass123",
        provider=None,
        is_superuser=False,
        is_staff=False,
        first_name="Test",
        last_name="User",
        email=None,
    ):
        if email is None:
            email = f"{username}@example.com"
        return User.objects.create_user(
            username=username,
            password=password,
            provider=provider,
            is_superuser=is_superuser,
            is_staff=is_staff or is_superuser,
            first_name=first_name,
            last_name=last_name,
            email=email,
        )

    def create_barrel(
        self,
        provider,
        number="B-001",
        oil_type="Olive",
        liters=100,
        billed=False,
    ):
        return Barrel.objects.create(
            provider=provider,
            number=number,
            oil_type=oil_type,
            liters=liters,
            billed=billed,
        )

    def create_invoice(self, provider, invoice_no="INV-001", issued_on=None):
        if issued_on is None:
            issued_on = date.today()
        return Invoice.objects.create(
            provider=provider,
            invoice_no=invoice_no,
            issued_on=issued_on,
        )

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

class SignupIntegrationTests(Lab3BaseAPITestCase):
    def test_signup_without_first_name_and_last_name_returns_400(self):
        payload = {
            "username": "missingnames",
            "password": "strongpass123",
            "email": "missingnames@example.com",
        }

        response = self.client.post(reverse("user-signup"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("first_name", response.data)
        self.assertIn("last_name", response.data)
        self.assertFalse(User.objects.filter(username="missingnames").exists())

    def test_signup_with_valid_payload_returns_201_and_names_are_persisted(self):
        payload = {
            "username": "newuser",
            "password": "strongpass123",
            "first_name": "New",
            "last_name": "User",
            "email": "newuser@example.com",
        }

        response = self.client.post(reverse("user-signup"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["username"], payload["username"])
        self.assertEqual(response.data["first_name"], payload["first_name"])
        self.assertEqual(response.data["last_name"], payload["last_name"])
        self.assertNotIn("password", response.data)
        created_user = User.objects.get(username=payload["username"])
        self.assertEqual(created_user.first_name, payload["first_name"])
        self.assertEqual(created_user.last_name, payload["last_name"])
        self.assertTrue(created_user.check_password(payload["password"]))

class InvoiceAddLineIntegrationTests(Lab3BaseAPITestCase):
    def test_adding_a_barrel_from_another_provider_returns_400_and_does_not_create_line(self):
        provider_a = self.create_provider(name="Provider A", tax_id="TAX-A")
        provider_b = self.create_provider(name="Provider B", tax_id="TAX-B")
        user_a = self.create_user(username="usera", provider=provider_a)
        invoice_a = self.create_invoice(provider=provider_a, invoice_no="INV-A-001")
        foreign_barrel = self.create_barrel(
            provider=provider_b,
            number="B-B-001",
            liters=150,
            billed=False,
        )
        self.authenticate(user_a)

        payload = {
            "barrel": foreign_barrel.id,
            "liters": foreign_barrel.liters,
            "unit_price": "2.50",
            "description": "Full barrel billing",
        }

        response = self.client.post(
            reverse("invoice-add-line", args=[invoice_a.id]),
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)
        self.assertEqual(InvoiceLine.objects.count(), 0)
        foreign_barrel.refresh_from_db()
        self.assertFalse(foreign_barrel.billed)

class InvoiceProviderScopingIntegrationTests(Lab3BaseAPITestCase):
    def test_invoice_list_returns_only_invoices_for_logged_in_users_provider(self):
        provider_a = self.create_provider(name="Provider A", tax_id="TAX-A")
        provider_b = self.create_provider(name="Provider B", tax_id="TAX-B")
        user_a = self.create_user(username="usera", provider=provider_a)
        invoice_a1 = self.create_invoice(provider=provider_a, invoice_no="INV-A-001")
        invoice_a2 = self.create_invoice(provider=provider_a, invoice_no="INV-A-002")
        self.create_invoice(provider=provider_b, invoice_no="INV-B-001")
        self.authenticate(user_a)
        response = self.client.get(reverse("invoice-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item["id"] for item in response.data}
        self.assertEqual(returned_ids, {invoice_a1.id, invoice_a2.id})
        self.assertEqual(len(response.data), 2)

    def test_invoice_detail_for_other_provider_returns_404(self):
        provider_a = self.create_provider(name="Provider A", tax_id="TAX-A")
        provider_b = self.create_provider(name="Provider B", tax_id="TAX-B")
        user_a = self.create_user(username="usera", provider=provider_a)
        foreign_invoice = self.create_invoice(provider=provider_b, invoice_no="INV-B-001")
        self.authenticate(user_a)
        response = self.client.get(reverse("invoice-detail", args=[foreign_invoice.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

class BarrelCreationIntegrationTests(Lab3BaseAPITestCase):
    def test_creating_barrel_ignores_provider_in_payload_and_uses_logged_in_users_provider(self):
        provider_a = self.create_provider(name="Provider A", tax_id="TAX-A")
        provider_b = self.create_provider(name="Provider B", tax_id="TAX-B")
        user_a = self.create_user(username="usera", provider=provider_a)
        self.authenticate(user_a)

        payload = {
            "provider": provider_b.id,
            "number": "A-NEW-001",
            "oil_type": "Sunflower",
            "liters": 220,
            "billed": True,
        }

        response = self.client.post(reverse("barrel-list"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_barrel = Barrel.objects.get(id=response.data["id"])
        self.assertEqual(created_barrel.provider_id, provider_a.id)
        self.assertEqual(response.data["provider"], provider_a.id)

class ProviderEndpointIntegrationTests(Lab3BaseAPITestCase):
    def test_provider_list_as_admin_returns_all_providers_and_aggregated_fields(self):
        provider_a = self.create_provider(name="Provider A", tax_id="TAX-A")
        provider_b = self.create_provider(name="Provider B", tax_id="TAX-B")
        self.create_barrel(provider=provider_a, number="A-1", liters=100, billed=True)
        self.create_barrel(provider=provider_a, number="A-2", liters=80, billed=False)
        self.create_barrel(provider=provider_b, number="B-1", liters=50, billed=False)
        admin = self.create_user(username="admin", is_superuser=True, is_staff=True)
        self.authenticate(admin)
        response = self.client.get(reverse("provider-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item["id"] for item in response.data}
        self.assertIn(provider_a.id, returned_ids)
        self.assertIn(provider_b.id, returned_ids)

        provider_a_data = next(item for item in response.data if item["id"] == provider_a.id)
        provider_b_data = next(item for item in response.data if item["id"] == provider_b.id)

        self.assertEqual(provider_a_data["name"], provider_a.name)
        self.assertEqual(provider_a_data["tax_id"], provider_a.tax_id)
        self.assertEqual(provider_a_data["billed_liters"], 100)
        self.assertEqual(provider_a_data["liters_to_bill"], 80)
        self.assertEqual(provider_b_data["billed_liters"], 0)
        self.assertEqual(provider_b_data["liters_to_bill"], 50)

    def test_provider_list_as_regular_user_returns_only_own_provider(self):
        provider_a = self.create_provider(name="Provider A", tax_id="TAX-A")
        provider_b = self.create_provider(name="Provider B", tax_id="TAX-B")
        self.create_barrel(provider=provider_a, number="A-1", liters=120, billed=True)
        self.create_barrel(provider=provider_a, number="A-2", liters=30, billed=False)
        self.create_barrel(provider=provider_b, number="B-1", liters=999, billed=False)
        user_a = self.create_user(username="usera", provider=provider_a)
        self.authenticate(user_a)
        response = self.client.get(reverse("provider-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], provider_a.id)
        self.assertEqual(response.data[0]["billed_liters"], 120)
        self.assertEqual(response.data[0]["liters_to_bill"], 30)

    def test_provider_detail_as_admin_returns_provider_data(self):
        provider = self.create_provider(name="Provider A", tax_id="TAX-A")
        self.create_barrel(provider=provider, number="A-1", liters=40, billed=True)
        self.create_barrel(provider=provider, number="A-2", liters=60, billed=False)
        admin = self.create_user(username="admin", is_superuser=True, is_staff=True)
        self.authenticate(admin)
        response = self.client.get(reverse("provider-detail", args=[provider.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], provider.id)
        self.assertEqual(response.data["name"], provider.name)
        self.assertEqual(response.data["billed_liters"], 40)
        self.assertEqual(response.data["liters_to_bill"], 60)

    def test_provider_detail_for_other_provider_as_regular_user_returns_404(self):
        provider_a = self.create_provider(name="Provider A", tax_id="TAX-A")
        provider_b = self.create_provider(name="Provider B", tax_id="TAX-B")
        user_a = self.create_user(username="usera", provider=provider_a)
        self.authenticate(user_a)
        response = self.client.get(reverse("provider-detail", args=[provider_b.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

class DeleteRestrictionIntegrationTests(Lab3BaseAPITestCase):
    def test_deleting_a_barrel_that_is_already_linked_to_an_invoice_line_is_rejected(self):
        provider = self.create_provider(name="Provider A", tax_id="TAX-A")
        user = self.create_user(username="usera", provider=provider)
        barrel = self.create_barrel(provider=provider, number="A-1", liters=100, billed=True)
        invoice = self.create_invoice(provider=provider, invoice_no="INV-A-001")
        InvoiceLine.objects.create(
            invoice=invoice,
            barrel=barrel,
            liters=100,
            description="Full barrel billing",
            unit_price=Decimal("2.50"),
        )
        self.authenticate(user)
        response = self.client.delete(reverse("barrel-detail", args=[barrel.id]))
        self.assertIn(
            response.status_code,
            {status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT},
        )
        self.assertTrue(Barrel.objects.filter(id=barrel.id).exists())
