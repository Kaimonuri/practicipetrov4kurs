from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .cart import Cart
from .forms import OrderCreateForm, ReviewForm
from .models import Category, Coupon, OrderItem, Product, Review, WishlistItem


CATALOG_CACHE_SECONDS = 300


def _safe_next_url(request, fallback):
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return fallback


def product_list(request, category_slug=None):
    category = None
    categories = cache.get('catalog_categories')
    if categories is None:
        categories = list(Category.objects.all())
        cache.set('catalog_categories', categories, CATALOG_CACHE_SECONDS)

    query = request.GET.get('q', '').strip()
    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()
    sort = request.GET.get('sort', '')

    has_filters = bool(category_slug or query or min_price or max_price or sort)

    if not has_filters:
        products = cache.get('catalog_products')
        if products is None:
            products = list(
                Product.objects.filter(available=True)
                .select_related('category')
                .order_by('id')
            )
            cache.set('catalog_products', products, CATALOG_CACHE_SECONDS)
    else:
        products = Product.objects.filter(available=True).select_related('category')

        if category_slug:
            category = get_object_or_404(Category, slug=category_slug)
            products = products.filter(category=category)

        if query:
            products = products.filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            )

        try:
            if min_price:
                products = products.filter(price__gte=Decimal(min_price))
        except InvalidOperation:
            messages.warning(request, 'Минимальная цена указана неверно.')

        try:
            if max_price:
                products = products.filter(price__lte=Decimal(max_price))
        except InvalidOperation:
            messages.warning(request, 'Максимальная цена указана неверно.')

        sorting = {
            'price_asc': 'price',
            'price_desc': '-price',
            'new': '-created',
        }
        if sort in sorting:
            products = products.order_by(sorting[sort])

    wishlist_ids = set()
    if request.user.is_authenticated:
        wishlist_ids = set(
            request.user.wishlist_items.values_list('product_id', flat=True)
        )

    return render(request, 'shop/product/list.html', {
        'category': category,
        'categories': categories,
        'products': products,
        'query': query,
        'min_price': min_price,
        'max_price': max_price,
        'sort': sort,
        'wishlist_ids': wishlist_ids,
    })


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, available=True)
    reviews = product.reviews.select_related('user').all()
    review_form = ReviewForm()
    can_review = False
    is_wishlisted = False

    if request.user.is_authenticated:
        is_wishlisted = WishlistItem.objects.filter(
            user=request.user,
            product=product,
        ).exists()

        can_review = OrderItem.objects.filter(
            order__user=request.user,
            order__status='Completed',
            product=product,
        ).exists()

        if request.method == 'POST':
            if not can_review:
                messages.error(
                    request,
                    'Отзыв можно оставить только после завершения заказа с этим товаром.',
                )
                return redirect('product_detail', slug=slug)

            existing_review = Review.objects.filter(
                product=product,
                user=request.user,
            ).first()
            review_form = ReviewForm(request.POST, instance=existing_review)
            if review_form.is_valid():
                review = review_form.save(commit=False)
                review.product = product
                review.user = request.user
                review.save()
                messages.success(request, 'Отзыв сохранён.')
                return redirect('product_detail', slug=slug)

    return render(request, 'shop/product/detail.html', {
        'product': product,
        'reviews': reviews,
        'review_form': review_form,
        'can_review': can_review,
        'is_wishlisted': is_wishlisted,
    })


def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id, available=True)

    if product.stock <= 0:
        messages.error(request, 'Товара нет на складе.')
        return redirect('product_detail', slug=product.slug)

    quantity = 1
    if request.method == 'POST':
        try:
            quantity = max(1, int(request.POST.get('quantity', 1)))
        except (TypeError, ValueError):
            quantity = 1

    cart.add(product=product, quantity=quantity)
    messages.success(request, 'Товар успешно добавлен в корзину.')
    return redirect(_safe_next_url(request, reverse('cart_detail')))


def cart_update(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity', 1))
        except (TypeError, ValueError):
            quantity = 1

        if quantity <= 0:
            cart.remove(product)
        else:
            cart.add(product, quantity=quantity, override_quantity=True)
        messages.success(request, 'Количество товара обновлено.')

    return redirect('cart_detail')


def cart_remove(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    messages.success(request, 'Товар удалён из корзины.')
    return redirect('cart_detail')


def cart_detail(request):
    cart = Cart(request)
    return render(request, 'shop/cart/detail.html', {'cart': cart})


@require_POST
def coupon_apply(request):
    cart = Cart(request)
    code = request.POST.get('code', '').strip()
    coupon = Coupon.objects.filter(code__iexact=code).first()

    if coupon and coupon.is_valid():
        cart.apply_coupon(coupon)
        messages.success(request, f'Промокод {coupon.code} применён.')
    else:
        cart.remove_coupon()
        messages.error(request, 'Промокод не найден или больше не действует.')

    return redirect('cart_detail')


@require_POST
def coupon_remove(request):
    Cart(request).remove_coupon()
    messages.info(request, 'Промокод удалён.')
    return redirect('cart_detail')


def order_create(request):
    cart = Cart(request)
    cart_items = list(cart)

    if not cart_items:
        messages.warning(request, 'Корзина пуста.')
        return redirect('product_list')

    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                locked_products = {}
                for item in cart_items:
                    product = Product.objects.select_for_update().get(
                        pk=item['product'].pk
                    )
                    if item['quantity'] > product.stock:
                        messages.error(
                            request,
                            f'Недостаточно товара «{product.name}» на складе. '
                            f'Доступно: {product.stock}.',
                        )
                        return redirect('cart_detail')
                    locked_products[product.pk] = product

                coupon = cart.get_coupon()
                discount = cart.get_discount()

                order = form.save(commit=False)
                if request.user.is_authenticated:
                    order.user = request.user
                if coupon:
                    order.coupon_code = coupon.code
                    order.discount_amount = discount
                order.save()

                for item in cart_items:
                    product = locked_products[item['product'].pk]
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        price=item['price'],
                        quantity=item['quantity'],
                    )
                    product.stock -= item['quantity']
                    product.available = product.stock > 0
                    product.save(update_fields=['stock', 'available'])

                cart.clear()

            messages.success(request, f'Заказ №{order.id} успешно оформлен.')
            return render(request, 'shop/order/created.html', {'order': order})
    else:
        initial = {}
        if request.user.is_authenticated:
            initial = {
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'email': request.user.email,
            }
        form = OrderCreateForm(initial=initial)

    return render(request, 'shop/order/create.html', {'cart': cart, 'form': form})


@login_required
def wishlist(request):
    items = request.user.wishlist_items.select_related('product', 'product__category')
    return render(request, 'shop/wishlist/list.html', {'wishlist_items': items})


@login_required
@require_POST
def wishlist_toggle(request, product_id):
    product = get_object_or_404(Product, pk=product_id, available=True)
    item, created = WishlistItem.objects.get_or_create(
        user=request.user,
        product=product,
    )
    if created:
        messages.success(request, 'Товар добавлен в избранное.')
    else:
        item.delete()
        messages.info(request, 'Товар удалён из избранного.')

    fallback = reverse('product_detail', kwargs={'slug': product.slug})
    return redirect(_safe_next_url(request, fallback))
