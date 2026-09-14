from decimal import Decimal

from django.conf import settings

from .models import Coupon, Product


class Cart:
    COUPON_SESSION_ID = 'coupon_id'

    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    def add(self, product, quantity=1, override_quantity=False):
        product_id = str(product.id)
        if product_id not in self.cart:
            self.cart[product_id] = {'quantity': 0, 'price': str(product.price)}

        if override_quantity:
            self.cart[product_id]['quantity'] = quantity
        else:
            self.cart[product_id]['quantity'] += quantity

        if self.cart[product_id]['quantity'] > product.stock:
            self.cart[product_id]['quantity'] = product.stock

        if self.cart[product_id]['quantity'] <= 0:
            self.cart.pop(product_id, None)

        self.save()

    def save(self):
        self.session.modified = True

    def remove(self, product):
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def __iter__(self):
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids)
        cart = self.cart.copy()
        for product in products:
            cart[str(product.id)]['product'] = product

        for item in cart.values():
            item['price'] = Decimal(item['price'])
            item['total_price'] = item['price'] * item['quantity']
            yield item

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        return sum(
            (Decimal(item['price']) * item['quantity'] for item in self.cart.values()),
            Decimal('0.00'),
        )

    def get_coupon(self):
        coupon_id = self.session.get(self.COUPON_SESSION_ID)
        if not coupon_id:
            return None
        try:
            coupon = Coupon.objects.get(pk=coupon_id)
        except Coupon.DoesNotExist:
            self.remove_coupon()
            return None
        if not coupon.is_valid():
            self.remove_coupon()
            return None
        return coupon

    @property
    def coupon(self):
        return self.get_coupon()

    def apply_coupon(self, coupon):
        self.session[self.COUPON_SESSION_ID] = coupon.id
        self.save()

    def remove_coupon(self):
        self.session.pop(self.COUPON_SESSION_ID, None)
        self.save()

    def get_discount(self):
        coupon = self.get_coupon()
        if not coupon:
            return Decimal('0.00')
        return coupon.calculate_discount(self.get_total_price())

    def get_total_after_discount(self):
        return max(self.get_total_price() - self.get_discount(), Decimal('0.00'))

    def clear(self):
        self.session.pop(settings.CART_SESSION_ID, None)
        self.session.pop(self.COUPON_SESSION_ID, None)
        self.save()
