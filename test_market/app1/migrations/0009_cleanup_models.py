import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


def normalize_categories(apps, schema_editor):
    Category = apps.get_model("app1", "Category")
    Product = apps.get_model("app1", "Product")
    seen = {}

    for category in Category.objects.order_by("id"):
        title = (category.title or "未分类").strip() or "未分类"
        if title in seen:
            Product.objects.filter(category=category).update(category=seen[title])
            category.delete()
            continue
        if title != category.title:
            category.title = title
            category.save(update_fields=["title"])
        seen[title] = category


def merge_duplicate_carts(apps, schema_editor):
    Cart = apps.get_model("app1", "Cart")
    CartItem = apps.get_model("app1", "CartItem")

    for customer_id in Cart.objects.values_list("customer_id", flat=True).distinct():
        carts = list(Cart.objects.filter(customer_id=customer_id).order_by("id"))
        if not carts:
            continue
        keep = carts[0]
        for duplicate in carts[1:]:
            CartItem.objects.filter(cart=duplicate).update(cart=keep)
            duplicate.delete()


def merge_duplicate_cart_items(apps, schema_editor):
    CartItem = apps.get_model("app1", "CartItem")
    seen = {}

    for item in CartItem.objects.order_by("cart_id", "product_id", "id"):
        key = (item.cart_id, item.product_id)
        existing = seen.get(key)
        if existing is None:
            seen[key] = item
            continue
        existing.quantity += item.quantity
        existing.save(update_fields=["quantity"])
        item.delete()


def backfill_seller_customer(apps, schema_editor):
    Seller = apps.get_model("app1", "Seller")
    Customer = apps.get_model("app1", "Customer")

    used_names = set(Seller.objects.exclude(shop_name="").values_list("shop_name", flat=True))
    for seller in Seller.objects.order_by("id"):
        customer = Customer.objects.filter(id=seller.id).first()
        if customer and not seller.customer_id:
            seller.customer = customer
        if not seller.shop_name:
            base_name = f"{customer.username}的店铺" if customer else f"店铺{seller.id}"
            shop_name = base_name
            index = 2
            while shop_name in used_names:
                shop_name = f"{base_name}-{index}"
                index += 1
            seller.shop_name = shop_name
            used_names.add(shop_name)
        seller.save()


class Migration(migrations.Migration):
    dependencies = [
        ("app1", "0008_alter_comment_reply"),
    ]

    operations = [
        migrations.AddField(
            model_name="seller",
            name="customer",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="seller_profile",
                to="app1.customer",
            ),
        ),
        migrations.RunPython(normalize_categories, migrations.RunPython.noop),
        migrations.RunPython(merge_duplicate_carts, migrations.RunPython.noop),
        migrations.RunPython(merge_duplicate_cart_items, migrations.RunPython.noop),
        migrations.RunPython(backfill_seller_customer, migrations.RunPython.noop),
        migrations.DeleteModel(name="ShopProduct"),
        migrations.RemoveField(model_name="customer", name="address"),
        migrations.AlterField(
            model_name="address",
            name="customer",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                primary_key=True,
                related_name="address",
                serialize=False,
                to="app1.customer",
            ),
        ),
        migrations.AlterField(
            model_name="category",
            name="title",
            field=models.CharField(db_index=True, max_length=100, unique=True),
        ),
        migrations.AlterField(
            model_name="cart",
            name="customer",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="cart",
                to="app1.customer",
            ),
        ),
        migrations.AlterField(
            model_name="cartitem",
            name="cart",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="items",
                to="app1.cart",
            ),
        ),
        migrations.AlterField(
            model_name="cartitem",
            name="product",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="cart_items",
                to="app1.product",
            ),
        ),
        migrations.AlterField(
            model_name="cartitem",
            name="quantity",
            field=models.PositiveIntegerField(
                default=1,
                validators=[django.core.validators.MinValueValidator(1)],
            ),
        ),
        migrations.AlterField(
            model_name="cartitem",
            name="unit_price",
            field=models.DecimalField(
                decimal_places=2,
                max_digits=10,
                validators=[django.core.validators.MinValueValidator(0)],
            ),
        ),
        migrations.AddConstraint(
            model_name="cartitem",
            constraint=models.UniqueConstraint(
                fields=("cart", "product"),
                name="unique_product_per_cart",
            ),
        ),
        migrations.AlterField(
            model_name="comment",
            name="customer",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="comments",
                to="app1.customer",
                verbose_name="买家",
            ),
        ),
        migrations.AlterField(
            model_name="comment",
            name="comment_type",
            field=models.CharField(
                choices=[
                    ("customer", "买家评论"),
                    ("seller", "卖家评论"),
                    ("other", "路人评论"),
                ],
                default="customer",
                max_length=10,
                verbose_name="评论类型",
            ),
        ),
        migrations.AlterField(
            model_name="comment",
            name="product",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="comments",
                to="app1.product",
                verbose_name="商品",
            ),
        ),
        migrations.AlterField(
            model_name="comment",
            name="reply",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="replies",
                to="app1.comment",
                verbose_name="回复对象",
            ),
        ),
        migrations.AlterField(
            model_name="comment",
            name="seller",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="comments",
                to="app1.seller",
                verbose_name="卖家",
            ),
        ),
        migrations.AlterField(
            model_name="customer",
            name="birth_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="customer",
            name="password",
            field=models.CharField(max_length=128),
        ),
        migrations.AlterField(
            model_name="customer",
            name="pocket",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="owner",
                to="app1.pocket",
            ),
        ),
        migrations.AlterField(
            model_name="order",
            name="placed_at",
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name="order",
            name="address",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="orders",
                to="app1.address",
            ),
        ),
        migrations.AlterField(
            model_name="order",
            name="customer",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="orders",
                to="app1.customer",
            ),
        ),
        migrations.AlterField(
            model_name="order",
            name="product",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="orders",
                to="app1.product",
            ),
        ),
        migrations.AlterField(
            model_name="order",
            name="quantity",
            field=models.PositiveIntegerField(
                default=1,
                validators=[django.core.validators.MinValueValidator(1)],
            ),
        ),
        migrations.AlterField(
            model_name="order",
            name="seller",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="sales_orders",
                to="app1.seller",
            ),
        ),
        migrations.AlterField(
            model_name="pocket",
            name="amount",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=10,
                validators=[django.core.validators.MinValueValidator(0)],
            ),
        ),
        migrations.AlterField(
            model_name="pocket",
            name="password",
            field=models.CharField(
                max_length=6,
                validators=[
                    django.core.validators.RegexValidator(
                        "^\\d{6}$",
                        "支付密码必须是 6 位数字",
                    )
                ],
            ),
        ),
        migrations.AlterField(
            model_name="product",
            name="category",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="products",
                to="app1.category",
            ),
        ),
        migrations.AlterField(
            model_name="product",
            name="inventory",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="product",
            name="price",
            field=models.DecimalField(
                decimal_places=2,
                max_digits=10,
                validators=[django.core.validators.MinValueValidator(0)],
            ),
        ),
        migrations.AlterField(
            model_name="product",
            name="sale",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RenameField(
            model_name="record",
            old_name="object",
            new_name="receiver",
        ),
        migrations.RenameField(
            model_name="record",
            old_name="pocket",
            new_name="payer",
        ),
        migrations.AlterField(
            model_name="record",
            name="money",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=10,
                validators=[django.core.validators.MinValueValidator(0)],
            ),
        ),
        migrations.AlterField(
            model_name="record",
            name="payer",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="paid_records",
                to="app1.pocket",
            ),
        ),
        migrations.AlterField(
            model_name="record",
            name="receiver",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="received_records",
                to="app1.pocket",
            ),
        ),
        migrations.AlterModelOptions(
            name="address",
            options={"verbose_name": "地址", "verbose_name_plural": "地址"},
        ),
        migrations.AlterModelOptions(
            name="cart",
            options={"verbose_name": "购物车", "verbose_name_plural": "购物车"},
        ),
        migrations.AlterModelOptions(
            name="cartitem",
            options={"verbose_name": "购物车条目", "verbose_name_plural": "购物车条目"},
        ),
        migrations.AlterModelOptions(
            name="category",
            options={"ordering": ["title"], "verbose_name": "商品分类", "verbose_name_plural": "商品分类"},
        ),
        migrations.AlterModelOptions(
            name="comment",
            options={"ordering": ["-created_at"], "verbose_name": "评论", "verbose_name_plural": "评论"},
        ),
        migrations.AlterModelOptions(
            name="customer",
            options={"ordering": ["username"], "verbose_name": "用户", "verbose_name_plural": "用户"},
        ),
        migrations.AlterModelOptions(
            name="order",
            options={"ordering": ["-placed_at"], "verbose_name": "订单", "verbose_name_plural": "订单"},
        ),
        migrations.AlterModelOptions(
            name="pocket",
            options={"verbose_name": "钱包", "verbose_name_plural": "钱包"},
        ),
        migrations.AlterModelOptions(
            name="product",
            options={"ordering": ["-sale", "-last_update"], "verbose_name": "商品", "verbose_name_plural": "商品"},
        ),
        migrations.AlterModelOptions(
            name="record",
            options={"ordering": ["-created"], "verbose_name": "付款记录", "verbose_name_plural": "付款记录"},
        ),
        migrations.AlterModelOptions(
            name="seller",
            options={"ordering": ["shop_name"], "verbose_name": "卖家", "verbose_name_plural": "卖家"},
        ),
    ]
