import csv

from django.contrib import admin
from django.http import HttpResponse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import (
    CarPart,
    Category,
    ContactMessage,
    Coupon,
    Order,
    OrderItem,
    Review,
    WishlistItem,
)


admin.site.site_header = "DriveGear Performance Admin"
admin.site.site_title = "DriveGear Admin Portal"
admin.site.index_title = "Welcome to DriveGear Performance Parts Dashboard"
admin.site.index_template = 'admin/index.html'


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'product_count_display')
    search_fields = ('name',)
    list_per_page = 20

    def product_count_display(self, obj):
        return format_html(
            '<span style="color: #c9a96e; font-weight: bold;">{}</span>',
            obj.carpart_set.count(),
        )
    product_count_display.short_description = 'Total Products'


class CarPartAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'thumbnail_preview',
        'name',
        'brand',
        'vehicle_name',
        'price',
        'category',
        'stock_status_display',
        'stock_quantity',
        'is_featured',
        'created_at',
    )
    list_display_links = ('name',)
    list_editable = ('price', 'stock_quantity', 'is_featured')
    list_filter = ('category', 'brand', 'vehicle_name', 'is_featured', 'is_available', 'created_at')
    search_fields = ('name', 'description', 'brand', 'vehicle_name')
    list_per_page = 25
    date_hierarchy = 'created_at'
    readonly_fields = ('image_preview_large', 'created_at', 'updated_at')
    actions = ['bulk_20_percent_discount', 'export_to_csv', 'mark_in_stock', 'mark_featured']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'brand', 'vehicle_name', 'category', 'price', 'description'),
            'description': 'Enter the product, brand, vehicle fitment and pricing details.',
        }),
        ('Media & Images', {
            'fields': ('image', 'image_preview_large'),
            'classes': ('wide',),
        }),
        ('Inventory Management', {
            'fields': ('stock_quantity', 'low_stock_threshold', 'is_available'),
            'classes': ('collapse',),
        }),
        ('Marketing & Visibility', {
            'fields': ('is_featured',),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def thumbnail_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="50" height="50" style="border-radius: 8px; object-fit: cover; border: 1px solid #c9a96e;" />',
                obj.image.url,
            )
        return mark_safe('<span style="color: #999;">No Image</span>')
    thumbnail_preview.short_description = 'Preview'

    def image_preview_large(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="200" style="border-radius: 12px; border: 2px solid #c9a96e;" /><br>'
                '<span style="font-size: 11px; color: #666;">Current product image</span>',
                obj.image.url,
            )
        return "No image uploaded"
    image_preview_large.short_description = 'Image Preview'

    def stock_status_display(self, obj):
        if obj.stock_quantity <= 0:
            return mark_safe('<span style="color: #ff6b6b; font-weight: bold;">OUT OF STOCK</span>')
        if obj.stock_quantity <= obj.low_stock_threshold:
            return format_html(
                '<span style="color: #ffa500; font-weight: bold;">LOW STOCK ({})</span>',
                obj.stock_quantity,
            )
        return format_html(
            '<span style="color: #51cf66; font-weight: bold;">IN STOCK ({})</span>',
            obj.stock_quantity,
        )
    stock_status_display.short_description = 'Stock Status'

    def bulk_20_percent_discount(self, request, queryset):
        for product in queryset:
            product.price = int(product.price * 0.8)
            product.save()
        self.message_user(request, f'Applied 20% discount to {queryset.count()} product(s).')
    bulk_20_percent_discount.short_description = 'Apply 20%% discount to selected'

    def export_to_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="drivegear_products_export.csv"'

        writer = csv.writer(response)
        writer.writerow(['ID', 'Name', 'Brand', 'Vehicle', 'Price', 'Category', 'Stock', 'Featured', 'Created Date'])

        for product in queryset:
            writer.writerow([
                product.id,
                product.name,
                product.brand,
                product.vehicle_name,
                f'Rs {product.price}',
                product.category.name,
                product.stock_quantity,
                'Yes' if product.is_featured else 'No',
                product.created_at.strftime('%Y-%m-%d') if product.created_at else '',
            ])

        self.message_user(request, 'Products exported successfully.')
        return response
    export_to_csv.short_description = 'Export selected to CSV'

    def mark_in_stock(self, request, queryset):
        queryset.update(stock_quantity=100, is_available=True)
        self.message_user(request, f'Marked {queryset.count()} product(s) as in stock.')
    mark_in_stock.short_description = 'Mark selected as in stock'

    def mark_featured(self, request, queryset):
        queryset.update(is_featured=True)
        self.message_user(request, f'{queryset.count()} product(s) marked as featured.')
    mark_featured.short_description = 'Mark selected as featured'


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product_name', 'price', 'quantity', 'subtotal')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'phone', 'payment_method', 'status', 'total', 'created_at')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('full_name', 'phone', 'email', 'address')
    list_editable = ('status',)
    inlines = [OrderItemInline]
    readonly_fields = ('subtotal', 'discount_amount', 'total', 'created_at')


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percent', 'is_active', 'valid_until')
    list_editable = ('discount_percent', 'is_active')
    search_fields = ('code',)


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')
    search_fields = ('user__username', 'product__name')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('product__name', 'user__username', 'comment')


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'name', 'email', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('subject', 'name', 'email', 'message')
    list_editable = ('is_read',)


admin.site.register(Category, CategoryAdmin)
admin.site.register(CarPart, CarPartAdmin)
