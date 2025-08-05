from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.contenttypes.models import ContentType

# Create your models here.

'''卖家模型类'''
class Seller(models.Model):
    shop_name = models.CharField(max_length=100, unique=True, verbose_name="店铺名称")
    avatar = models.ImageField(
        upload_to='sellers/avatars/',  # 头像保存路径
        null=False, blank=False,
        verbose_name="卖家头像",
        default='sellers/avatars/img.png'
    )
    created_at = models.DateTimeField(auto_now_add=True)

'''类别模型类'''
class Category(models.Model):
    title = models.CharField(max_length=100)

'''商店中的商品模型类'''
class ShopProduct(models.Model):
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, related_name='shop_products')
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

'''商品模型类'''
class Product(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(decimal_places=2, max_digits=10)
    image = models.ImageField(  # 商品主图
        upload_to='products/images/',
        null=True,
        blank=True,
        verbose_name="商品图片"
    )
    inventory = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)]  # 库存不能为负数
    )
    last_update = models.DateTimeField(auto_now=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    seller = models.ForeignKey(  # 关联卖家
        Seller,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name="所属卖家"
    )
    sale = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)] )

'''用户模型类'''
class Customer(models.Model):
    username = models.CharField(max_length=18, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=18)
    avatar = models.ImageField(
        upload_to='customers/avatars/',
        null=False,
        blank=False,
        verbose_name="买家头像",
        default='customers/avatars/img.png',
    )
    birth_date = models.DateField(null=True)
    GENDER = {'F':'女', 'M':'男', 'N':'未知'}
    gender = models.CharField(max_length=1, choices=GENDER, default='N')
    pocket = models.ForeignKey('Pocket',unique=True, on_delete=models.CASCADE, null=True, related_name='owner')
    address = models.ForeignKey('Address', on_delete=models.CASCADE, related_name='receiver', null=True)

'''订单模型类'''
class Order(models.Model):
    placed_at = models.DateTimeField(auto_now=True)
    PAYMENT_STATUS = {'ING':'未支付',
                      'DONE':'支付完成',
                      'FAIL':'支付失败'}
    payment_status = models.CharField(max_length=4, choices=PAYMENT_STATUS, default='ING')
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    SHIPPING_STATUS = {
        'NOT': '未发货',
        'ING':'送货中',
        'DONE':'已送达',
    }
    shipping_status = models.CharField(max_length=4, choices=SHIPPING_STATUS, default='NOT')
    address = models.ForeignKey('Address', on_delete=models.PROTECT,default='')
    quantity = models.IntegerField(default=1)
    total_price = models.DecimalField(decimal_places=2, max_digits=10)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    seller = models.ForeignKey(Seller, on_delete=models.PROTECT,default='')


'''地址模型类'''
class Address(models.Model):
    street = models.CharField(max_length=100, default='未设置')
    city = models.CharField(max_length=100, default='未设置')
    state = models.CharField(max_length=100, default='未设置')
    customer = models.ForeignKey(Customer, primary_key=True, on_delete=models.CASCADE, related_name='addresses',unique=True)  # Customer被删除后，Address也被删除

'''购物车模型类'''
class Cart(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, default=1)

'''购物车条目模型'''
class CartItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(decimal_places=2, max_digits=10)

'''评论模型类'''
class Comment(models.Model):
    COMMENT_TYPE_CHOICES = [
        ('customer', '买家评论'),
        ('seller', '卖家评论'),
        ('other', '路人评论')
    ]

    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="买家")
    seller = models.ForeignKey(Seller, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="卖家")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="商品")
    comment_type = models.CharField(max_length=10, choices=COMMENT_TYPE_CHOICES, verbose_name="评论类型")
    content = models.TextField(verbose_name="评论内容")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="评论时间")
    reply = models.ForeignKey(
        'Comment',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='replies',  # 添加反向关系名称
        verbose_name="回复对象",
        default=''
    )

'''钱包模型类'''
class Pocket(models.Model):
    name = models.CharField(max_length=100)
    password = models.CharField(max_length=6)
    amount = models.DecimalField(decimal_places=2, max_digits=10, default=0)

'''付款记录模型类'''
class Record(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    object = models.ForeignKey(Pocket, on_delete=models.CASCADE, related_name='receive_record')
    pocket = models.ForeignKey(Pocket, on_delete=models.CASCADE, related_name='paid_record')
    money = models.DecimalField(decimal_places=2, max_digits=10, default=0)
