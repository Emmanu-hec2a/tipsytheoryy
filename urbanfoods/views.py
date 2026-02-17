from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt as crsf_exempt
from .models import *
import json
import uuid
from urbanfoods.notifications import send_admin_order_notification, send_customer_order_confirmation
from urbanfoods.utils import notify_new_order
import logging
from .mpesa_utils import mpesa
from .models import MpesaTransaction, OrderStatusHistory
from django.db import transaction
from django.conf import settings
from decimal import Decimal

# ==================== HOMEPAGE & FOOD CATALOG ====================

def offline(request):
    """Offline page for PWA"""
    return render(request, 'offline.html')

def homepage(request):
    """Main food catalog page"""
    # Get store type from session or default to 'food'
    store_type = request.session.get('store_type', 'liquor')
    
    # Filter categories by store type
    categories = FoodCategory.objects.filter(store_type=store_type)

    # Get filter parameters
    category_id = request.GET.get('category')
    search_query = request.GET.get('q')

    # Base queryset filtered by store type
    food_items = FoodItem.objects.filter(is_available=True, store_type=store_type)

    # Apply filters
    if category_id:
        food_items = food_items.filter(category_id=category_id)
    if search_query:
        food_items = food_items.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Get special items filtered by store type
    meal_of_day = FoodItem.objects.filter(is_meal_of_day=True, is_available=True, store_type=store_type).first()
    featured_items_queryset = FoodItem.objects.filter(is_featured=True, is_available=True, store_type=store_type)[:4]
    featured_items = list(featured_items_queryset) if featured_items_queryset else []
    popular_items = FoodItem.objects.filter(is_available=True, store_type=store_type).order_by('-times_ordered')[:6]

    # Cart count
    cart_count = 0
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_count = cart.item_count

    context = {
        'categories': categories,
        'food_items': food_items,
        'meal_of_day': meal_of_day,
        'featured_items': featured_items,
        'popular_items': popular_items,
        'cart_count': cart_count,
        'selected_category': category_id,
        'search_query': search_query,
        'store_type': store_type,
    }
    return render(request, 'homepage.html', context)

@require_http_methods(["POST"])
def switch_store(request):
    """Switch between food and liquor store"""
    data = json.loads(request.body)
    store_type = data.get('store_type', 'food')
    
    if store_type in ['food', 'liquor', 'grocery']:
        # Clear cart if user is authenticated and cart has items of different store type
        if request.user.is_authenticated:
            try:
                cart, _ = Cart.objects.get_or_create(user=request.user)
                if cart.items.exists():
                    # Check if cart has items of different store type
                    cart_items = cart.items.select_related('food_item').all()
                    has_different_store_type = any(
                        item.food_item.store_type != store_type for item in cart_items
                    )
                    
                    if has_different_store_type:
                        # Clear the cart
                        cart.items.all().delete()
            except Cart.DoesNotExist:
                pass
        
        request.session['store_type'] = store_type
        return JsonResponse({'success': True, 'store_type': store_type})
    
    return JsonResponse({'success': False, 'message': 'Invalid store type'}, status=400)

# ==================== AUTHENTICATION ====================

def signup_view(request):
    """User registration"""
    if request.method == 'POST':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            data = json.loads(request.body)
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')
            phone = data.get('phone')

            # Validation
            if User.objects.filter(username=username).exists():
                return JsonResponse({'success': False, 'message': 'Username already exists'})
            if User.objects.filter(email=email).exists():
                return JsonResponse({'success': False, 'message': 'Email already registered'})

            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                phone_number=phone
            )

            # Auto login
            login(request, user)

            return JsonResponse({
                'success': True,
                'message': 'Account created successfully!',
                'redirect': '/'
            })

    return render(request, 'signup.html')

def login_view(request):
    """User login"""
    if request.method == 'POST':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            data = json.loads(request.body)
            username_or_email = data.get('username')
            password = data.get('password')
            remember = data.get('remember', False)

            user = None

            # Check if input is an email
            if '@' in username_or_email:
                try:
                    user_obj = User.objects.get(email=username_or_email)
                    user = authenticate(username=user_obj.username, password=password)
                except User.DoesNotExist:
                    pass
            else:
                # Treat as username
                user = authenticate(username=username_or_email, password=password)

            if user is not None:
                login(request, user)

                # Remember me functionality
                if not remember:
                    request.session.set_expiry(0)  # Browser close

                return JsonResponse({
                    'success': True,
                    'message': 'Login successful!',
                    'redirect': '/'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid username or password'
                })

    return render(request, 'login.html')

def logout_view(request):
    """User logout"""
    logout(request)
    return redirect('login')

# ==================== CART OPERATIONS ====================

@login_required
@require_http_methods(["POST"])
def add_to_cart(request):
    """Add item to cart"""
    data = json.loads(request.body)
    food_item_id = data.get('food_item_id')
    quantity = int(data.get('quantity', 1))

    food_item = get_object_or_404(FoodItem, id=food_item_id, is_available=True)
    cart, _ = Cart.objects.get_or_create(user=request.user)

    # Check if cart has items of different store type
    if cart.items.exists():
        cart_items = cart.items.select_related('food_item').all()
        existing_store_type = cart_items.first().food_item.store_type
        
        if existing_store_type != food_item.store_type:
            return JsonResponse({
                'success': False,
                'message': f'Cannot mix {existing_store_type} and {food_item.store_type} items in cart. Please clear your cart first or switch stores.'
            }, status=400)

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        food_item=food_item,
        defaults={'quantity': quantity}
    )

    print("USER:", request.user, request.user.is_authenticated)

    if not created:
        cart_item.quantity += quantity
        cart_item.save()

    return JsonResponse({
        'success': True,
        'message': f'{food_item.name} added to cart',
        'cart_count': cart.item_count,
        'cart_total': float(cart.total)
    })

@login_required
@require_http_methods(["POST"])
def update_cart_item(request):
    """Update cart item quantity"""
    data = json.loads(request.body)
    cart_item_id = data.get('cart_item_id')
    quantity = int(data.get('quantity'))

    cart_item = get_object_or_404(CartItem, id=cart_item_id, cart__user=request.user)

    if quantity > 0:
        cart_item.quantity = quantity
        cart_item.save()
    else:
        cart_item.delete()

    cart = cart_item.cart if quantity > 0 else request.user.cart

    return JsonResponse({
        'success': True,
        'cart_count': cart.item_count,
        'cart_total': float(cart.total),
        'item_subtotal': float(cart_item.subtotal) if quantity > 0 else 0
    })

@login_required
@require_http_methods(["POST"])
def remove_from_cart(request):
    """Remove item from cart"""
    data = json.loads(request.body)
    cart_item_id = data.get('cart_item_id')

    cart_item = get_object_or_404(CartItem, id=cart_item_id, cart__user=request.user)
    cart_item.delete()

    cart = request.user.cart

    return JsonResponse({
        'success': True,
        'message': 'Item removed from cart',
        'cart_count': cart.item_count,
        'cart_total': float(cart.total)
    })

@login_required
def get_cart(request):
    """Get cart contents"""
    cart, _ = Cart.objects.get_or_create(user=request.user)

    items = []
    for item in cart.items.all():
        items.append({
            'id': item.id,
            'food_item_id': item.food_item.id,
            'name': item.food_item.name,
            'price': float(item.food_item.price),
            'quantity': item.quantity,
            'subtotal': float(item.subtotal),
            'image': item.food_item.image.url if item.food_item.image else None
        })

    return JsonResponse({
        'success': True,
        'items': items,
        'cart_count': cart.item_count,
        'subtotal': float(cart.total),
        'delivery_fee': 0,
        'total': float(cart.total)
    })

# ==================== ORDER PLACEMENT ====================

# ==================== ORDER TRACKING ====================

@login_required
def my_orders(request):
    """User's order history"""
    orders = Order.objects.filter(user=request.user).prefetch_related('items')

    # Separate active and completed orders
    active_orders = orders.exclude(status__in=['delivered', 'cancelled'])
    order_history = orders.filter(status__in=['delivered', 'cancelled'])

    context = {
        'active_orders': active_orders,
        'order_history': order_history,
    }
    return render(request, 'my_orders.html', context)

@login_required
def order_detail(request, order_number):
    """View specific order details"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    status_history = order.status_history.all()

    context = {
        'order': order,
        'status_history': status_history,
    }
    return render(request, 'order_detail.html', context)

@login_required
def order_status_api(request, order_number):
    """API endpoint for order status polling"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    return JsonResponse({
        'success': True,
        'status': order.status,
        'status_display': order.get_status_display(),
        'updated_at': order.updated_at.isoformat()
    })

# ==================== USER PROFILE ====================

@login_required
def profile(request):
    """User profile page"""
    if request.method == 'POST':
        user = request.user
        user.phone_number = request.POST.get('phone_number')
        user.default_hostel = request.POST.get('default_hostel')
        user.default_room = request.POST.get('default_room')
        user.save()

        return redirect('profile')

    recent_orders = Order.objects.filter(user=request.user)[:5]

    context = {
        'recent_orders': recent_orders,
    }
    return render(request, 'profile.html', context)

# ==================== ORDER RATING ====================

@login_required
@require_http_methods(["POST"])
def rate_order(request, order_number):
    """Rate and review a delivered order"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user, status='delivered')

    if order.rating:
        return JsonResponse({'success': False, 'message': 'Order already rated'})

    rating = request.POST.get('rating')
    review = request.POST.get('review', '')

    if not rating or not rating.isdigit() or int(rating) < 1 or int(rating) > 5:
        return JsonResponse({'success': False, 'message': 'Invalid rating'})

    order.rating = int(rating)
    order.review = review
    order.save()

    return redirect('order_detail', order_number=order_number)

# ==================== FOOD REVIEWS ====================

@login_required
@require_http_methods(["POST"])
def submit_food_review(request, order_number):
    try:
        order = Order.objects.get(order_number=order_number, user=request.user)
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Order not found'}, status=404)

    if order.status != 'delivered':
        return JsonResponse({'success': False, 'message': 'You can only review delivered orders'}, status=400)

    for item in order.items.all():
        rating = request.POST.get(f'rating-{item.food_item.id}')
        comment = request.POST.get(f'comment-{item.food_item.id}', '')

        if rating:
            if not FoodReview.objects.filter(user=request.user, food_item=item.food_item, order=order).exists():
                FoodReview.objects.create(
                    user=request.user,
                    food_item=item.food_item,
                    order=order,
                    rating=rating,
                    comment=comment
                )

    return redirect('order_detail', order_number=order.order_number)


# ==================== ORDER CANCELLATION ====================

@login_required
@require_http_methods(["POST"])
def cancel_order(request, order_number):
    """Cancel an order with reason"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    # Only allow cancellation for pending or preparing orders
    if order.status not in ['pending', 'preparing']:
        return JsonResponse({'success': False, 'message': 'Order cannot be cancelled at this stage'})

    reason = request.POST.get('reason', '').strip()
    if not reason:
        return JsonResponse({'success': False, 'message': 'Please provide a cancellation reason'})

    # Update order status
    order.status = 'cancelled'
    order.cancellation_reason = reason
    order.save()

    # Create status history
    OrderStatusHistory.objects.create(
        order=order,
        status='cancelled',
        notes=f'Cancelled by user: {reason}'
    )

    return JsonResponse({'success': True, 'message': 'Order cancelled successfully'})

# ==================== MPESA INTEGRATION ====================

@login_required
@require_http_methods(["POST"])
def initiate_mpesa_payment(request):
    """Initiate MPESA payment for an existing order"""
    data = json.loads(request.body)
    order_number = data.get('order_number')

    if not order_number:
        return JsonResponse({'success': False, 'message': 'Order number required'})

    try:
        order = Order.objects.get(order_number=order_number, user=request.user)
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Order not found'})

    if order.payment_status == 'completed':
        return JsonResponse({'success': False, 'message': 'Payment already completed'})

    from .mpesa_utils import mpesa

    try:
        # Format phone number for MPESA
        formatted_phone = mpesa.format_phone_number(order.phone_number)

        # Initiate STK push
        stk_result = mpesa.initiate_stk_push(
            phone_number=formatted_phone,
            amount=int(order.total),
            account_reference=order.order_number,
            transaction_desc=f"Payment for Order {order.order_number}",
            store_type=order.store_type
        )

        if stk_result['success']:
            # Update order with MPESA details
            order.mpesa_checkout_request_id = stk_result['checkout_request_id']
            order.payment_status = 'processing'
            order.save()

            # Create status history
            OrderStatusHistory.objects.create(
                order=order,
                status=order.status,
                notes=f'MPESA payment initiated. STK Push sent to {order.phone_number}'
            )

            return JsonResponse({
                'success': True,
                'message': stk_result['customer_message'],
                'checkout_request_id': stk_result['checkout_request_id']
            })
        else:
            return JsonResponse({
                'success': False,
                'message': stk_result['message']
            })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Payment initiation failed: {str(e)}'
        })

import json
import logging
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Cart, MpesaTransaction, Order, OrderItem, OrderStatusHistory
from .mpesa_utils import mpesa

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
#  SAFARICOM IP ALLOWLIST
#  https://developer.safaricom.co.ke/docs#callbacks
# ─────────────────────────────────────────────────────────────
SAFARICOM_IPS = {
    '196.201.214.200', '196.201.214.206', '196.201.213.114',
    '196.201.214.207', '196.201.214.208', '196.201.213.44',
    '196.201.212.127', '196.201.212.138', '125.163.154.12',
}


def _get_client_ip(request):
    """Return the real client IP, respecting X-Forwarded-For from trusted proxies."""
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def safaricom_ip_required(view_func):
    """
    Decorator that rejects requests not originating from Safaricom's
    known callback IPs with a silent 403.
    """
    def wrapper(request, *args, **kwargs):
        if _get_client_ip(request) not in SAFARICOM_IPS:
            logger.warning(
                "Blocked callback attempt from unauthorized IP: %s",
                _get_client_ip(request)
            )
            return HttpResponse(status=403)
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


# ─────────────────────────────────────────────────────────────
#  SHARED PAYMENT CONFIRMATION  (single source of truth)
# ─────────────────────────────────────────────────────────────
def _confirm_payment(order, receipt_number=None, notes='Payment confirmed'):
    """
    Mark an order as fully paid. Handles all side-effects so both
    the callback and the STK-query fallback stay in sync automatically.

    Must be called inside a transaction.atomic() block.
    """
    order.payment_status = 'completed'
    order.status = 'pending'
    order.payment_completed_at = timezone.now()
    if receipt_number:
        order.mpesa_receipt_number = receipt_number
    order.save()

    # ── Update sales stats atomically with F() + bulk_update ──
    items = list(order.items.select_related('food_item'))
    for item in items:
        # F() defers the increment to the DB — race-condition safe
        item.food_item.times_ordered = F('times_ordered') + item.quantity

    from .models import FoodItem  # local import avoids circular at module level
    FoodItem.objects.bulk_update(
        [item.food_item for item in items],
        ['times_ordered']
    )

    # ── Clear cart (items only — keep the Cart row for future orders) ──
    Cart.objects.filter(user=order.user).first() and \
        Cart.objects.filter(user=order.user).first().items.all().delete()
    # Cleaner version:
    from .models import CartItem
    CartItem.objects.filter(cart__user=order.user).delete()

    # ── Award loyalty points ──
    order.user.loyalty_points = F('loyalty_points') + int(order.total)
    order.user.save(update_fields=['loyalty_points'])

    # ── Status history ──
    OrderStatusHistory.objects.create(
        order=order,
        status='pending',
        notes=notes
    )

    # ── Notifications ──
    notify_new_order(order)
    send_customer_order_confirmation(order)
    send_admin_order_notification(order)


def _fail_payment(order, reason=''):
    """Mark an order payment as failed — no atomic block needed (simple update)."""
    order.payment_status = 'failed'
    order.status = 'cancelled'
    order.payment_failure_reason = reason
    order.save(update_fields=['payment_status', 'status', 'payment_failure_reason'])

    OrderStatusHistory.objects.create(
        order=order,
        status='cancelled',
        notes=f'Payment failed: {reason}'
    )


# ─────────────────────────────────────────────────────────────
#  PLACE ORDER
# ─────────────────────────────────────────────────────────────
@login_required
@require_http_methods(["POST"])
def place_order(request):
    """Place a new order (M-Pesa or Cash on Delivery)."""
    data = json.loads(request.body)

    cart = get_object_or_404(Cart, user=request.user)

    if not cart.items.exists():
        return JsonResponse({'success': False, 'message': 'Cart is empty'})

    hostel = data.get('hostel')
    room_number = data.get('room_number')
    phone_number = data.get('phone_number')
    delivery_notes = data.get('delivery_notes', '')
    payment_method = data.get('payment_method', 'cash')

    if payment_method not in ['mpesa', 'cash']:
        return JsonResponse({'success': False, 'message': 'Invalid payment method'})

    # ── Totals ──
    subtotal = cart.total
    first_item = cart.items.select_related('food_item').first()
    store_type = first_item.food_item.store_type if first_item else 'liquor'
    delivery_fee = 0 if store_type == 'food' else 20
    total = subtotal + delivery_fee
    estimated_delivery = timezone.now() + timezone.timedelta(minutes=30)

    # ══════════════════════════════
    #  M-PESA PAYMENT
    # ══════════════════════════════
    if payment_method == 'mpesa':
        try:
            formatted_phone = mpesa.format_phone_number(phone_number)
        except ValueError as e:
            return JsonResponse({'success': False, 'message': str(e)})

        try:
            with transaction.atomic():
                order = Order.objects.create(
                    user=request.user,
                    hostel=hostel,
                    room_number=room_number,
                    phone_number=formatted_phone,
                    delivery_notes=delivery_notes,
                    subtotal=subtotal,
                    delivery_fee=delivery_fee,
                    total=total,
                    payment_method='mpesa',
                    store_type=store_type,
                    payment_type='paybill',
                    payment_status='pending',
                    status='payment_pending',
                    estimated_delivery=estimated_delivery,
                )

                OrderItem.objects.bulk_create([
                    OrderItem(
                        order=order,
                        food_item=item.food_item,
                        quantity=item.quantity,
                        price_at_order=item.food_item.price,
                    )
                    for item in cart.items.select_related('food_item')
                ])

                OrderStatusHistory.objects.create(
                    order=order,
                    status='payment_pending',
                    notes='Order created — awaiting M-Pesa STK payment',
                )

                # ── Initiate STK push ──
                stk_response = mpesa.initiate_stk_push(
                    phone_number=formatted_phone,
                    amount=int(total),
                    account_reference=order.order_number,
                    transaction_desc="Tipsy Theoryy Order",
                    store_type=store_type,
                )

                if not stk_response.get('success'):
                    # Let atomic() roll back the order
                    raise Exception(stk_response.get('message', 'STK push failed'))

                checkout_request_id = stk_response.get('checkout_request_id')
                if not checkout_request_id:
                    raise Exception('No checkout_request_id returned by Safaricom')

                order.mpesa_checkout_request_id = checkout_request_id
                order.save(update_fields=['mpesa_checkout_request_id'])

        except Exception as e:
            logger.exception("M-Pesa STK push failed for user %s", request.user.id)
            return JsonResponse({
                'success': False,
                'message': f'Payment initiation failed: {e}',
            })

        return JsonResponse({
            'success': True,
            'message': stk_response.get('customer_message', 'STK push sent — check your phone'),
            'order_number': order.order_number,
            'checkout_request_id': order.mpesa_checkout_request_id,
            'payment_method': 'mpesa',
            'estimated_delivery': estimated_delivery.strftime('%I:%M %p'),
            'awaiting_payment': True,
        })

    # ══════════════════════════════
    #  CASH ON DELIVERY
    # ══════════════════════════════
    with transaction.atomic():
        order = Order.objects.create(
            user=request.user,
            hostel=hostel,
            room_number=room_number,
            phone_number=phone_number,
            delivery_notes=delivery_notes,
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            total=total,
            payment_method='cash',
            store_type=store_type,
            payment_status='pending',
            status='pending',
            estimated_delivery=estimated_delivery,
        )

        OrderItem.objects.bulk_create([
            OrderItem(
                order=order,
                food_item=item.food_item,
                quantity=item.quantity,
                price_at_order=item.food_item.price,
            )
            for item in cart.items.select_related('food_item')
        ])

        # ── Update stats atomically ──
        cart_items = list(cart.items.select_related('food_item'))
        for cart_item in cart_items:
            cart_item.food_item.times_ordered = F('times_ordered') + cart_item.quantity

        from .models import FoodItem
        FoodItem.objects.bulk_update(
            [ci.food_item for ci in cart_items],
            ['times_ordered']
        )

        # ── Clear cart items (keep Cart row) ──
        cart.items.all().delete()

        # ── Award loyalty points ──
        order.user.loyalty_points = F('loyalty_points') + int(total)
        order.user.save(update_fields=['loyalty_points'])

        OrderStatusHistory.objects.create(
            order=order,
            status='pending',
            notes='Order placed — Cash on delivery',
        )

        notify_new_order(order)
        send_customer_order_confirmation(order)
        send_admin_order_notification(order)

    return JsonResponse({
        'success': True,
        'message': 'Order placed successfully!',
        'order_number': order.order_number,
        'payment_method': 'cash',
        'estimated_delivery': estimated_delivery.strftime('%I:%M %p'),
    })


# ─────────────────────────────────────────────────────────────
#  M-PESA CALLBACK  (called by Safaricom — no auth, IP-guarded)
# ─────────────────────────────────────────────────────────────
@csrf_exempt                  # Safaricom cannot send CSRF tokens
@safaricom_ip_required        # Only accept known Safaricom IPs
@require_http_methods(["POST"])
def mpesa_callback(request):
    try:
        callback_data = json.loads(request.body)
        stk_callback = callback_data.get('Body', {}).get('stkCallback', {})
        result_code = stk_callback.get('ResultCode')
        result_desc = stk_callback.get('ResultDesc', '')
        checkout_request_id = stk_callback.get('CheckoutRequestID')

        if not checkout_request_id:
            return HttpResponse("OK")

        try:
            order = Order.objects.select_related('user').get(
                mpesa_checkout_request_id=checkout_request_id
            )
        except Order.DoesNotExist:
            logger.warning(
                "Callback received for unknown CheckoutRequestID: %s",
                checkout_request_id,
            )
            return HttpResponse("OK")

        # ── Idempotency guard ──
        if order.payment_status == 'completed':
            return HttpResponse("OK")

        # ── Parse callback metadata ──
        metadata = stk_callback.get('CallbackMetadata', {}).get('Item', [])
        mpesa_receipt = None
        callback_phone = None
        amount = None

        for item in metadata:
            name = item.get('Name')
            if name == 'MpesaReceiptNumber': mpesa_receipt = item.get('Value')
            elif name == 'PhoneNumber': callback_phone = item.get('Value')
            elif name == 'Amount': amount = item.get('Value')

        # ── Always persist the raw transaction (audit trail) ──
        MpesaTransaction.objects.create(
            order=order,
            checkout_request_id=checkout_request_id,
            mpesa_receipt_number=mpesa_receipt,
            phone_number=str(callback_phone) if callback_phone else '',
            amount=Decimal(str(amount)) if amount else Decimal('0.00'),
            result_code=result_code,
            result_desc=result_desc,
            raw_callback=callback_data,
        )

        # ── Payment failed ──
        if result_code != 0:
            _fail_payment(order, reason=result_desc)
            return HttpResponse("OK")

        # ── Validate amount ──
        if Decimal(str(amount)) != order.total:
            _fail_payment(order, reason=f'Amount mismatch: got {amount}, expected {order.total}')
            logger.error(
                "Amount mismatch on order %s: received %s expected %s",
                order.order_number, amount, order.total,
            )
            return HttpResponse("OK")

        # ── Validate phone ──
        try:
            expected_phone = mpesa.format_phone_number(order.phone_number)
        except ValueError:
            expected_phone = order.phone_number

        if str(callback_phone) != expected_phone:
            _fail_payment(order, reason=f'Phone mismatch: got {callback_phone}')
            logger.error(
                "Phone mismatch on order %s: received %s expected %s",
                order.order_number, callback_phone, expected_phone,
            )
            return HttpResponse("OK")

        # ── All checks passed — confirm payment ──
        with transaction.atomic():
            _confirm_payment(
                order,
                receipt_number=mpesa_receipt,
                notes=f'Payment confirmed via callback. Receipt: {mpesa_receipt}',
            )

    except Exception:
        logger.exception("Unhandled error in mpesa_callback")

    return HttpResponse("OK")


# ─────────────────────────────────────────────────────────────
#  STK QUERY  (client-side polling fallback)
# ─────────────────────────────────────────────────────────────
@login_required
@require_http_methods(["POST"])
def mpesa_stk_query(request):
    """
    Fallback for when the Safaricom callback is delayed.
    The frontend polls this endpoint while the payment modal is open.
    """
    data = json.loads(request.body)
    checkout_request_id = data.get('checkout_request_id')

    if not checkout_request_id:
        return JsonResponse({'success': False, 'message': 'checkout_request_id required'})

    # ── Guard: only allow the order owner to query ──
    try:
        order = Order.objects.select_related('user').get(
            mpesa_checkout_request_id=checkout_request_id,
            user=request.user,          # prevents other users querying someone else's order
        )
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Order not found'})

    # ── Idempotency: already done via callback ──
    if order.payment_status == 'completed':
        return JsonResponse({
            'success': True,
            'result_code': 0,
            'result_desc': 'Payment already confirmed',
            'payment_status': 'completed',
        })

    # ── Ask Safaricom ──
    result = mpesa.query_stk_status(checkout_request_id)

    if not result.get('success'):
        return JsonResponse(result)

    result_code = result.get('result_code')

    if result_code == 0:
        # Payment successful — reuse shared helper
        with transaction.atomic():
            _confirm_payment(
                order,
                notes='Payment confirmed via STK query',
            )
        result['payment_status'] = 'completed'

    elif result_code in [1, 1032, 1037]:
        # 1    = Insufficient funds
        # 1032 = Request cancelled by user
        # 1037 = DS timeout (user never responded)
        _fail_payment(order, reason=result.get('result_desc', 'Payment failed'))
        result['payment_status'] = 'failed'

    else:
        # Still pending — tell the frontend to keep polling
        result['payment_status'] = 'pending'

    return JsonResponse(result)


# ─────────────────────────────────────────────────────────────
#  PAYMENT STATUS POLL  (lightweight, cacheable)
# ─────────────────────────────────────────────────────────────
@login_required
@require_http_methods(["GET"])
def check_order_payment_status(request, order_number):
    """
    Lightweight endpoint for the frontend payment-waiting screen.
    Returns only what the UI needs — no sensitive data.
    """
    try:
        order = Order.objects.only(
            'payment_status', 'status', 'mpesa_receipt_number'
        ).get(order_number=order_number, user=request.user)
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Order not found'}, status=404)

    return JsonResponse({
        'success': True,
        'payment_status': order.payment_status,
        'order_status': order.status,
        'mpesa_receipt_number': order.mpesa_receipt_number,
    })


# ─────────────────────────────────────────────────────────────
#  INITIATE MPESA PAYMENT  (retry for existing order)
# ─────────────────────────────────────────────────────────────
@login_required
@require_http_methods(["POST"])
def initiate_mpesa_payment(request):
    """Re-initiate an STK push for an existing unpaid order."""
    data = json.loads(request.body)
    order_number = data.get('order_number')

    if not order_number:
        return JsonResponse({'success': False, 'message': 'Order number required'})

    try:
        order = Order.objects.get(order_number=order_number, user=request.user)
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Order not found'})

    if order.payment_status == 'completed':
        return JsonResponse({'success': False, 'message': 'Payment already completed'})

    try:
        formatted_phone = mpesa.format_phone_number(order.phone_number)
    except ValueError as e:
        return JsonResponse({'success': False, 'message': str(e)})

    stk_result = mpesa.initiate_stk_push(
        phone_number=formatted_phone,
        amount=int(order.total),
        account_reference=order.order_number,
        transaction_desc=f"Order {order.order_number}",
        store_type=order.store_type,
    )

    if not stk_result.get('success'):
        return JsonResponse({'success': False, 'message': stk_result.get('message')})

    order.mpesa_checkout_request_id = stk_result['checkout_request_id']
    order.payment_status = 'pending'
    order.save(update_fields=['mpesa_checkout_request_id', 'payment_status'])

    OrderStatusHistory.objects.create(
        order=order,
        status=order.status,
        notes=f"STK push re-sent to {formatted_phone}",
    )

    return JsonResponse({
        'success': True,
        'message': stk_result.get('customer_message', 'STK push sent'),
        'checkout_request_id': stk_result['checkout_request_id'],
    })