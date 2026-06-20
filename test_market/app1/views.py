from decimal import Decimal, InvalidOperation
import random

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.hashers import check_password, identify_hasher, make_password
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render

from .models import Address, Cart, CartItem, Category, Comment, Customer, Order, Pocket, Product, Record, Seller


verification_code = {}
DEMO_INITIAL_BALANCE = Decimal("999999.00")
DEFAULT_PAYMENT_PASSWORD = "999999"


def send_verification_email(email):
    code = "".join(random.SystemRandom().choices("0123456789", k=6))
    send_mail(
        subject="您的验证码",
        message=f"您的验证码是：{code}，请勿泄露。",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )
    verification_code[email] = code
    return code


def get_current_customer(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    customer = Customer.objects.filter(id=user_id).first()
    if not customer:
        request.session.flush()
    return customer


def require_customer(request):
    customer = get_current_customer(request)
    if customer is None:
        messages.warning(request, "请先登录")
    return customer


def is_hashed_password(value):
    try:
        identify_hasher(value)
        return True
    except Exception:
        return False


def password_matches(customer, raw_password):
    if is_hashed_password(customer.password):
        return check_password(raw_password, customer.password)
    if customer.password == raw_password:
        customer.password = make_password(raw_password)
        customer.save(update_fields=["password"])
        return True
    return False


def unique_shop_name(base_name, seller_id=None):
    base_name = (base_name or "未命名店铺").strip() or "未命名店铺"
    name = base_name
    index = 2
    queryset = Seller.objects.all()
    if seller_id:
        queryset = queryset.exclude(id=seller_id)
    while queryset.filter(shop_name=name).exists():
        name = f"{base_name}-{index}"
        index += 1
    return name


def get_seller_for_customer(customer, create=True):
    try:
        return customer.seller_profile
    except Seller.DoesNotExist:
        legacy_seller = Seller.objects.filter(id=customer.id).first()
        if legacy_seller:
            legacy_seller.customer = customer
            if not legacy_seller.shop_name:
                legacy_seller.shop_name = unique_shop_name(f"{customer.username}的店铺", legacy_seller.id)
            legacy_seller.save()
            return legacy_seller
        if not create:
            return None
        return Seller.objects.create(
            customer=customer,
            shop_name=unique_shop_name(f"{customer.username}的店铺"),
        )


def ensure_pocket(customer, name=None):
    if customer.pocket_id:
        return Pocket.objects.get(id=customer.pocket_id)

    pocket, _ = Pocket.objects.get_or_create(
        id=customer.id,
        defaults={
            "name": name or customer.username,
            "password": DEFAULT_PAYMENT_PASSWORD,
            "amount": DEMO_INITIAL_BALANCE,
        },
    )
    customer.pocket = pocket
    customer.save(update_fields=["pocket"])
    return pocket


def ensure_seller_pocket(seller):
    if seller.customer_id:
        return ensure_pocket(seller.customer, seller.shop_name)
    pocket, _ = Pocket.objects.get_or_create(
        id=seller.id,
        defaults={
            "name": seller.shop_name or f"店铺{seller.id}",
            "password": DEFAULT_PAYMENT_PASSWORD,
            "amount": DEMO_INITIAL_BALANCE,
        },
    )
    return pocket


def get_customer_address(customer):
    try:
        return customer.address
    except Address.DoesNotExist:
        return None


def has_complete_address(customer):
    address = get_customer_address(customer)
    if not address:
        return False
    parts = [address.state, address.city, address.street]
    return all(part and part != "未设置" for part in parts)


def parse_money(value):
    try:
        money = Decimal(str(value))
    except (InvalidOperation, TypeError):
        return None
    return money if money >= 0 else None


def parse_positive_int(value, default=1):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(number, 1)


def paginate(request, items, per_page=8):
    paginator = Paginator(items, per_page)
    return paginator, paginator.get_page(request.GET.get("page"))


def login(request):
    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""
        customer = Customer.objects.filter(username=username).first()

        if customer and password_matches(customer, password):
            request.session["user_id"] = customer.id
            request.session["username"] = customer.username
            ensure_pocket(customer)
            get_seller_for_customer(customer)
            messages.success(request, "欢迎回来")
            return redirect("home")

        return render(request, "login.html", {"error": "用户名或密码错误"})

    return render(request, "login.html")


def register(request):
    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        email = (request.POST.get("email") or "").strip()
        password = request.POST.get("password") or ""
        user_code = (request.POST.get("verification_code") or "").strip()
        context = {"username": username, "email": email, "password": password}

        if "send_code" in request.POST:
            if not email:
                context["error"] = "请先填写邮箱"
                return render(request, "register.html", context)
            if Customer.objects.filter(email=email).exists():
                context["error"] = "该邮箱已注册"
                return render(request, "register.html", context)
            try:
                code = send_verification_email(email)
            except Exception as exc:
                context["error"] = f"验证码发送失败：{exc}"
            else:
                context["message"] = "验证码已发送，请查收邮箱。"
                if settings.EMAIL_BACKEND.endswith("console.EmailBackend"):
                    context["message"] = f"开发模式验证码：{code}"
            return render(request, "register.html", context)

        if len(username) < 3 or len(username) > 18 or len(password) < 8 or len(password) > 18:
            context["error"] = "用户名需 3-18 位，密码需 8-18 位"
            return render(request, "register.html", context)
        if Customer.objects.filter(username=username).exists():
            context["error"] = "该用户名已存在"
            return render(request, "register.html", context)
        if Customer.objects.filter(email=email).exists():
            context["error"] = "该邮箱已注册"
            return render(request, "register.html", context)
        if verification_code.get(email) != user_code:
            context["error"] = "验证码错误，请重新输入"
            return render(request, "register.html", context)

        with transaction.atomic():
            customer = Customer.objects.create(
                username=username,
                email=email,
                password=make_password(password),
                gender=Customer.Gender.UNKNOWN,
            )
            ensure_pocket(customer)
            get_seller_for_customer(customer)

        verification_code.pop(email, None)
        messages.success(request, "注册成功，请登录")
        return redirect("login")

    return render(request, "register.html")


def update(request):
    if request.method == "POST":
        email = (request.POST.get("email") or "").strip()
        new_username = (request.POST.get("username") or "").strip()
        new_password = request.POST.get("password") or ""
        user_code = (request.POST.get("verification_code") or "").strip()
        context = {"email": email, "username": new_username, "password": new_password}

        if "send-code" in request.POST:
            if not Customer.objects.filter(email=email).exists():
                context["error"] = "该邮箱未注册"
                return render(request, "update.html", context)
            try:
                code = send_verification_email(email)
            except Exception as exc:
                context["error"] = f"验证码发送失败：{exc}"
            else:
                context["message"] = "验证码已发送，请查收邮箱。"
                if settings.EMAIL_BACKEND.endswith("console.EmailBackend"):
                    context["message"] = f"开发模式验证码：{code}"
            return render(request, "update.html", context)

        if verification_code.get(email) != user_code:
            context["error"] = "验证码错误，请重新输入"
            return render(request, "update.html", context)
        if len(new_username) < 3 or len(new_username) > 18 or len(new_password) < 8 or len(new_password) > 18:
            context["error"] = "用户名需 3-18 位，密码需 8-18 位"
            return render(request, "update.html", context)

        customer = get_object_or_404(Customer, email=email)
        if new_username != customer.username and Customer.objects.filter(username=new_username).exists():
            context["error"] = "该用户名已被其他用户使用"
            return render(request, "update.html", context)

        customer.username = new_username
        customer.password = make_password(new_password)
        customer.save(update_fields=["username", "password"])
        verification_code.pop(email, None)
        messages.success(request, "账号已更新，请重新登录")
        return redirect("login")

    return render(request, "update.html")


def logout(request):
    request.session.flush()
    messages.success(request, "已退出登录")
    return redirect("login")


def home(request):
    customer = require_customer(request)
    if not customer:
        return redirect("login")

    products = Product.objects.select_related("category", "seller").filter(inventory__gt=0)
    paginator, page_obj = paginate(request, products)
    return render(
        request,
        "home.html",
        {"page_obj": page_obj, "paginator": paginator, "featured_count": products.count()},
    )


def person(request):
    customer = require_customer(request)
    if not customer:
        return redirect("login")

    if request.method == "POST":
        gender = request.POST.get("gender") or Customer.Gender.UNKNOWN
        if gender not in Customer.Gender.values:
            gender = Customer.Gender.UNKNOWN

        customer.gender = gender
        customer.birth_date = request.POST.get("birth_date") or None
        avatar = request.FILES.get("avatar")
        if avatar:
            customer.avatar = avatar
        customer.save()

        address, _ = Address.objects.get_or_create(customer=customer)
        address.state = (request.POST.get("state") or "").strip() or "未设置"
        address.city = (request.POST.get("city") or "").strip() or "未设置"
        address.street = (request.POST.get("street") or "").strip() or "未设置"
        address.save()

        messages.success(request, "个人信息已保存")
        return redirect("person")

    address = get_customer_address(customer)
    return render(
        request,
        "person.html",
        {
            "user_gender": customer.gender,
            "user_email": customer.email,
            "user_birth_date": customer.birth_date,
            "state": address.state if address else "",
            "city": address.city if address else "",
            "street": address.street if address else "",
        },
    )


def store(request):
    customer = require_customer(request)
    if not customer:
        return redirect("login")

    seller = get_seller_for_customer(customer)
    products = Product.objects.filter(seller=seller).select_related("category", "seller")
    paginator, page_obj = paginate(request, products)
    return render(
        request,
        "store.html",
        {
            "seller": seller,
            "store_name": seller.shop_name,
            "store_avatar": seller.avatar,
            "page_obj": page_obj,
            "paginator": paginator,
        },
    )


def store_set(request):
    customer = require_customer(request)
    if not customer:
        return redirect("login")
    seller = get_seller_for_customer(customer)

    if request.method == "POST":
        store_name = (request.POST.get("store_name") or "").strip()
        avatar = request.FILES.get("avatar")
        if not store_name:
            return render(request, "store_set.html", {"seller": seller, "error": "店铺名字不能为空"})
        if Seller.objects.exclude(id=seller.id).filter(shop_name=store_name).exists():
            return render(request, "store_set.html", {"seller": seller, "error": "店铺名字已被使用"})

        seller.shop_name = store_name
        if avatar:
            seller.avatar = avatar
        seller.save()
        messages.success(request, "店铺设置已保存")
        return redirect("store")

    return render(request, "store_set.html", {"seller": seller})


def update_product(request):
    customer = require_customer(request)
    if not customer:
        return redirect("login")
    seller = get_seller_for_customer(customer)

    if request.method != "POST":
        return render(request, "update_product.html")

    title = (request.POST.get("title") or "").strip()
    description = (request.POST.get("description") or "").strip()
    price = parse_money(request.POST.get("price"))
    inventory = parse_positive_int(request.POST.get("inventory"), default=0)
    category_title = (request.POST.get("category") or "").strip()
    image = request.FILES.get("image")

    if not all([title, description, category_title]) or price is None:
        messages.error(request, "请完整填写商品名称、描述、分类和有效价格")
        return redirect("update_product")

    category, _ = Category.objects.get_or_create(title=category_title)
    Product.objects.create(
        title=title,
        description=description,
        price=price,
        image=image,
        inventory=inventory,
        category=category,
        seller=seller,
    )
    messages.success(request, "商品已发布")
    return redirect("store")


def detail(request):
    product_id = request.GET.get("product_id")
    if not product_id:
        return HttpResponseBadRequest("商品详细信息需要商品 ID")

    product = get_object_or_404(
        Product.objects.select_related("category", "seller", "seller__customer"),
        pk=product_id,
    )
    customer = get_current_customer(request)
    is_owner = bool(customer and product.seller.customer_id == customer.id)
    can_purchase = bool(customer and not is_owner and product.inventory > 0)
    comments = product.comments.filter(reply=None).select_related("customer", "seller")

    context = {
        "product": product,
        "seller": product.seller,
        "can_purchase": can_purchase,
        "is_owner": is_owner,
        "comments": comments,
        "user_id": customer.id if customer else None,
    }

    up_comment_id = request.GET.get("up_comment_id")
    if up_comment_id:
        up_comment = Comment.objects.filter(id=up_comment_id).select_related("customer").first()
        if up_comment:
            context["up_content"] = up_comment.content
            context["up_user"] = up_comment.customer.username if up_comment.customer else "已注销用户"
            context["up_comment_id"] = up_comment_id

    return render(request, "detail.html", context)


def change_detail(request):
    customer = require_customer(request)
    if not customer:
        return redirect("login")

    product_id = request.POST.get("product_id") if request.method == "POST" else request.GET.get("product_id")
    product = get_object_or_404(Product.objects.select_related("seller", "category"), id=product_id)
    if product.seller.customer_id != customer.id:
        messages.error(request, "只能修改自己店铺的商品")
        return redirect(f"/store/detail/?product_id={product.id}")

    if request.method != "POST":
        return render(request, "change_detail.html", {"product": product})

    price = parse_money(request.POST.get("price"))
    inventory = parse_positive_int(request.POST.get("inventory"), default=0)
    category_title = (request.POST.get("category") or "").strip()
    if price is None or not category_title:
        messages.error(request, "请填写有效的价格和分类")
        return redirect(f"/change_detail/?product_id={product.id}")

    product.title = (request.POST.get("title") or "").strip() or product.title
    product.description = (request.POST.get("description") or "").strip()
    product.inventory = inventory
    product.price = price
    product.category, _ = Category.objects.get_or_create(title=category_title)
    image = request.FILES.get("image")
    if image:
        product.image = image
    product.save()
    messages.success(request, "商品信息已更新")
    return redirect(f"/store/detail/?product_id={product.id}")


def transfer(request):
    customer = require_customer(request)
    if not customer:
        return redirect("login")

    product_id = request.POST.get("product_id") if request.method == "POST" else request.GET.get("product_id")
    product = get_object_or_404(Product.objects.select_related("seller", "seller__customer"), id=product_id)

    if product.seller.customer_id == customer.id:
        messages.error(request, "不能购买自己店铺的商品")
        return redirect(f"/store/detail/?product_id={product.id}")
    if product.inventory <= 0:
        messages.error(request, "商品已售罄")
        return redirect(f"/store/detail/?product_id={product.id}")

    seller_name = product.seller.shop_name
    context = {"money": product.price, "payee_name": seller_name, "product_id": product.id}

    if request.method != "POST":
        return render(request, "transfer.html", context)

    if not has_complete_address(customer):
        context["error"] = "请先到个人中心设置完整地址"
        return render(request, "transfer.html", context)

    with transaction.atomic():
        product = Product.objects.select_for_update().select_related("seller", "seller__customer").get(id=product.id)
        payer = Pocket.objects.select_for_update().get(id=ensure_pocket(customer).id)
        receiver = Pocket.objects.select_for_update().get(id=ensure_seller_pocket(product.seller).id)

        if payer.password != request.POST.get("password"):
            context["error"] = "支付密码错误"
            return render(request, "transfer.html", context)
        if product.inventory <= 0:
            context["error"] = "商品已售罄"
            return render(request, "transfer.html", context)
        if payer.amount < product.price:
            context["error"] = "余额不足"
            return render(request, "transfer.html", context)

        product.inventory -= 1
        product.sale += 1
        product.save(update_fields=["inventory", "sale", "last_update"])

        payer.amount -= product.price
        receiver.amount += product.price
        payer.save(update_fields=["amount"])
        receiver.save(update_fields=["amount"])
        Record.objects.create(receiver=receiver, payer=payer, money=product.price)
        Order.objects.create(
            seller=product.seller,
            payment_status=Order.PaymentStatus.DONE,
            customer=customer,
            shipping_status=Order.ShippingStatus.NOT_SHIPPED,
            address=customer.address,
            quantity=1,
            total_price=product.price,
            product=product,
        )

    messages.success(request, "购买成功，订单已生成")
    return redirect("my_order")


def add_order(request):
    product_id = request.GET.get("product_id")
    messages.info(request, "请先完成支付，系统会自动生成订单")
    if product_id:
        return redirect(f"/transfer/?product_id={product_id}")
    return redirect("home")


def delete_order(request):
    customer = require_customer(request)
    if not customer:
        return redirect("login")
    order = get_object_or_404(Order, id=request.GET.get("order_id"), customer=customer)
    if order.shipping_status != Order.ShippingStatus.NOT_SHIPPED:
        messages.error(request, "订单已进入配送流程，不能删除")
    else:
        order.delete()
        messages.success(request, "订单已删除")
    return redirect("my_order")


def cart(request):
    customer = require_customer(request)
    if not customer:
        return redirect("login")

    my_cart, _ = Cart.objects.get_or_create(customer=customer)
    cart_items = my_cart.items.select_related("product", "product__seller").all()
    total = sum((item.subtotal for item in cart_items), Decimal("0"))
    return render(request, "cart.html", {"cart_items": cart_items, "total": total, "error": request.GET.get("error")})


def add_cart(request):
    customer = require_customer(request)
    if not customer:
        return redirect("login")

    product = get_object_or_404(Product.objects.select_related("seller"), id=request.GET.get("product_id"))
    if product.seller.customer_id == customer.id:
        messages.error(request, "不能把自己店铺的商品加入购物车")
        return redirect(f"/store/detail/?product_id={product.id}")
    if product.inventory <= 0:
        messages.error(request, "商品已售罄")
        return redirect(f"/store/detail/?product_id={product.id}")

    my_cart, _ = Cart.objects.get_or_create(customer=customer)
    item, created = CartItem.objects.get_or_create(
        cart=my_cart,
        product=product,
        defaults={"quantity": 1, "unit_price": product.price},
    )
    if not created:
        if item.quantity >= product.inventory:
            messages.warning(request, "购物车数量已达到当前库存")
        else:
            item.quantity += 1
            item.unit_price = product.price
            item.save(update_fields=["quantity", "unit_price"])
    messages.success(request, "已加入购物车")
    return redirect("home")


def clear_cart(request):
    customer = require_customer(request)
    if not customer:
        return redirect("login")
    Cart.objects.get_or_create(customer=customer)[0].items.all().delete()
    messages.success(request, "购物车已清空")
    return redirect("cart")


def remove_cart(request):
    customer = require_customer(request)
    if not customer:
        return redirect("login")
    my_cart, _ = Cart.objects.get_or_create(customer=customer)
    my_cart.items.filter(product_id=request.GET.get("product_id")).delete()
    messages.success(request, "商品已移出购物车")
    return redirect("cart")


def change_cart(request):
    customer = require_customer(request)
    if not customer:
        return redirect("login")
    my_cart, _ = Cart.objects.get_or_create(customer=customer)
    cart_item = get_object_or_404(my_cart.items.select_related("product"), product_id=request.GET.get("product_id"))
    if cart_item.product.inventory <= 0:
        cart_item.delete()
        messages.warning(request, "商品已售罄，已从购物车移除")
        return redirect("cart")
    quantity = parse_positive_int(request.GET.get("quantity"))
    cart_item.quantity = min(quantity, cart_item.product.inventory)
    cart_item.unit_price = cart_item.product.price
    cart_item.save(update_fields=["quantity", "unit_price"])
    messages.success(request, "购物车数量已更新")
    return redirect("cart")


def checkout(request):
    customer = require_customer(request)
    if not customer:
        return redirect("login")
    if request.method != "POST":
        return redirect("cart")
    if not has_complete_address(customer):
        messages.error(request, "请先到个人中心设置完整地址")
        return redirect("cart")

    my_cart, _ = Cart.objects.get_or_create(customer=customer)
    cart_items = list(my_cart.items.select_related("product", "product__seller", "product__seller__customer"))
    if not cart_items:
        messages.info(request, "购物车为空")
        return redirect("cart")

    payment_password = request.POST.get("payment_password")

    with transaction.atomic():
        payer = Pocket.objects.select_for_update().get(id=ensure_pocket(customer).id)
        if payer.password != payment_password:
            messages.error(request, "支付密码错误")
            return redirect("cart")

        locked_products = {
            product.id: product
            for product in Product.objects.select_for_update()
            .select_related("seller", "seller__customer")
            .filter(id__in=[item.product_id for item in cart_items])
        }

        total = Decimal("0")
        for item in cart_items:
            product = locked_products[item.product_id]
            if item.quantity > product.inventory:
                messages.error(request, f"{product.title} 库存不足")
                return redirect("cart")
            total += product.price * item.quantity

        if payer.amount < total:
            messages.error(request, "余额不足")
            return redirect("cart")

        payer.amount -= total
        payer.save(update_fields=["amount"])

        for item in cart_items:
            product = locked_products[item.product_id]
            line_total = product.price * item.quantity
            receiver = Pocket.objects.select_for_update().get(id=ensure_seller_pocket(product.seller).id)
            receiver.amount += line_total
            receiver.save(update_fields=["amount"])
            Record.objects.create(receiver=receiver, payer=payer, money=line_total)
            Order.objects.create(
                seller=product.seller,
                payment_status=Order.PaymentStatus.DONE,
                customer=customer,
                shipping_status=Order.ShippingStatus.NOT_SHIPPED,
                address=customer.address,
                quantity=item.quantity,
                total_price=line_total,
                product=product,
            )
            product.inventory -= item.quantity
            product.sale += item.quantity
            product.save(update_fields=["inventory", "sale", "last_update"])

        my_cart.items.all().delete()

    messages.success(request, "结算成功，订单已生成")
    return redirect("my_order")


def my_order(request):
    customer = require_customer(request)
    if not customer:
        return redirect("login")

    seller = get_seller_for_customer(customer, create=False)
    orders = list(Order.objects.filter(customer=customer).select_related("customer", "product", "seller", "address"))
    if seller:
        orders += list(Order.objects.filter(seller=seller).select_related("customer", "product", "seller", "address"))
    unique_orders = sorted({order.id: order for order in orders}.values(), key=lambda order: order.placed_at, reverse=True)
    paginator, page_obj = paginate(request, unique_orders, per_page=6)
    return render(
        request,
        "my_order.html",
        {
            "page_obj": page_obj,
            "paginator": paginator,
            "orders": unique_orders,
            "user_id": customer.id,
        },
    )


def process_order(request):
    customer = require_customer(request)
    if not customer:
        return redirect("login")
    order = get_object_or_404(Order.objects.select_related("seller"), id=request.GET.get("order_id"))
    if order.seller.customer_id != customer.id:
        messages.error(request, "只能处理自己店铺的订单")
        return redirect("my_order")

    status = request.GET.get("status")
    if status not in Order.ShippingStatus.values:
        return HttpResponse("ERROR", status=400)
    order.shipping_status = status
    order.save(update_fields=["shipping_status"])
    messages.success(request, "订单状态已更新")
    return redirect("my_order")


def delete_comment(request):
    customer = require_customer(request)
    if not customer:
        return redirect("login")
    comment = get_object_or_404(Comment.objects.select_related("product", "product__seller"), id=request.GET.get("comment_id"))
    product_id = request.GET.get("product_id") or comment.product_id
    is_product_owner = comment.product.seller.customer_id == customer.id
    if comment.customer_id != customer.id and not is_product_owner:
        messages.error(request, "只能删除自己的评论或自己商品下的评论")
    else:
        comment.delete()
        messages.success(request, "评论已删除")
    return redirect(f"/store/detail/?product_id={product_id}")


def add_comment(request):
    customer = require_customer(request)
    if not customer:
        return redirect("login")
    product = get_object_or_404(Product.objects.select_related("seller"), id=request.GET.get("product_id"))
    content = (request.POST.get("content") or "").strip()
    if not content:
        return redirect(f"/store/detail/?product_id={product.id}")

    up_comment = Comment.objects.filter(id=request.POST.get("up_comment_id"), product=product).first()
    comment_type = Comment.CommentType.SELLER if product.seller.customer_id == customer.id else Comment.CommentType.CUSTOMER
    Comment.objects.create(
        customer=customer,
        seller=product.seller if comment_type == Comment.CommentType.SELLER else None,
        product=product,
        content=content,
        comment_type=comment_type,
        reply=up_comment,
    )
    messages.success(request, "评论已发布")
    return redirect(f"/store/detail/?product_id={product.id}")


def reply_comment(request):
    product_id = request.GET.get("product_id")
    up_comment_id = request.GET.get("up_comment_id")
    return redirect(f"/store/detail/?product_id={product_id}&up_comment_id={up_comment_id}")


def search(request):
    customer = require_customer(request)
    if not customer:
        return redirect("login")

    query = (request.GET.get("query") or request.POST.get("query") or "").strip()
    products = Product.objects.select_related("category", "seller").filter(inventory__gt=0)
    if query:
        products = products.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(category__title__icontains=query)
            | Q(seller__shop_name__icontains=query)
        ).distinct()

    paginator, page_obj = paginate(request, products)
    return render(
        request,
        "home.html",
        {
            "page_obj": page_obj,
            "paginator": paginator,
            "query": query,
            "featured_count": products.count(),
        },
    )
