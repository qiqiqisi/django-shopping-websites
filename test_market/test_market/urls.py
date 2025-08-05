"""
URL configuration for test_market project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# from django.contrib import admin
from django.urls import path
from app1 import views
from debug_toolbar.toolbar import debug_toolbar_urls
from django.conf import settings
from django.conf.urls.static import static
urlpatterns = [
    #    path('admin/', admin.site.urls),
    path('register/', views.register, name='register'),
    path('update/', views.update, name='update'),
    path('login/', views.login, name='login'),
    path('home/', views.home, name='home'),
    path('logout/', views.logout, name='logout'),
    path('person/', views.person, name='person'),
    path('store/', views.store, name='store'),
    path('store_set/', views.store_set, name='store_set'),
    path('store/update_product/', views.update_product, name='update_product'),
    path('store/detail/', views.detail, name='detail'),
    path('transfer/', views.transfer, name='transfer'),
    path('add_cart/', views.add_cart, name='add_cart'),
    path('cart/',views.cart, name='cart'),
    path('add_order/', views.add_order, name='add_order'),
    path('my_order/', views.my_order, name='my_order'),
    path('process_order/', views.process_order, name='process_order'),
    path('checkout/', views.checkout, name='checkout'),
    path('clear_cart/', views.clear_cart, name='clear_cart'),
    path('remove_cart/', views.remove_cart, name='remove_cart'),
    path('change_cart/', views.change_cart, name='change_cart'),
    path('delete_comment/', views.delete_comment, name='delete_comment'),
    path('delete_order/', views.delete_order, name='delete_order'),
    path('search/', views.search, name='search'),
    path('add_comment/', views.add_comment, name='add_comment'),
    path('reply_comment/', views.reply_comment, name='reply_comment'),
    path('change_detail/', views.change_detail, name='change_detail'),
    path('test/', views.test),
]+debug_toolbar_urls() #add for debug
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)