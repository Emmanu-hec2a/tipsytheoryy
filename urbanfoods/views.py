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
            username = data.get('username')
            password = data.get('password')
            remember = data.get('remember', False)

            user = authenticate(username=username, password=password)

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

@login_required
@require_http_methods(["POST"])
def place_order(request):
    """Place a new order"""
    data = json.loads(request.body)

    cart = get_object_or_404(Cart, user=request.user)

    if not cart.items.exists():
        return JsonResponse({'success': False, 'message': 'Cart is empty'})

    # Extract order details
    hostel = data.get('hostel')
    room_number = data.get('room_number')
    phone_number = data.get('phone_number')
    delivery_notes = data.get('delivery_notes', '')
    payment_method = data.get('payment_method', 'cash')

    if payment_method not in ['manual', 'cash']:
        return JsonResponse({'success': False, 'message': 'Invalid payment method'})

    # Calculate totals
    subtotal = cart.total
    store_type = cart.items.first().food_item.store_type if cart.items.exists() else 'food'
    delivery_fee = 0 if store_type == 'food' else 20
    total = subtotal + delivery_fee

    # Generate order number
    order_number = f"TT{timezone.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"

    # Manual payment logic
    if payment_method == 'manual':
        order = Order.objects.create(
            order_number=order_number,
            user=request.user,
            hostel=hostel,
            room_number=room_number,
            phone_number=phone_number,
            delivery_notes=delivery_notes,
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            total=total,
            payment_method=payment_method,
            store_type=store_type,
            payment_type='paybill' if store_type == 'liquor' else 'till',
            payment_status='pending',
            status='pending',  # Ready for processing once payment is confirmed by admin
            estimated_delivery=timezone.now() + timezone.timedelta(minutes=30)
        )

        # Create order items
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                food_item=cart_item.food_item,
                quantity=cart_item.quantity,
                price_at_order=cart_item.food_item.price
            )

        # Create status history
        OrderStatusHistory.objects.create(
            order=order,
            status='pending',
            notes='Order placed - Awaiting manual payment confirmation'
        )

        # DON'T clear cart yet - will clear after payment confirmation
        # DON'T update times_ordered yet - will update after payment confirmation

        return JsonResponse({
            'success': True,
            'message': 'Order placed successfully! Please complete payment using the TILL number provided.',
            'order_number': order.order_number,
            'payment_method': 'manual',
            'estimated_delivery': order.estimated_delivery.strftime('%I:%M %p'),
            'awaiting_payment': True
        })

    # Cash on delivery logic stays the same...
    else:
        order = Order.objects.create(
            order_number=order_number,
            user=request.user,
            hostel=hostel,
            room_number=room_number,
            phone_number=phone_number,
            delivery_notes=delivery_notes,
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            total=total,
            payment_method=payment_method,
            store_type=store_type,
            payment_type='paybill' if store_type == 'liquor' else 'till',
            payment_status='pending',
            estimated_delivery=timezone.now() + timezone.timedelta(minutes=30)
        )

        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                food_item=cart_item.food_item,
                quantity=cart_item.quantity,
                price_at_order=cart_item.food_item.price
            )
            cart_item.food_item.times_ordered += cart_item.quantity
            cart_item.food_item.save()

        OrderStatusHistory.objects.create(
            order=order,
            status='pending',
            notes='Order placed - Cash on delivery'
        )

        cart.items.all().delete()

        request.user.loyalty_points += int(total)
        request.user.save()

        send_customer_order_confirmation(order)
        send_admin_order_notification(order)

        return JsonResponse({
            'success': True,
            'message': 'Order placed successfully!',
            'order_number': order.order_number,
            'payment_method': 'cash',
            'estimated_delivery': order.estimated_delivery.strftime('%I:%M %p')
        })
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

@crsf_exempt
@require_http_methods(["POST"])
def mpesa_callback(request):
    """Handle M-PESA payment callback"""
    try:
        callback_data = json.loads(request.body)
        
        print("====== MPESA CALLBACK ======")
        print(json.dumps(callback_data, indent=2))
        print("============================")

        # Extract callback data
        stk_callback = callback_data.get('Body', {}).get('stkCallback', {})
        result_code = stk_callback.get('ResultCode')
        checkout_request_id = stk_callback.get('CheckoutRequestID')
        result_desc = stk_callback.get('ResultDesc', '')

        # Find the order
        try:
            order = Order.objects.get(mpesa_checkout_request_id=checkout_request_id)
        except Order.DoesNotExist:
            print(f"Order not found for CheckoutRequestID: {checkout_request_id}")
            return HttpResponse("OK")

        # Payment successful
        if result_code == 0:
            # Extract payment details
            callback_metadata = stk_callback.get('CallbackMetadata', {}).get('Item', [])
            mpesa_receipt_number = None
            phone_number = None
            amount = None
            transaction_date = None
            
            for item in callback_metadata:
                name = item.get('Name')
                if name == 'MpesaReceiptNumber':
                    mpesa_receipt_number = item.get('Value')
                elif name == 'PhoneNumber':
                    phone_number = item.get('Value')
                elif name == 'Amount':
                    amount = item.get('Value')
                elif name == 'TransactionDate':
                    transaction_date = item.get('Value')

            # Update order
            order.payment_status = 'completed'
            order.status = 'pending'  # Now ready for processing
            order.mpesa_receipt_number = mpesa_receipt_number
            order.mpesa_transaction_date = str(transaction_date) if transaction_date else None
            order.payment_completed_at = timezone.now()
            order.save()

            # Update food item popularity
            for order_item in order.items.all():
                order_item.food_item.times_ordered += order_item.quantity
                order_item.food_item.save()

            # Clear user's cart
            try:
                cart = Cart.objects.get(user=order.user)
                cart.items.all().delete()
            except Cart.DoesNotExist:
                pass

            # Award loyalty points
            order.user.loyalty_points += int(order.total)
            order.user.save()

            # Create status history with more details
            OrderStatusHistory.objects.create(
                order=order,
                status='pending',
                notes=f'Payment confirmed. M-PESA Receipt: {mpesa_receipt_number}. Amount: KES {amount}. Phone: {phone_number}'
            )

            print(f"Order {order.order_number} payment confirmed - Receipt: {mpesa_receipt_number}, Phone: {phone_number}")

        # Payment failed or cancelled
        else:
            order.payment_status = 'failed'
            order.status = 'cancelled'
            order.payment_failure_reason = result_desc
            order.save()

            OrderStatusHistory.objects.create(
                order=order,
                status='cancelled',
                notes=f'Payment failed: {result_desc}'
            )

            print(f"Order {order.order_number} payment failed: {result_desc}")

        return HttpResponse("OK")

    except Exception as e:
        print(f"Error in M-PESA callback: {str(e)}")
        import traceback
        traceback.print_exc()
        return HttpResponse("OK")
    
@require_http_methods(["POST"])
def mpesa_stk_query(request):
    """Query MPESA STK push status"""
    data = json.loads(request.body)
    checkout_request_id = data.get('checkout_request_id')

    if not checkout_request_id:
        return JsonResponse({'success': False, 'message': 'CheckoutRequestID required'})

    from .mpesa_utils import mpesa
    result = mpesa.query_stk_status(checkout_request_id)

    if result['success']:
        # Update order status based on query result
        try:
            order = Order.objects.get(mpesa_checkout_request_id=checkout_request_id)

            if result.get('result_code') == 0:
                # Payment successful
                order.payment_status = 'completed'
                order.status = 'preparing'
                order.save()

                OrderStatusHistory.objects.create(
                    order=order,
                    status='preparing',
                    notes='Payment confirmed via STK query'
                )

                # Award loyalty points
                order.user.loyalty_points += int(order.total)
                order.user.save()

            elif result.get('result_code') == 1:
                # Payment failed
                order.payment_status = 'failed'
                order.save()

                OrderStatusHistory.objects.create(
                    order=order,
                    status='pending',
                    notes=f'Payment failed: {result.get("result_desc", "Unknown error")}'
                )

        except Order.DoesNotExist:
            pass

    return JsonResponse(result)

# views.py
@login_required
def check_order_payment_status(request, order_number):
    """Check order payment status"""
    try:
        order = Order.objects.get(order_number=order_number, user=request.user)
        
        return JsonResponse({
            'success': True,
            'payment_status': order.payment_status,
            'order_status': order.status,
            'mpesa_receipt_number': order.mpesa_receipt_number
#         })
        })
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Order not found'}, status=404)
#             'mpesa_receipt_number': order.mpesa_receipt_number


