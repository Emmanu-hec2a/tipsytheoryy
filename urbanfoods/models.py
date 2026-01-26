from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid

class User(AbstractUser):
    """Extended user model for students"""
    phone_number = models.CharField(max_length=15, blank=True)
    default_hostel = models.CharField(max_length=100, blank=True)
    default_room = models.CharField(max_length=50, blank=True)
    student_email = models.EmailField(unique=True, null=True, blank=True)
    loyalty_points = models.IntegerField(default=0)
    is_verified = models.BooleanField(default=False)
    
    def __str__(self):
        return self.username

class FoodCategory(models.Model):
    """Categories for organizing food items"""
    STORE_CHOICES = [
        ('food', 'Food Store'),
        ('liquor', 'Liquor Store'),
        ('grocery', 'Grocery Shop'),
    ]

    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)  # emoji or icon class
    order = models.IntegerField(default=0)  # for sorting
    store_type = models.CharField(max_length=10, choices=STORE_CHOICES, default='liquor')
    stock_quantity = models.PositiveIntegerField(default=0, help_text="Available stock for this category (for liquor store)")
    
    class Meta:
        verbose_name_plural = "Food Categories"
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name

class FoodItem(models.Model):
    """Individual food items available for order"""
    STORE_CHOICES = [
        ('food', 'Food Store'),
        ('liquor', 'Liquor Store'),
        ('grocery', 'Grocery Shop'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    category = models.ForeignKey(FoodCategory, on_delete=models.CASCADE, related_name='items')
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    image = models.ImageField(upload_to='food_images/')
    prep_time = models.IntegerField(help_text="Preparation time in minutes", default=15)
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_meal_of_day = models.BooleanField(default=False)
    times_ordered = models.IntegerField(default=0)  # for popularity tracking
    store_type = models.CharField(max_length=10, choices=STORE_CHOICES, default='liquor')
    bottle_size = models.CharField(max_length=20, blank=True, help_text="For liquor items (e.g., 250ml, 500ml, 750ml)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def is_liquor(self):
        return self.store_type == 'liquor'

    @property
    def average_rating(self):
        reviews = self.reviews.all()
        if reviews.exists():
            return round(sum(review.rating for review in reviews) / reviews.count(), 1)
        return 0

    @property
    def review_count(self):
        return self.reviews.count()
    
    class Meta:
        ordering = ['-is_featured', '-times_ordered', 'name']
    
    def __str__(self):
        return f"{self.name} - KES {self.price}"

class Cart(models.Model):
    """Shopping cart for each user"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Cart for {self.user.username}"
    
    @property
    def total(self):
        return sum(item.subtotal for item in self.items.all())
    
    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())

class CartItem(models.Model):
    """Individual items in a cart"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    food_item = models.ForeignKey(FoodItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['cart', 'food_item']
    
    @property
    def subtotal(self):
        return self.food_item.price * self.quantity
    
    def __str__(self):
        return f"{self.quantity}x {self.food_item.name}"

class Order(models.Model):
    """Customer orders"""
    STATUS_CHOICES = [
        ('payment_pending', 'Payment Pending'),
        ('pending', 'Pending'),
        ('preparing', ' Preparing'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    order_number = models.CharField(max_length=20, unique=True, editable=False)
    is_test_order = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Delivery information
    hostel = models.CharField(max_length=100)
    room_number = models.CharField(max_length=50)
    phone_number = models.CharField(max_length=15)
    delivery_notes = models.TextField(blank=True)
    
    # Pricing
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    estimated_delivery = models.DateTimeField(null=True, blank=True, default=30)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    # Payment information
    payment_method = models.CharField(max_length=10, choices=[('mpesa', 'MPESA'), ('till', 'TILL')], default='till')
    payment_status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled')
    ], default='pending')
    payment_type = models.CharField(max_length=20, choices=[
        ('till', 'Till Number'),
        ('paybill', 'Paybill Number')
    ], blank=True, null=True)
    payment_completed_at = models.DateTimeField(null=True, blank=True)
    payment_failure_reason = models.TextField(blank=True, null=True)

    # Store type for the order
    store_type = models.CharField(max_length=10, choices=[
        ('food', 'Food Store'),
        ('liquor', 'Liquor Store'),
        ('grocery', 'Grocery Shop')
    ], default='liquor')

    # MPESA specific fields
    mpesa_checkout_request_id = models.CharField(max_length=50, blank=True, null=True)
    mpesa_receipt_number = models.CharField(max_length=20, blank=True, null=True)
    mpesa_transaction_date = models.CharField(max_length=20, blank=True, null=True)

    # Additional fields
    cancellation_reason = models.TextField(blank=True)
    rating = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    review = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            # Generate unique order number
            self.order_number = f"UF{timezone.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Order {self.order_number} - {self.user.username}"

class OrderItem(models.Model):
    """Items in an order"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    food_item = models.ForeignKey(FoodItem, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    price_at_order = models.DecimalField(max_digits=10, decimal_places=2)  # Price snapshot
    
    @property
    def subtotal(self):
        return self.price_at_order * self.quantity
    
    def __str__(self):
        return f"{self.quantity}x {self.food_item.name} (Order: {self.order.order_number})"

class OrderStatusHistory(models.Model):
    """Track order status changes"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    status = models.CharField(max_length=20)
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['timestamp']
        verbose_name_plural = "Order Status Histories"
    
    def __str__(self):
        return f"{self.order.order_number} - {self.status} at {self.timestamp}"

class FoodReview(models.Model):
    """Reviews for food items"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    food_item = models.ForeignKey(FoodItem, on_delete=models.CASCADE, related_name='reviews')
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'food_item', 'order']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.food_item.name} ({self.rating}★)"

class Promotion(models.Model):
    """Promotional offers and deals"""
    title = models.CharField(max_length=200)
    description = models.TextField()
    code = models.CharField(max_length=20, unique=True, blank=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    usage_limit = models.IntegerField(null=True, blank=True)
    times_used = models.IntegerField(default=0)
    
    def __str__(self):
        return self.title
    
class PushSubscription(models.Model):
    endpoint = models.TextField(unique=True)
    keys = models.JSONField()  # stores 'p256dh' and 'auth'
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.endpoint