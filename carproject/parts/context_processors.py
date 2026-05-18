from django.db.models import Avg, Count, Sum

from .models import CarPart, Category


def admin_dashboard_stats(request):
    if not request.path.startswith('/admin/'):
        return {}

    products = CarPart.objects.all()
    total_products = products.count()
    total_categories = Category.objects.count()
    total_value = sum(product.price * product.stock_quantity for product in products)
    avg_price = products.aggregate(avg=Avg('price'))['avg'] or 0

    return {
        'total_products': total_products,
        'total_categories': total_categories,
        'low_stock': products.filter(stock_quantity__lte=10, stock_quantity__gt=0).count(),
        'total_value': f'{total_value:,.0f}',
        'avg_price': f'{avg_price:,.0f}',
        'categories': Category.objects.all(),
        'brand_count': products.exclude(brand='').values('brand').distinct().count(),
        'vehicle_count': products.exclude(vehicle_name='').values('vehicle_name').distinct().count(),
        'dashboard_brands': products.exclude(brand='').values('brand').annotate(count=Count('id')).order_by('brand')[:8],
        'dashboard_vehicles': products.exclude(vehicle_name='').values('vehicle_name').annotate(count=Count('id')).order_by('vehicle_name')[:8],
    }
