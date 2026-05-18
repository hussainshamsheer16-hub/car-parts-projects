from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum, Avg
from .models import Category, CarPart

@staff_member_required
def statistics_view(request):
    """Statistics Dashboard View"""
    # Calculate statistics
    total_products = CarPart.objects.count()
    total_categories = Category.objects.count()
    
    # Calculate total value of all products
    total_value = CarPart.objects.aggregate(total=Sum('price'))['total'] or 0
    
    # Calculate total inventory value (price * quantity)
    all_products = CarPart.objects.all()
    total_inventory_value = sum(p.price * p.stock_quantity for p in all_products)
    
    # Calculate average price
    avg_price = CarPart.objects.aggregate(avg=Avg('price'))['avg'] or 0
    
    # Stock counts
    low_stock_count = CarPart.objects.filter(stock_quantity__lte=10, stock_quantity__gt=0).count()
    out_of_stock_count = CarPart.objects.filter(stock_quantity=0).count()
    featured_count = CarPart.objects.filter(is_featured=True).count()
    
    # Category breakdown
    categories_data = []
    for category in Category.objects.all():
        products_in_category = CarPart.objects.filter(category=category)
        category_total = products_in_category.aggregate(total=Sum('price'))['total'] or 0
        categories_data.append({
            'name': category.name,
            'count': products_in_category.count(),
            'total_value': category_total,
        })

    brands_data = []
    for row in CarPart.objects.exclude(brand='').values('brand').annotate(count=Count('id')).order_by('brand'):
        brand_products = CarPart.objects.filter(brand=row['brand'])
        brands_data.append({
            'name': row['brand'],
            'count': row['count'],
            'stock': sum(product.stock_quantity for product in brand_products),
            'total_value': sum(product.price * product.stock_quantity for product in brand_products),
        })

    vehicles_data = []
    for row in CarPart.objects.exclude(vehicle_name='').values('vehicle_name').annotate(count=Count('id')).order_by('vehicle_name'):
        vehicle_products = CarPart.objects.filter(vehicle_name=row['vehicle_name'])
        vehicles_data.append({
            'name': row['vehicle_name'],
            'count': row['count'],
            'stock': sum(product.stock_quantity for product in vehicle_products),
            'total_value': sum(product.price * product.stock_quantity for product in vehicle_products),
        })
    
    context = {
        'total_products': total_products,
        'total_categories': total_categories,
        'total_value': f'{total_value:,.0f}',
        'total_inventory_value': f'{total_inventory_value:,.0f}',
        'avg_price': f'{avg_price:,.0f}',
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'featured_count': featured_count,
        'categories_data': categories_data,
        'brands_data': brands_data,
        'vehicles_data': vehicles_data,
        'brand_count': len(brands_data),
        'vehicle_count': len(vehicles_data),
    }
    return render(request, 'admin/statistics.html', context)

@staff_member_required
def inventory_report(request):
    """Inventory Report View"""
    products = CarPart.objects.all().select_related('category')
    total_inventory_value = sum(p.price * p.stock_quantity for p in products)
    
    # Calculate summary
    total_products = products.count()
    total_stock_units = sum(p.stock_quantity for p in products)
    average_stock = total_stock_units / total_products if total_products > 0 else 0
    brand_count = products.exclude(brand='').values('brand').distinct().count()
    vehicle_count = products.exclude(vehicle_name='').values('vehicle_name').distinct().count()
    
    context = {
        'products': products,
        'total_products': total_products,
        'total_inventory_value': f'{total_inventory_value:,.0f}',
        'total_stock_units': total_stock_units,
        'average_stock': f'{average_stock:.1f}',
        'brand_count': brand_count,
        'vehicle_count': vehicle_count,
    }
    return render(request, 'admin/inventory_report.html', context)
