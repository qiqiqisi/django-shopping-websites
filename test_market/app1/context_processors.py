from .models import Customer


def market_context(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return {}

    customer = Customer.objects.filter(id=user_id).first()
    if not customer:
        request.session.flush()
        return {}

    return {
        "current_customer": customer,
        "username": customer.username,
        "user_avatar": customer.avatar,
    }
