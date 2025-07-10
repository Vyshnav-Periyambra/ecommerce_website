from django.urls import path
from . import views

urlpatterns = [
    path('', views.user_login, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('add-product/', views.add_product, name='add_product'),
    
    path('signup/', views.user_signup, name='signup'),
    path('logout/', views.user_logout, name='logout'),
    path('product/edit/<int:product_id>/', views.edit_product, name='edit_product'),
    path('product/delete/<int:product_id>/', views.delete_product, name='delete_product'),

    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove-from-cart/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/', views.view_cart, name='view_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('process-product/<int:product_id>/', views.process_request, name='process_product'),

]



