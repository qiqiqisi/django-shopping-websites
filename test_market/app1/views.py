from datetime import timezone
from django.core.mail import send_mail
from django.conf import settings
from pyexpat.errors import messages
from django.contrib import messages
from .models import *
import random
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from .models import Product, Customer, Comment
from django.utils import timezone


# 发送邮件
# 全局变量存储验证码
verification_code = {}
def send_verification_email(email):
    """
    发送验证码到指定邮箱
    :param email: 目标邮箱
    :return: 验证码（字符串）或 None（发送失败）
    """
    # 生成 6 位随机验证码
    code = ''.join(random.choices('0123456789', k=6))
    print(code)
    # 发送邮件
    try:
        send_mail(
            subject='您的验证码',
            message=f'您的验证码是：{code}，请勿泄露。',
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            fail_silently=False,
        )
        # 将验证码存储到全局变量中
        verification_code[email] = code
        return code
    except Exception as e:
        print(f"邮件发送失败: {e}")
        return None

# 登录
def login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        # 验证用户名和密码
        try:
            customer = Customer.objects.get(username=username, password=password)
            # 将用户信息存储在 session 中
            request.session['user_id'] = customer.id
            request.session['username'] = customer.username
            return redirect('/home/')  # 登录成功，跳转到 Home 页面
        except Customer.DoesNotExist:
            messages.error(request, '用户名或密码错误')
            return render(request, 'login.html', {'error': '用户名或密码错误'})

    # 如果是 GET 请求，直接渲染登录页面
    return render(request, 'login.html')

# 注册
def register(request):
    if request.method == 'POST':
        # 获取表单数据
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        user_code = request.POST.get('verification_code')

        # 判断是发送验证码还是提交注册
        if 'send_code' in request.POST:  # 发送验证码
            if Customer.objects.filter(email=email).exists():
                return render(request, 'register.html', {'error': '该邮箱已注册'})

            # 调用发送验证码的函数
            code = send_verification_email(email)
            if code:
                context = {
                    'message': '验证码已发送，请查收邮箱！',
                    'username': username,
                    'email': email,
                    'password': password,
                }
            else:
                context = {
                    'error': '邮件发送失败，请稍后重试！',
                    'username': username,
                    'email': email,
                    'password': password,
                }
            return render(request, 'register.html', context)

        elif 'register' in request.POST:  # 提交注册
            # 验证验证码
            if email in verification_code and user_code == verification_code[email]:
                if Customer.objects.filter(username=username).exists():
                    return render(request, 'register.html', {'error': '该用户名已存在'})
                if len(username) < 3 or len(username) > 18 or len(password) < 8 or len(password) > 18:
                    return render(request, 'register.html', {'error': '用户名或密码输入格式不正确'})

                # 验证码正确，创建用户
                try:
                    user_id = Customer.objects.create(
                        username=username,
                        email=email,
                        password=password,  # 实际项目中应对密码进行哈希处理
                        birth_date=None,  # 你的表单中没有出生日期字段，设为 None
                        gender='N',  # 默认性别为“未知”
                    )
                    Seller.objects.create(shop_name='', id=user_id)
                    # 清除验证码
                    del verification_code[email]
                    return redirect('/login/')  # 注册成功，跳转到成功页面
                except Exception as e:
                    context = {
                        'error': '注册失败，请检查输入信息！',
                        'username': username,
                        'email': email,
                        'password': password,
                    }
                    print(e)
                    return render(request, 'register.html', context)
            else:
                context = {
                    'error': '验证码错误，请重新输入！',
                    'username': username,
                    'email': email,
                    'password': password,
                }
                return render(request, 'register.html', context)

    # 如果是 GET 请求，直接渲染注册页面
    return render(request, 'register.html')

# 更新
def update(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        new_username = request.POST.get('username')
        new_password = request.POST.get('password')
        user_code = request.POST.get('verification_code')

        # 判断是发送验证码还是提交更新
        if 'send-code' in request.POST:  # 发送验证码
            if not Customer.objects.filter(email=email).exists():
                return render(request, 'update.html', {'error': '该邮箱未注册'})

            # 调用发送验证码的函数
            code = send_verification_email(email)
            if code:
                context = {
                    'message': '验证码已发送，请查收邮箱！',
                    'email': email,
                    'username': new_username,
                    'password': new_password,
                }
            else:
                context = {
                    'error': '邮件发送失败，请稍后重试！',
                    'email': email,
                    'username': new_username,
                    'password': new_password,
                }

            return render(request, 'update.html', context)

        elif 'update' in request.POST:  # 提交更新
            # 验证验证码
            if email in verification_code and user_code == verification_code[email]:
                try:
                    customer = Customer.objects.get(email=email)

                    # 检查新用户名是否唯一（除非是当前用户的用户名）
                    if new_username != customer.username and Customer.objects.filter(username=new_username).exists():
                        context = {
                            'error': '该用户名已被其他用户使用',
                            'email': email,
                            'username': new_username,
                            'password': new_password,
                        }
                        return render(request, 'update.html', context)

                    # 检查用户名和密码长度
                    if len(new_username) < 3 or len(new_username) > 18 or len(new_password) < 8 or len(new_password) > 18:
                        context = {
                            'error': '用户名或密码输入格式不正确',
                            'email': email,
                            'username': new_username,
                            'password': new_password,
                        }
                        return render(request, 'update.html', context)

                    # 更新用户名和密码
                    customer.username = new_username
                    customer.password = new_password
                    customer.save()

                    # 清除验证码
                    del verification_code[email]
                    return redirect('/login/')
                except Exception as e:
                    context = {
                        'error': '更新失败，请检查输入信息！',
                        'email': email,
                        'username': new_username,
                        'password': new_password,
                    }
                    return render(request, 'update.html', context)
            else:
                context = {
                    'error': '验证码错误，请重新输入！',
                    'email': email,
                    'username': new_username,
                    'password': new_password,
                }
                return render(request, 'update.html', context)

    # 如果是 GET 请求，直接渲染更新页面
    return render(request, 'update.html')

# 退出登录
def logout(request):
    # 清除 session 中的用户信息
    request.session.flush()
    return redirect('/login/')  # 重定向到登录页面

# 主页
def home(request):
    # 从 session 中获取用户信息
    user_id = request.session.get('user_id')
    username = request.session.get('username')
    if not user_id or not username:
        return redirect('/login/')  # 如果未登录，重定向到登录页面
    user_avatar = Customer.objects.get(id=user_id).avatar


    # 以销量的形式作为排序，判断推荐情况
    products = Product.objects.all()
    products = products.order_by('-sale')

    # 使用分页器
    paginator = Paginator(products, 6)  # 每页显示 6 个商品
    page_number = request.GET.get('page')  # 获取当前页码
    page_obj = paginator.get_page(page_number)  # 获取当前页的商品
    context = {
        'username': username,
        'user_avatar': user_avatar,
        'page_obj': page_obj,
        'paginator': paginator,
        'products': products,
    }
    return render(request, 'home.html', context)

# 个人中心
def person(request):
    user_id = request.session.get('user_id')
    username = request.session.get('username')

    if not user_id or not username:
        return redirect('/login/')

    customer = Customer.objects.get(id=user_id)

    if request.method == 'GET':
        # 准备上下文数据
        context = {
            'username': username,
            'user_avatar': customer.avatar,
            'user_gender': customer.gender,
            'user_email': customer.email,
            'user_birth_date': customer.birth_date,
        }

        if Address.objects.filter(customer=customer).exists():
            address = Address.objects.get(customer=customer)
            context['state'] = address.state
            context['city'] = address.city
            context['street'] = address.street

        return render(request, 'person.html', context)

    # 处理 POST 请求
    gender = request.POST.get('gender')
    birth_date = request.POST.get('birth_date')
    avatar = request.FILES.get('avatar')
    state = request.POST.get('state')
    city = request.POST.get('city')
    street = request.POST.get('street')

    # 更新用户信息
    customer.gender = gender
    customer.birth_date = birth_date if birth_date else customer.birth_date  # 如果未提交值，保留原始值
    if avatar:
        customer.avatar = avatar
    customer.save()

    # 更新或创建地址信息
    address, created = Address.objects.get_or_create(customer=customer)
    address.state = state
    address.city = city
    address.street = street
    address.save()

    # 确保Customer对象的address字段被更新
    customer.address = address
    customer.save()

    return redirect('/person/')


# 我的商店
def store(request):
    user_id = request.session.get('user_id')
    username = request.session.get('username')
    if not user_id or not username:
        return redirect('/login/')

    try:
        seller = Seller.objects.get(id=user_id)
        store_name = seller.shop_name
        store_avatar = seller.avatar
        products = Product.objects.filter(seller=seller)  # 查询当前卖家的所有商品
    except Seller.DoesNotExist:
        store_name = '未命名'
        store_avatar = 'sellers/avatars/img.png'
        products = []

    # 使用分页器
    paginator = Paginator(products, 6)  # 每页显示 6 个商品
    page_number = request.GET.get('page')  # 获取当前页码
    page_obj = paginator.get_page(page_number)  # 获取当前页的商品

    context = {
        'store_name': store_name,
        'store_avatar': store_avatar,
        'page_obj': page_obj, # 将分页对象传递到模板
        'paginator': paginator,
    }
    return render(request, 'store.html', context)

# 设置我的商店基本信息
def store_set(request):
    if request.method != 'POST':
        return render(request, 'store_set.html')

    user_id = request.session.get('user_id')
    username = request.session.get('username')
    store_name = request.POST.get('store_name')
    avatar = request.FILES.get('avatar')  # 获取上传的头像文件

    if 'save' in request.POST:
        if Seller.objects.filter(id=user_id).exists():
            seller = Seller.objects.get(id=user_id)
            seller.shop_name = store_name
            if avatar:
                seller.avatar = avatar  # 更新头像
            seller.save()
            return HttpResponse('SUCCESS')
        else:
            if avatar:
                Seller.objects.create(id=user_id, shop_name=store_name, avatar=avatar)
            else:
                Seller.objects.create(id=user_id, shop_name=store_name)
            return HttpResponse('SUCCESS')
    return HttpResponse('FAILED')

# 上传商品
def update_product(request):
    if request.method != 'POST':
        # 如果不是 POST 请求，直接返回上传商品页面
        return render(request, 'update_product.html')

    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login/')  # 如果未登录，重定向到登录页面

    try:
        seller = Seller.objects.get(id=user_id)
    except Seller.DoesNotExist:
        return HttpResponse('您尚未注册为卖家，无法上传商品。')

    title = request.POST.get('title')
    description = request.POST.get('description')
    price = request.POST.get('price')
    inventory = request.POST.get('inventory')
    category_title = request.POST.get('category')
    image = request.FILES.get('image')

    # 数据验证
    if not all([title, description, price, inventory, category_title, image]):
        messages.error(request, '所有字段均为必填项。')
        return redirect('/store/update_product/')

    try:
        price = float(price)
        inventory = int(inventory)
    except ValueError:
        messages.error(request, '价格和库存必须是数字。')
        return redirect('/store/update_product/')

    if price < 0 or inventory < 0:
        messages.error(request, '价格和库存不能为负数。')
        return redirect('/store/update_product/')

    # 创建或获取分类
    category, created = Category.objects.get_or_create(title=category_title)

    # 创建商品
    Product.objects.create(
        title=title,
        description=description,
        price=price,
        image=image,
        inventory=inventory,
        category=category,
        seller=seller
    )

    messages.success(request, '商品上传成功！')
    return redirect('/store/')  # 重定向到店铺管理页面

# 商店内商品具体内容
def detail(request):
    product_id = request.GET.get('product_id')

    if not product_id:
        return HttpResponse("商品详细信息需要商品 ID，请检查 URL", status=400)

    try:
        product = Product.objects.get(pk=product_id)
    except Product.DoesNotExist:
        return HttpResponse("商品不存在", status=404)

    user_id = request.session.get('user_id')
    seller_id = product.seller_id
    can_purchase = False
    comments_type = None

    if user_id:
        try:
            if user_id == seller_id:
                can_purchase = False  # 是卖家，不能购买
                comments_type = 'seller'
            else:
                can_purchase = True  # 不是卖家，可以购买
                comments_type = 'customer'
        except Customer.DoesNotExist:
            can_purchase = True  # 用户不存在，视为普通用户可以购买
            comments_type = 'other'
    else:
        can_purchase = False  # 未登录用户不能购买

    # 获取所有评论
    comments = Comment.objects.filter(product=product, reply=None).order_by('-created_at')

    context = {
        'product': product,
        'seller': product.seller,
        'can_purchase': can_purchase,
        'user_id': user_id,
        'comments': comments,
    }

    # 获取回复的评论信息
    up_comment_id = request.GET.get('up_comment_id')
    if up_comment_id:
        try:
            up_comment = Comment.objects.get(id=up_comment_id)
            context['up_content'] = up_comment.content
            context['up_user'] = up_comment.customer.username
            context['up_comment_id'] = up_comment_id
        except Comment.DoesNotExist:
            pass

    return render(request, 'detail.html', context)

# 修改商店信息
def change_detail(request):
    if request.method != 'POST':
        product_id = request.GET.get('product_id')
        product = Product.objects.get(id=product_id)
        return render(request, 'change_detail.html', {'product': product})
    else:
        product_id = request.POST.get('product_id')
        product = Product.objects.get(id=product_id)
        description = request.POST.get('description')
        image = request.FILES.get('image')

        inventory = request.POST.get('inventory')
        category = request.POST.get('category')
        price = request.POST.get('price')
        title = request.POST.get('title')
        product.description = description
        product.inventory = inventory
        product.category.title = category
        product.price = price
        product.title = title
        if image:
            product.image = image
        print(f"image:{image}")
        product.save()
        return redirect('/store/detail/?product_id=' + product_id)

# 钱包
def transfer(request):
    # customer
    user_id = request.session.get('user_id')
    username = request.session.get('username')

    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        print(f'post: {product_id}')
    else:
        product_id = request.GET.get('product_id')
        print(f'get: {product_id}')

    # 检查 product_id 是否为空
    if product_id == '':
        messages.error(request, "商品 ID 未指定")
        return HttpResponse('商品 ID 未指定')

    try:
        # 获取商品信息
        product = Product.objects.get(id=product_id)
        money = product.price
        seller_id = product.seller_id
        seller_name = Customer.objects.get(id=seller_id).username
    except Product.DoesNotExist:
        messages.error(request, "商品不存在，请检查商品 ID")
        return HttpResponse('no product')
    except Customer.DoesNotExist:
        messages.error(request, "卖家信息不存在，请联系管理员")
        return HttpResponse('no customer')



    # 初始化钱包
    if not Pocket.objects.filter(id=seller_id).exists():
        Pocket.objects.create(id=seller_id, name=seller_name, amount=999999, password=999999)
    if not Pocket.objects.filter(id=user_id).exists():
        Pocket.objects.create(id=user_id, name=username, amount=999999, password=999999)

    payer = Pocket.objects.get(id=user_id)
    receiver = Pocket.objects.get(id=seller_id)

    # POST 请求处理
    if request.method == 'POST':
        password = request.POST.get('password')

        # 验证支付密码
        if payer.password != password:
            messages.error(request, '支付密码错误')
            context = {'error': '支付密码错误', 'money': money, 'object': seller_name, 'product_id': product_id}
            return render(request, 'transfer.html', context)

        # 验证余额
        if payer.amount < money:
            messages.error(request, '余额不足')
            context = {'error': '余额不足', 'money': money, 'object': seller_name, 'product_id': product_id}
            return render(request, 'transfer.html', context)

        # 转账前必须有地址
        customer = Customer.objects.get(id=user_id)
        address = customer.address
        if not address:
            messages.error(request, '请先到个人中心设置地址')
            context = {'error': '请先到个人中心设置地址', 'money': money, 'object': seller_name,
                       'product_id': product_id}
            return render(request, 'transfer.html', context)

        if not address.state or not address.city or not address.street:
            messages.error(request, '请先到个人中心完善地址')
            context = {'error': '请先到个人中心设置地址', 'money': money, 'object': seller_name,
                        'product_id': product_id}
            print(f'{address.city}, {address.street}, {address.state}')
            return render(request, 'transfer.html', context)


        # 执行转账（直接操作数据库）
        try:
            payer.amount -= money
            payer.save()
            receiver.amount += money
            receiver.save()
            Record.objects.create(object=receiver, pocket=payer, money=money)
        except Exception as e:
            messages.error(request, '支付失败')
            context = {'error': '支付失败', 'money': money, 'object': seller_name, 'product_id': product_id}
            return render(request, 'transfer.html', context)

        messages.success(request, '支付成功')
        return redirect(f'/add_order/?product_id={product_id}&status=DONE&quantity=1')

    # GET 请求处理
    context = {'money': money, 'object': seller_name, 'product_id': product_id}
    return render(request, 'transfer.html', context)

# 添加订单
def add_order(request):

    user_id = request.session.get('user_id')
    username = request.session.get('username')

    customer = Customer.objects.get(id=user_id)

    product_id = request.GET.get('product_id')
    status = request.GET.get('status')
    quantity = request.GET.get('quantity')
    product = Product.objects.get(id=product_id)
    product.inventory -= int(quantity)
    product.sale += int(quantity)
    product.save()
    order = Order.objects.create(seller=product.seller, payment_status=status, customer=customer, shipping_status='NOT', address=customer.address, quantity=1, total_price=product.price, product=product)

    return redirect('/my_order/')

# 删除订单
def delete_order(request):
    order_id = request.GET.get('order_id')
    order = Order.objects.get(id=order_id)
    order.delete()
    return redirect('/my_order/')



# 购物车
def cart(request):
    user_id = request.session.get('user_id')
    username = request.session.get('username')
    customer = Customer.objects.get(id=user_id)
    user_avatar = customer.avatar
    try:
        my_cart = Cart.objects.get(customer=customer)
    except Cart.DoesNotExist:
        my_cart = Cart.objects.create(customer=customer)
    cart_items = CartItem.objects.filter(cart=my_cart)
    total = 0
    for item in cart_items:
        total += item.quantity * item.unit_price

    context = {'user_avatar': user_avatar,'username': username , 'cart_items': cart_items, 'total': total}
    try:
        error = request.GET.get('error')
        context['error'] = error
    except:
        pass
    return render(request, 'cart.html', context)

# 添加购物车
def add_cart(request):
    product_id = request.GET.get('product_id')
    product = Product.objects.get(id=product_id)
    user_id = request.session.get('user_id')
    customer = Customer.objects.get(id=user_id)
    # 判断是否存在购物车，若不存在就新建购物车
    if not Cart.objects.filter(customer=customer).exists():
        Cart.objects.create(customer=customer)
    my_cart = Cart.objects.get(customer=customer)

    # 如果购物车中原本没有这个商品
    if not CartItem.objects.filter(cart=my_cart, product=product).exists():
        CartItem.objects.create(cart=my_cart, product=product, quantity=1, unit_price=product.price)

    # 如果购物车含有这个商品
    else:
        cart_item = CartItem.objects.get(cart=my_cart, product=product)
        cart_item.quantity += 1
        cart_item.save()

    return redirect('/home/')

# 清空购物车
def clear_cart(request):
    user_id = request.session.get('user_id')
    customer = Customer.objects.get(id=user_id)
    my_cart = Cart.objects.get(customer=customer)
    CartItem.objects.filter(cart=my_cart).all().delete()
    return redirect('/cart/')

# 删除购物车的一个商品
def remove_cart(request):
    user_id = request.session.get('user_id')
    customer = Customer.objects.get(id=user_id)
    my_cart = Cart.objects.get(customer=customer)
    product_id = request.GET.get('product_id')
    CartItem.objects.get(cart=my_cart, product=product_id).delete()
    return redirect('/cart/')

# 修改购物车数量
def change_cart(request):
    user_id = request.session.get('user_id')
    customer = Customer.objects.get(id=user_id)
    my_cart = Cart.objects.get(customer=customer)
    quantity = request.GET.get('quantity')
    product_id = request.GET.get('product_id')
    product = Product.objects.get(id=product_id)
    cart_item = CartItem.objects.get(cart=my_cart, product=product)
    cart_item.quantity = int(quantity)
    cart_item.save()
    return redirect('/cart/')

# 一键结算
def checkout(request):
    user_id = request.session.get('user_id')
    username = request.session.get('username')
    if not user_id or not username:
        return redirect('/login/')  # 如果未登录，重定向到登录页面

    customer = Customer.objects.get(id=user_id)
    my_cart = Cart.objects.get(customer=customer)
    cart_items = CartItem.objects.filter(cart=my_cart)

    # 转账前必须有地址
    address = customer.address
    if not address or not address.state or not address.city or not address.street:
        messages.error(request, '请先到个人中心设置完整地址')
        return redirect('/cart/?error=请先到个人中心设置完整地址')
    else:
        print(customer.address)



    total = 0
    error = ''
    not_enough = False
    for item in cart_items:
        total += item.quantity * item.unit_price
        # 确定不超出库存数目
        if item.product.inventory < item.quantity:
            not_enough = True
            error += item.product.title
            error += ' '
    if not_enough:
        error += '库存不足'
        return redirect(f'/cart/?error={error}')

    # 获取支付密码
    payment_password = request.POST.get('payment_password')

    # 验证支付密码（假设 Pocket 模型有一个 password 字段）
    try:
        payer_pocket = Pocket.objects.get(id=user_id)
    except Pocket.DoesNotExist:
        payer_pocket = Pocket.objects.create(id=user_id, name=username, amount=999999, password=999999)

    # 检查支付密码是否正确
    if payer_pocket.password != payment_password:
        messages.error(request, '支付密码错误')
        return redirect('/cart/')  # 重定向回购物车页面

    payer_amount = payer_pocket.amount

    try:
        if payer_amount >= total:
            # 扣除用户余额
            payer_pocket.amount -= total
            payer_pocket.save()

            # 创建订单（每个商品一个订单）
            for item in cart_items:
                product = item.product
                seller = product.seller
                # 更新卖家余额
                seller_pocket = Pocket.objects.get(id=seller.id)
                seller_pocket.amount += product.price
                seller_pocket.save()

                # 创建订单
                Order.objects.create(
                    seller=seller,
                    payment_status='DONE',
                    customer=customer,
                    shipping_status='NOT',
                    address=customer.address,
                    quantity=item.quantity,
                    total_price=product.price * item.quantity,  # 假设单价乘数量是总价
                    product=product
                )
                product.inventory -= item.quantity
                product.sale += item.quantity
                product.save()
            # 清空购物车
            cart_items.delete()

            messages.success(request, '结算成功')
            return redirect('/home/')
        else:
            messages.error(request, '余额不足')
            return redirect('/cart/')
    except Exception as e:
        messages.error(request, '结算失败')
        return HttpResponse('ERROR')

# 我的订单
def my_order(request):
    user_id = request.session.get('user_id')
    username = request.session.get('username')
    customer = Customer.objects.get(id=user_id)
    seller = Seller.objects.get(id=user_id)
    user_avatar = customer.avatar
    orders_customer = Order.objects.filter(customer=customer)
    orders_seller = Order.objects.filter(seller=seller)


    combine = list(orders_seller) + list(orders_customer)

    # 使用分页器
    paginator = Paginator(combine, 6)  # 每页显示 6 个商品
    page_number = request.GET.get('page')  # 获取当前页码
    page_obj = paginator.get_page(page_number)  # 获取当前页的商品

    context = {
        'page_obj': page_obj,  # 将分页对象传递到模板
        'paginator': paginator,
        'page_number': page_number,
        'user_avatar': user_avatar,
        'username': username,
        'orders': combine,
        'user_id': user_id,
    }
    return render(request, 'my_order.html', context)

# 处理订单
def process_order(request):
    user_id = request.session.get('user_id')
    status = request.GET.get('status')
    order_id = request.GET.get('order_id')
    print(f'id: {order_id}')
    order = Order.objects.get(id=order_id)
    if status == 'NOT':
        order.shipping_status = 'NOT'
    elif status == 'ING':
        order.shipping_status = 'ING'
    elif status == 'DONE':
        order.shipping_status = 'DONE'
    else:
        return HttpResponse('ERROR')
    order.save()
    return redirect('/my_order/')


# 删除评论
def delete_comment(request):
    comment_id = request.GET.get('comment_id')
    comment = Comment.objects.get(id=comment_id)
    comment.delete()
    product_id = request.GET.get('product_id')
    return redirect('/store/detail/?product_id=' + product_id)

# 添加评论
def add_comment(request):
    user_id = request.session.get('user_id')
    product_id = request.GET.get('product_id')
    product = Product.objects.get(id=product_id)
    seller = product.seller
    seller_id = seller.id
    content = request.POST.get('content')
    # 如果用户什么也没输入，那就不会新增评论
    if content=='':
        return redirect(f"/store/detail/?product_id={product_id}")
    up_comment_id = request.POST.get('up_comment_id')
    is_reply = True
    try:
        up_comment = Comment.objects.get(id=up_comment_id)
    except Comment.DoesNotExist:
        is_reply = False
    comments_type = None

    if user_id:
        try:
            if user_id == seller_id:
                comments_type = 'seller'
            else:
                comments_type = 'customer'
                print(f"user:{user_id},{type(user_id)}\nseller:{seller_id},{type(seller_id)}")
        except Customer.DoesNotExist:
            comments_type = 'other'

    # 创建新的评论
    comment = Comment(
    customer_id=user_id,
    product=product,
    content=content,
    comment_type=comments_type,
    created_at=timezone.now(),
    )
    if is_reply:
        comment.reply = up_comment
    comment.save()
    # 确保重定向的 URL 中包含 product_id
    return redirect('/store/detail/?product_id=' + product_id)


# 回复评论
def reply_comment(request):
    product_id = request.GET.get('product_id')
    up_comment_id = request.GET.get('up_comment_id')
    print(f'id: {up_comment_id}')
    return redirect(f'/store/detail/?product_id={product_id}&up_comment_id={up_comment_id}')


# 搜索
def search(request):
    user_id = request.session.get('user_id')
    username = request.session.get('username')
    customer = Customer.objects.get(id=user_id)
    user_avatar = customer.avatar
    query = request.POST.get('query', '')  # 获取搜索关键词
    products = Product.objects.filter(
        models.Q(title__icontains=query) |  # 搜索商品名称
        models.Q(description__icontains=query) |  # 搜索商品描述
        models.Q(category__title__icontains=query) | # 搜索商品类别
        models.Q(seller__shop_name__icontains=query)
    ).distinct()  # 去重

    # 分页处理
    paginator = Paginator(products, 6)  # 每页显示10个商品
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {'page_obj': page_obj, 'paginator': paginator,'products': query,'user_avatar': user_avatar,'username': username}
    return render(request, 'home.html', context)



# 测试函数
def test(request):
    customer = Customer.objects.get(id=5)
    customer.delete()
    return HttpResponse('SUCCESS')