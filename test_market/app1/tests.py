from decimal import Decimal

from django.contrib.auth.hashers import check_password, make_password
from django.test import TestCase
from django.urls import reverse

from .models import Address, Cart, CartItem, Category, Customer, Order, Pocket, Product, Seller


class MarketFlowTests(TestCase):
    def create_customer(self, username, amount="999999.00", raw_password="password123"):
        pocket = Pocket.objects.create(name=username, password="999999", amount=Decimal(amount))
        customer = Customer.objects.create(
            username=username,
            email=f"{username}@example.com",
            password=make_password(raw_password),
            pocket=pocket,
        )
        Address.objects.create(customer=customer, state="中国", city="上海", street="测试路 1 号")
        return customer

    def login_as(self, customer):
        session = self.client.session
        session["user_id"] = customer.id
        session["username"] = customer.username
        session.save()

    def create_product(self, seller_customer, price="10.00", inventory=5):
        seller = Seller.objects.create(customer=seller_customer, shop_name=f"{seller_customer.username}的店铺")
        category = Category.objects.create(title="测试分类")
        return Product.objects.create(
            title="测试商品",
            description="用于自动化测试",
            price=Decimal(price),
            inventory=inventory,
            category=category,
            seller=seller,
        )

    def test_legacy_plain_password_login_upgrades_to_hash(self):
        customer = Customer.objects.create(
            username="legacy",
            email="legacy@example.com",
            password="password123",
        )

        response = self.client.post(
            reverse("login"),
            {"username": "legacy", "password": "password123"},
        )

        self.assertEqual(response.status_code, 302)
        customer.refresh_from_db()
        self.assertTrue(check_password("password123", customer.password))

    def test_checkout_transfers_full_line_total_to_seller(self):
        buyer = self.create_customer("buyer", amount="100.00")
        seller_customer = self.create_customer("seller", amount="0.00")
        product = self.create_product(seller_customer, price="10.00", inventory=5)
        cart = Cart.objects.create(customer=buyer)
        CartItem.objects.create(cart=cart, product=product, quantity=3, unit_price=product.price)
        self.login_as(buyer)

        response = self.client.post(reverse("checkout"), {"payment_password": "999999"})

        self.assertEqual(response.status_code, 302)
        buyer.pocket.refresh_from_db()
        seller_customer.pocket.refresh_from_db()
        product.refresh_from_db()
        self.assertEqual(buyer.pocket.amount, Decimal("70.00"))
        self.assertEqual(seller_customer.pocket.amount, Decimal("30.00"))
        self.assertEqual(product.inventory, 2)
        self.assertEqual(Order.objects.get().total_price, Decimal("30.00"))
        self.assertFalse(CartItem.objects.exists())

    def test_add_order_legacy_endpoint_does_not_create_free_order(self):
        buyer = self.create_customer("buyer2", amount="100.00")
        seller_customer = self.create_customer("seller2", amount="0.00")
        product = self.create_product(seller_customer, price="10.00", inventory=5)
        self.login_as(buyer)

        response = self.client.get(
            reverse("add_order"),
            {"product_id": product.id, "status": "DONE", "quantity": 1},
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Order.objects.exists())
