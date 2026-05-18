from django.urls import path
from . import views

# This is the app_name - IMPORTANT!
urlpatterns = [
    # Home page - THIS IS THE 'home' URL that your template is looking for
    path('', views.home, name='home'),  # ← This creates the 'home' name
    
    # Product detail
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    
    # Category pages
    path('category/<int:category_id>/', views.category_products, name='category_products'),
    
    # Cart URLs
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:product_id>/', views.update_cart, name='update_cart'),
    
    # Checkout
    path('checkout/', views.checkout, name='checkout'),
    path('order-success/', views.order_success, name='order_success'),
    path('order-success/<int:order_id>/', views.order_success, name='order_success'),
    path('orders/', views.order_history, name='order_history'),
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/<int:product_id>/', views.toggle_wishlist, name='toggle_wishlist'),
    path('review/<int:product_id>/', views.add_review, name='add_review'),
    path('contact/', views.contact, name='contact'),
    
]
