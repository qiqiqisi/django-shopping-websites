# django-shopping-websites
中国海洋大学ouc爱特假期项目：制作购物网站，使用django
### 前提

下载MySQL

获取QQ授权码

### test_market/settings.py

找到这部分代码

```py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'market',
        'USER': '',
        'PASSWORD': '',
        'HOST': '127.0.0.1',
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
        },
    }
}
```

填入自己的MySQL账号和密码



找到这部分代码

```py
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''  # QQ邮箱授权码
DEFAULT_FROM_EMAIL = ''
```

输入自己的QQ邮箱以及通过邮箱获取的授权码

### 运行

若使用pycharm，打开终端，输入

```cmd
python manage.py runserver
```
