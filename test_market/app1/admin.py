from django.contrib import admin

from .models import Address, Cart, CartItem, Category, Comment, Customer, Order, Pocket, Product, Record, Seller


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "gender")
    search_fields = ("username", "email")


@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    list_display = ("shop_name", "customer", "created_at")
    search_fields = ("shop_name", "customer__username")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("title", "seller", "category", "price", "inventory", "sale")
    list_filter = ("category", "seller")
    search_fields = ("title", "description", "seller__shop_name")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "customer", "seller", "payment_status", "shipping_status", "total_price", "placed_at")
    list_filter = ("payment_status", "shipping_status")
    search_fields = ("product__title", "customer__username", "seller__shop_name")


admin.site.register(Address)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Category)
admin.site.register(Comment)
admin.site.register(Pocket)
admin.site.register(Record)
