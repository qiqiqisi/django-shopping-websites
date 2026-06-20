from django.core.validators import MinValueValidator, RegexValidator
from django.db import models


class Category(models.Model):
    title = models.CharField(max_length=100, unique=True, db_index=True)

    class Meta:
        ordering = ["title"]
        verbose_name = "商品分类"
        verbose_name_plural = "商品分类"

    def __str__(self):
        return self.title


class Pocket(models.Model):
    name = models.CharField(max_length=100)
    password = models.CharField(
        max_length=6,
        validators=[RegexValidator(r"^\d{6}$", "支付密码必须是 6 位数字")],
    )
    amount = models.DecimalField(
        decimal_places=2,
        max_digits=10,
        default=0,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        verbose_name = "钱包"
        verbose_name_plural = "钱包"

    def __str__(self):
        return f"{self.name}的钱包"


class Customer(models.Model):
    class Gender(models.TextChoices):
        FEMALE = "F", "女"
        MALE = "M", "男"
        UNKNOWN = "N", "未知"

    username = models.CharField(max_length=18, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    avatar = models.ImageField(
        upload_to="customers/avatars/",
        verbose_name="买家头像",
        default="customers/avatars/img.png",
    )
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=Gender.choices, default=Gender.UNKNOWN)
    pocket = models.OneToOneField(
        Pocket,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owner",
    )

    class Meta:
        ordering = ["username"]
        verbose_name = "用户"
        verbose_name_plural = "用户"

    def __str__(self):
        return self.username


class Seller(models.Model):
    customer = models.OneToOneField(
        Customer,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="seller_profile",
    )
    shop_name = models.CharField(max_length=100, unique=True, verbose_name="店铺名称")
    avatar = models.ImageField(
        upload_to="sellers/avatars/",
        verbose_name="卖家头像",
        default="sellers/avatars/img.png",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["shop_name"]
        verbose_name = "卖家"
        verbose_name_plural = "卖家"

    def __str__(self):
        return self.shop_name or f"店铺 #{self.pk}"


class Address(models.Model):
    customer = models.OneToOneField(
        Customer,
        primary_key=True,
        on_delete=models.CASCADE,
        related_name="address",
    )
    state = models.CharField(max_length=100, default="未设置")
    city = models.CharField(max_length=100, default="未设置")
    street = models.CharField(max_length=100, default="未设置")

    class Meta:
        verbose_name = "地址"
        verbose_name_plural = "地址"

    def __str__(self):
        return f"{self.state} {self.city} {self.street}"


class Product(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(
        decimal_places=2,
        max_digits=10,
        validators=[MinValueValidator(0)],
    )
    image = models.ImageField(
        upload_to="products/images/",
        null=True,
        blank=True,
        verbose_name="商品图片",
    )
    inventory = models.PositiveIntegerField(default=0)
    last_update = models.DateTimeField(auto_now=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    seller = models.ForeignKey(
        Seller,
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name="所属卖家",
    )
    sale = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-sale", "-last_update"]
        verbose_name = "商品"
        verbose_name_plural = "商品"

    @property
    def is_available(self):
        return self.inventory > 0

    def __str__(self):
        return self.title


class Order(models.Model):
    class PaymentStatus(models.TextChoices):
        PENDING = "ING", "未支付"
        DONE = "DONE", "支付完成"
        FAILED = "FAIL", "支付失败"

    class ShippingStatus(models.TextChoices):
        NOT_SHIPPED = "NOT", "未发货"
        SHIPPING = "ING", "送货中"
        DONE = "DONE", "已送达"

    placed_at = models.DateTimeField(auto_now_add=True)
    payment_status = models.CharField(
        max_length=4,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="orders")
    shipping_status = models.CharField(
        max_length=4,
        choices=ShippingStatus.choices,
        default=ShippingStatus.NOT_SHIPPED,
    )
    address = models.ForeignKey(Address, on_delete=models.PROTECT, related_name="orders")
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    total_price = models.DecimalField(decimal_places=2, max_digits=10)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="orders")
    seller = models.ForeignKey(Seller, on_delete=models.PROTECT, related_name="sales_orders")

    class Meta:
        ordering = ["-placed_at"]
        verbose_name = "订单"
        verbose_name_plural = "订单"

    def __str__(self):
        return f"订单 #{self.pk} - {self.product}"


class Cart(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name="cart")

    class Meta:
        verbose_name = "购物车"
        verbose_name_plural = "购物车"

    def __str__(self):
        return f"{self.customer}的购物车"


class CartItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="cart_items")
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(
        decimal_places=2,
        max_digits=10,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["cart", "product"], name="unique_product_per_cart")
        ]
        verbose_name = "购物车条目"
        verbose_name_plural = "购物车条目"

    @property
    def subtotal(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.product} x {self.quantity}"


class Comment(models.Model):
    class CommentType(models.TextChoices):
        CUSTOMER = "customer", "买家评论"
        SELLER = "seller", "卖家评论"
        OTHER = "other", "路人评论"

    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="comments",
        verbose_name="买家",
    )
    seller = models.ForeignKey(
        Seller,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="comments",
        verbose_name="卖家",
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="comments", verbose_name="商品")
    comment_type = models.CharField(
        max_length=10,
        choices=CommentType.choices,
        default=CommentType.CUSTOMER,
        verbose_name="评论类型",
    )
    content = models.TextField(verbose_name="评论内容")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="评论时间")
    reply = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="replies",
        verbose_name="回复对象",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "评论"
        verbose_name_plural = "评论"

    def __str__(self):
        return self.content[:30]


class Record(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    receiver = models.ForeignKey(Pocket, on_delete=models.CASCADE, related_name="received_records")
    payer = models.ForeignKey(Pocket, on_delete=models.CASCADE, related_name="paid_records")
    money = models.DecimalField(
        decimal_places=2,
        max_digits=10,
        default=0,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        ordering = ["-created"]
        verbose_name = "付款记录"
        verbose_name_plural = "付款记录"

    def __str__(self):
        return f"{self.payer} -> {self.receiver}: {self.money}"
