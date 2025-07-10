from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('supplier', 'Supplier'),
        ('customer', 'Customer'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    def __str__(self):
        return f"{self.user.username} - {self.role}"


class Supplier(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    company = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.user.username} - {self.company}"
    
class Product(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=100)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    image_url = models.URLField(max_length=200, blank=True, null=True)
    manufacture_date = models.DateField()
    expiry_date = models.DateField()
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)  
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending') 
    rejection_reason = models.TextField(blank=True, null=True)
    
    def is_low_stock(self):
        return self.quantity < 5
    
    def __str__(self):
        return self.name

class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    email = models.EmailField(unique=True)
    address = models.TextField()
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)

    def __str__(self):
        return self.user.username


class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    total_paid = models.DecimalField(max_digits=10, decimal_places=2)
    total_profit = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment by {self.user.username if self.user else 'Unknown'} on {self.date.strftime('%Y-%m-%d %H:%M')}"


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart of {self.user.username}"

    def get_total(self):
        return sum(item.get_total_price() for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    def get_total_price(self):
        return self.product.selling_price * self.quantity
