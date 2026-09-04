from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .cart import Cart
from .forms import OrderCreateForm, ReviewForm
from .models import Category, OrderItem, Product, Review


def product_list(request, category_slug=None):
    category = None
    categories = Category.objects.all()
    products = Product.objects.filter(available=True)

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)

    query = request.GET.get('q', '').strip()
    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()

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

    sort = request.GET.get('sort', '')
    sorting = {
        'price_asc': 'price',
        'price_desc': '-price',
        'new': '-created',
    }
    if sort in sorting:
        products = products.order_by(sorting[sort])

    return render(request, 'shop/product/list.html', {
        'category': category,
        'categories': categories,
        'products': products,
        'query': query,
        'min_price': min_price,
        'max_price': max_price,
        'sort': sort,
    })


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, available=True)
    reviews = product.reviews.select_related('user').all()
    review_form = ReviewForm()
    can_review = False

    if request.user.is_authenticated:
        can_review = OrderItem.objects.filter(
            order__user=request.user,
            product=product,
        ).exists()

        if request.method == 'POST':
            if not can_review:
                messages.error(request, 'Оставить отзыв можно только после покупки товара.')
                return redirect('product_detail', slug=slug)

            existing_review = Review.objects.filter(product=product, user=request.user).first()
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
    return redirect('cart_detail')


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
                    product = Product.objects.select_for_update().get(pk=item['product'].pk)
                    if item['quantity'] > product.stock:
                        messages.error(
                            request,
                            f'Недостаточно товара «{product.name}» на складе. Доступно: {product.stock}.',
                        )
                        return redirect('cart_detail')
                    locked_products[product.pk] = product

                order = form.save(commit=False)
                if request.user.is_authenticated:
                    order.user = request.user
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
                    if product.stock == 0:
                        product.available = False
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
