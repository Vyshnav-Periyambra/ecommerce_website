# --- views.py ---
from datetime import datetime
import random

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from django.db.models import Sum
from django.db import transaction
from django.contrib import messages

from .models import (
    Cart, CartItem, Customer, Payment,
    Product, Profile, Supplier
)

# ======================= AUTHENTICATION ============================

@never_cache
def user_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, 'Logged in successfully.')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid credentials.')
    return render(request, 'login.html')


@never_cache
def user_logout(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


@never_cache
def user_signup(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        role = request.POST.get('role')

        customer_full_name = request.POST.get('customer_full_name')
        customer_phone = request.POST.get('customer_phone')
        customer_email = request.POST.get('customer_email')

        supplier_name = request.POST.get('supplier_name')
        supplier_company = request.POST.get('supplier_company')
        supplier_contact = request.POST.get('supplier_contact')
        supplier_email = request.POST.get('supplier_email')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'signup.html')

        if role == 'customer':
            if not all([customer_full_name, customer_phone, customer_email]):
                messages.error(request, 'All customer fields are required.')
                return render(request, 'signup.html')
            email = customer_email
        elif role == 'supplier':
            if not all([supplier_name, supplier_company, supplier_contact, supplier_email]):
                messages.error(request, 'All supplier fields are required.')
                return render(request, 'signup.html')
            email = supplier_email
        else:
            messages.error(request, 'Invalid role selected.')
            return render(request, 'signup.html')

        user = User.objects.create_user(username=username, password=password, email=email)
        Profile.objects.create(user=user, role=role)

        if role == 'customer':
            Customer.objects.create(user=user, full_name=customer_full_name, phone=customer_phone, email=email)
        else:
            Supplier.objects.create(user=user, name=supplier_name, company=supplier_company, contact_number=supplier_contact, email=email)

        messages.success(request, 'User registered successfully. You can now log in.')
        return redirect('login')

    return render(request, 'signup.html')


# ======================= DASHBOARD ============================

@login_required
@never_cache
def dashboard(request):
    try:
        profile = Profile.objects.get(user=request.user)
    except Profile.DoesNotExist:
        messages.error(request, 'Profile not found.')
        return redirect('login')

    if profile.role == 'owner':
        return handle_owner(request)
    elif profile.role == 'supplier':
        return handle_supplier(request)
    elif profile.role == 'customer':
        return handle_customer(request)

    return redirect('login')


def handle_owner(request):
    payments = Payment.objects.select_related('user').order_by('-date')
    total_profit = payments.aggregate(Sum('total_profit'))['total_profit__sum'] or 0
    total_paid = payments.aggregate(Sum('total_paid'))['total_paid__sum'] or 0

    all_products = Product.objects.all()
    approved_products = all_products.filter(status='approved')
    rejected_products = all_products.filter(status='rejected')
    new_products = approved_products.order_by('-created_at')[:10]
    pending_requests = all_products.filter(status='pending')
    low_stock_products = approved_products.filter(quantity__lt=5)

    context = {
        'user': request.user,
        'payments': payments,
        'total_profit': total_profit,
        'total_paid': total_paid,
        'products': all_products,
        'low_stock_products': low_stock_products,
        'rejected_products': rejected_products,
        'approved_products': approved_products,
        'new_products': new_products,
        'pending_requests': pending_requests,
        'suppliers': User.objects.filter(profile__role='supplier'),
        'customer': User.objects.filter(profile__role='customer'),
    }

    return render(request, 'owner_dashboard.html', context)


def handle_supplier(request):
    try:
        supplier_instance = Supplier.objects.get(user=request.user)
    except Supplier.DoesNotExist:
        messages.error(request, "No supplier record found.")
        return redirect('login')

    if request.method == 'POST':
        name = request.POST.get('name')
        category = request.POST.get('category')
        quantity = request.POST.get('quantity')
        price = request.POST.get('price')
        manufacture_date = request.POST.get('manufacture_date')
        expiry_date = request.POST.get('expiry_date')

        if not all([name, category, quantity, price, manufacture_date, expiry_date]):
            messages.error(request, "All fields are required.")
            return redirect('dashboard')

        try:
            quantity = int(quantity)
            price = float(price)
        except ValueError:
            messages.error(request, "Quantity must be an integer and price a number.")
            return redirect('dashboard')

        Product.objects.create(
            supplier=supplier_instance,
            name=name,
            category=category,
            quantity=quantity,
            price=price,
            selling_price=price,
            manufacture_date=manufacture_date,
            expiry_date=expiry_date,
            status='pending',
        )

        messages.success(request, "Request submitted successfully!")
        return redirect('dashboard')

    srequests = Product.objects.filter(supplier=supplier_instance)
    context = {
        'supplier_requests': srequests,
    }
    return render(request, 'supplier_dashboard.html', context)


def handle_customer(request):
    customer_products = Product.objects.filter(status='approved')
    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_count = cart.items.aggregate(total_quantity=Sum('quantity'))['total_quantity'] or 0

    return render(request, 'customer_dashboard.html', {
        'products': customer_products,
        'cart_count': cart_count
    })


# ======================= PRODUCT MANAGEMENT ============================

PASTEL_BACKGROUNDS = [
    'FFB3BA', 'FFDFBA', 'FFFFBA', 'BAFFC9',
    'BAE1FF', 'E0BBE4', 'D5F4E6', 'FFDAC1',
]
TEXT_COLOR = '333333'


@login_required
def add_product(request):
    if request.method == 'POST':
        supplier_id = request.POST.get('supplier')
        supplier = Supplier.objects.filter(id=supplier_id).first() if supplier_id else None

        product_name = request.POST.get('name')
        image_url = request.POST.get('image_url')

        if not image_url:
            fallback_text = product_name if product_name else 'Product'
            bg_color = random.choice(PASTEL_BACKGROUNDS)
            image_url = f'https://placehold.co/50x50/{bg_color}/{TEXT_COLOR}?text={fallback_text}'

        Product.objects.create(
            name=product_name,
            category=request.POST['category'],
            quantity=int(request.POST['quantity']),
            price=float(request.POST['price']),
            image_url=image_url,
            manufacture_date=datetime.strptime(request.POST['manufacture_date'], '%Y-%m-%d'),
            expiry_date=datetime.strptime(request.POST['expiry_date'], '%Y-%m-%d'),
            supplier=supplier,
            selling_price=float(request.POST['selling_price'])
        )

        messages.success(request, 'Product added successfully.')
        return redirect('dashboard')

    return render(request, 'add_product.html', {'suppliers': Supplier.objects.all()})


@login_required
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        product.name = request.POST['name']
        product.category = request.POST['category']
        product.quantity = int(request.POST['quantity'])
        product.price = float(request.POST['price'])
        product.selling_price = float(request.POST['selling_price'])
        product.image_url = request.POST.get('image_url', '')
        product.manufacture_date = datetime.strptime(request.POST['manufacture_date'], '%Y-%m-%d').date()
        product.expiry_date = datetime.strptime(request.POST['expiry_date'], '%Y-%m-%d')

        supplier_id = request.POST.get('supplier')
        if supplier_id:
            product.supplier = Supplier.objects.filter(id=supplier_id).first()

        product.save()
        messages.success(request, 'Product updated successfully.')
        return redirect('dashboard')

    return render(request, 'edit_product.html', {'product': product})


@login_required
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.delete()
    messages.success(request, 'Product deleted.')
    return redirect('dashboard')

@login_required
@require_http_methods(["POST"])
def process_request(request, product_id):
    profile = getattr(request.user, 'profile', None)
    if not profile or profile.role != 'owner':
        messages.error(request, 'Only owners can manage product requests.')
        return redirect('dashboard')

    action = request.POST.get('action')
    product = get_object_or_404(Product, id=product_id, status='pending')

    if action == 'approve':
        product.status = 'approved'
        product.rejection_reason = ''
        product.save()
        messages.success(request, f'Product "{product.name}" has been approved.')

    elif action == 'reject':
        reason = request.POST.get('reason', '').strip()
        if not reason:
            messages.error(request, 'Rejection reason is required.')
            return redirect('dashboard')

        product.status = 'rejected'
        product.rejection_reason = reason
        product.save()
        messages.warning(request, f'Product "{product.name}" has been rejected.')

    else:
        messages.error(request, 'Invalid action.')

    return redirect('dashboard')


# ======================= CART & CHECKOUT ============================
@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if product.quantity <= 0:
        messages.error(request, 'This product is out of stock.')
        return redirect('dashboard')

    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)

    if created:
        cart_item.quantity = 1
    else:
        if cart_item.quantity < product.quantity:
            cart_item.quantity += 1
        else:
            messages.warning(request, 'You have added the maximum available quantity.')
            return redirect('dashboard')

    cart_item.save()
    messages.success(request, 'Item added to cart.')
    return redirect('dashboard')


@login_required
def view_cart(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.select_related('product')

    for item in cart_items:
        item.item_total = item.quantity * item.product.selling_price

    total = sum(item.item_total for item in cart_items)

    return render(request, 'cart.html', {
        'cart_items': cart_items,
        'total': total,
    })


@login_required
def remove_from_cart(request, product_id):
    cart = get_object_or_404(Cart, user=request.user)
    deleted, _ = CartItem.objects.filter(cart=cart, product_id=product_id).delete()

    if deleted:
        messages.success(request, 'Item removed from cart.')
    else:
        messages.warning(request, 'Item not found in cart.')

    return redirect('view_cart')


@login_required
@transaction.atomic
def checkout(request):
    cart = get_object_or_404(Cart, user=request.user)
    cart_items = cart.items.select_related('product').select_for_update()

    if not cart_items.exists():
        messages.warning(request, 'Your cart is empty.')
        return redirect('dashboard')

    total_paid = 0
    total_profit = 0

    for item in cart_items:
        product = item.product
        quantity = item.quantity

        if quantity > product.quantity:
            messages.error(request, f'Not enough stock for {product.name}.')
            return redirect('view_cart')

        item_total = product.selling_price * quantity
        profit = (product.selling_price - product.price) * quantity

        product.quantity -= quantity
        product.save()

        total_paid += item_total
        total_profit += profit

    Payment.objects.create(
        user=request.user,
        total_paid=total_paid,
        total_profit=total_profit
    )

    cart.items.all().delete()
    messages.success(request, 'Checkout successful!')
    return render(request, 'checkout_success.html', {'total': total_paid})
