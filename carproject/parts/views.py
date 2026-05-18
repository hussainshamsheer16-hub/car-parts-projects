from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Category, CarPart, Coupon, Order, OrderItem, WishlistItem, Review, ContactMessage

def home(request):
    """Home page showing all car parts"""
    products = CarPart.objects.all().select_related('category')
    
    # Search functionality
    search_query = request.GET.get('q')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query) |
            Q(brand__icontains=search_query) |
            Q(vehicle_name__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )
    
    # Category filter
    category_id = request.GET.get('category')
    active_category = None
    if category_id:
        products = products.filter(category_id=category_id)
        active_category = get_object_or_404(Category, id=category_id)

    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    availability = request.GET.get('availability')
    brand = request.GET.get('brand')
    vehicle_name = request.GET.get('vehicle_name')
    sort = request.GET.get('sort', 'newest')

    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)
    if availability == 'in_stock':
        products = products.filter(is_available=True, stock_quantity__gt=0)
    elif availability == 'featured':
        products = products.filter(is_featured=True)
    if brand:
        products = products.filter(brand__icontains=brand)
    if vehicle_name:
        products = products.filter(vehicle_name__icontains=vehicle_name)

    sort_options = {
        'price_low': 'price',
        'price_high': '-price',
        'name': 'name',
        'featured': '-is_featured',
        'newest': '-created_at',
    }
    products = products.order_by(sort_options.get(sort, '-created_at'))
    
    # Get all categories
    categories = Category.objects.all()
    all_products = CarPart.objects.all()
    brands = CarPart.objects.exclude(brand='').order_by('brand').values_list('brand', flat=True).distinct()
    vehicle_names = CarPart.objects.exclude(vehicle_name='').order_by('vehicle_name').values_list('vehicle_name', flat=True).distinct()
    total_stock_units = sum(product.stock_quantity for product in all_products)
    total_inventory_value = sum(product.price * product.stock_quantity for product in all_products)
    paginator = Paginator(products, 6)
    page_obj = paginator.get_page(request.GET.get('page'))
    query_params = request.GET.copy()
    query_params.pop('page', None)
    pagination_query = query_params.urlencode()
    
    context = {
        'parts': page_obj,
        'page_obj': page_obj,
        'pagination_query': pagination_query,
        'categories': categories,
        'search_query': search_query,
        'active_category': active_category,
        'min_price': min_price,
        'max_price': max_price,
        'availability': availability,
        'brand': brand,
        'vehicle_name': vehicle_name,
        'brands': brands,
        'vehicle_names': vehicle_names,
        'sort': sort,
        'total_products': all_products.count(),
        'total_categories': categories.count(),
        'featured_count': all_products.filter(is_featured=True).count(),
        'available_count': all_products.filter(is_available=True, stock_quantity__gt=0).count(),
        'total_stock_units': total_stock_units,
        'total_inventory_value': f'{total_inventory_value:,.0f}',
    }
    return render(request, 'index.html', context)

def product_detail(request, product_id):
    """Product detail page"""
    product = get_object_or_404(CarPart, id=product_id)
    related_products = CarPart.objects.filter(category=product.category).exclude(id=product.id)[:4]
    reviews = product.reviews.select_related('user')
    recently_viewed = request.session.get('recently_viewed', [])
    recently_viewed = [item for item in recently_viewed if item != product.id]
    recently_viewed.insert(0, product.id)
    request.session['recently_viewed'] = recently_viewed[:5]
    recent_products = CarPart.objects.filter(id__in=recently_viewed[1:5])
    is_wishlisted = False
    if request.user.is_authenticated:
        is_wishlisted = WishlistItem.objects.filter(user=request.user, product=product).exists()
    
    context = {
        'product': product,
        'related_products': related_products,
        'reviews': reviews,
        'recent_products': recent_products,
        'is_wishlisted': is_wishlisted,
    }
    return render(request, 'product_detail.html', context)

def category_products(request, category_id):
    """Display products by category"""
    category = get_object_or_404(Category, id=category_id)
    products = CarPart.objects.filter(category=category)
    
    context = {
        'category': category,
        'parts': products,
    }
    return render(request, 'category_products.html', context)

def add_to_cart(request, product_id):
    """Add product to cart"""
    product = get_object_or_404(CarPart, id=product_id)
    quantity = max(int(request.POST.get('quantity', 1)), 1)

    if not product.is_available or product.stock_quantity <= 0:
        messages.error(request, f'{product.name} is out of stock.')
        return redirect('product_detail', product_id=product.id)
    
    cart = request.session.get('cart', {})
    product_key = str(product_id)
    current_quantity = cart.get(product_key, {}).get('quantity', 0)
    new_quantity = min(current_quantity + quantity, product.stock_quantity)
    
    if product_key in cart:
        cart[product_key]['quantity'] = new_quantity
    else:
        cart[product_key] = {
            'name': product.name,
            'price': product.price,
            'quantity': min(quantity, product.stock_quantity),
            'image': product.image.url if product.image else '',
            'category': product.category.name,
        }
    
    request.session['cart'] = cart
    request.session.modified = True
    
    if new_quantity < current_quantity + quantity:
        messages.warning(request, f'Only {product.stock_quantity} unit(s) available for {product.name}.')
    else:
        messages.success(request, f'Added {product.name} to cart!')
    return redirect(request.POST.get('next') or 'home')

def cart_view(request):
    """View cart"""
    cart = request.session.get('cart', {})
    cart_items = []
    total = 0
    
    for key, item in cart.items():
        product = CarPart.objects.filter(id=key).first()
        if not product:
            continue
        item['quantity'] = min(item['quantity'], product.stock_quantity)
        subtotal = item['price'] * item['quantity']
        total += subtotal
        cart_items.append({
            'id': key,
            'name': item['name'],
            'price': item['price'],
            'quantity': item['quantity'],
            'subtotal': subtotal,
            'image': item.get('image', ''),
            'stock_quantity': product.stock_quantity,
        })
    
    context = {
        'cart_items': cart_items,
        'total': total,
        'cart_count': sum(item['quantity'] for item in cart.values()),
    }
    return render(request, 'cart.html', context)

def update_cart(request, product_id):
    """Update cart quantity"""
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 0))
        cart = request.session.get('cart', {})
        
        if str(product_id) in cart:
            if quantity > 0:
                product = get_object_or_404(CarPart, id=product_id)
                cart[str(product_id)]['quantity'] = min(quantity, product.stock_quantity)
            else:
                del cart[str(product_id)]
        
        request.session['cart'] = cart
        request.session.modified = True
        messages.success(request, 'Cart updated!')
    
    return redirect('cart_view')

def remove_from_cart(request, product_id):
    """Remove item from cart"""
    cart = request.session.get('cart', {})
    if str(product_id) in cart:
        del cart[str(product_id)]
        request.session['cart'] = cart
        request.session.modified = True
        messages.success(request, 'Item removed from cart!')
    
    return redirect('cart_view')

def checkout(request):
    """Checkout page"""
    cart = request.session.get('cart', {})
    
    if not cart:
        messages.warning(request, 'Your cart is empty!')
        return redirect('home')
    
    cart_items = []
    subtotal = 0
    for key, item in cart.items():
        product = get_object_or_404(CarPart, id=key)
        quantity = min(item['quantity'], product.stock_quantity)
        line_total = product.price * quantity
        subtotal += line_total
        cart_items.append({'product': product, 'name': product.name, 'price': product.price, 'quantity': quantity, 'subtotal': line_total})

    coupon_code = request.POST.get('coupon_code') or request.session.get('coupon_code')
    coupon = None
    discount_amount = 0
    if coupon_code:
        coupon = Coupon.objects.filter(code__iexact=coupon_code).first()
        if coupon and coupon.is_valid():
            request.session['coupon_code'] = coupon.code
            discount_amount = subtotal * coupon.discount_percent // 100
        elif request.method == 'POST':
            messages.error(request, 'Invalid or expired coupon code.')
    total = subtotal - discount_amount

    if request.method == 'POST' and request.POST.get('place_order') == '1':
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        email = request.POST.get('email', '').strip()
        payment_method = request.POST.get('payment_method', 'cod')

        if not full_name or not phone or not address:
            messages.error(request, 'Please enter your name, phone and address.')
        else:
            for item in cart_items:
                if item['quantity'] > item['product'].stock_quantity:
                    messages.error(request, f"Only {item['product'].stock_quantity} unit(s) available for {item['name']}.")
                    return redirect('cart_view')

            order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                full_name=full_name,
                phone=phone,
                email=email,
                address=address,
                payment_method=payment_method,
                coupon=coupon if coupon and coupon.is_valid() else None,
                subtotal=subtotal,
                discount_amount=discount_amount,
                total=total,
            )
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    product_name=item['name'],
                    price=item['price'],
                    quantity=item['quantity'],
                    subtotal=item['subtotal'],
                )
                item['product'].stock_quantity -= item['quantity']
                item['product'].is_available = item['product'].stock_quantity > 0
                item['product'].save(update_fields=['stock_quantity', 'is_available'])

            request.session['cart'] = {}
            request.session.pop('coupon_code', None)
            request.session.modified = True
            return redirect('order_success', order_id=order.id)
    
    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'discount_amount': discount_amount,
        'total': total,
        'coupon_code': coupon_code or '',
    }
    return render(request, 'checkout.html', context)

def order_success(request, order_id=None):
    """Order success page"""
    order = get_object_or_404(Order, id=order_id) if order_id else None
    return render(request, 'order_success.html', {'order': order})


@login_required
def toggle_wishlist(request, product_id):
    product = get_object_or_404(CarPart, id=product_id)
    item, created = WishlistItem.objects.get_or_create(user=request.user, product=product)
    if created:
        messages.success(request, f'{product.name} added to wishlist.')
    else:
        item.delete()
        messages.success(request, f'{product.name} removed from wishlist.')
    return redirect('product_detail', product_id=product.id)


@login_required
def wishlist_view(request):
    items = WishlistItem.objects.filter(user=request.user).select_related('product', 'product__category')
    return render(request, 'wishlist.html', {'items': items})


@login_required
def add_review(request, product_id):
    product = get_object_or_404(CarPart, id=product_id)
    if request.method == 'POST':
        rating = max(1, min(int(request.POST.get('rating', 5)), 5))
        comment = request.POST.get('comment', '').strip()
        if comment:
            Review.objects.update_or_create(
                product=product,
                user=request.user,
                defaults={'rating': rating, 'comment': comment},
            )
            messages.success(request, 'Review saved.')
        else:
            messages.error(request, 'Please write a review comment.')
    return redirect('product_detail', product_id=product.id)


@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items')
    return render(request, 'order_history.html', {'orders': orders})


def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()
        if name and email and subject and message:
            ContactMessage.objects.create(name=name, email=email, subject=subject, message=message)
            messages.success(request, 'Your message has been sent.')
            return redirect('contact')
        messages.error(request, 'Please fill all contact fields.')
    return render(request, 'contact.html')

