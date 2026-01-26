from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.hashers import check_password
from django.http import JsonResponse
from django.db.models.functions import ExtractHour, TruncDate
from django.db.models import Count, Sum, Avg, Max
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from datetime import timedelta
from .utils import send_push_to_all
from .models import *
import json

def staff_member_required(view_func=None, login_url='admin_login'):
    actual_decorator = user_passes_test(
        lambda u: u.is_active and u.is_staff,
        login_url=login_url
    )
    if view_func:
        return actual_decorator(view_func)
    return actual_decorator

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.http import JsonResponse
import json

def admin_login(request):
    """Admin login page with AJAX support"""
    # If staff user is already logged in
    if request.user.is_authenticated and request.user.is_staff:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # AJAX request: return JSON
            return JsonResponse({
                'success': True,
                'redirect': '/admin-panel/liquor/'
            })
        # Normal request: redirect
        return redirect('/admin-panel/liquor/')

    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON'}, status=400)

        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return JsonResponse({'success': False, 'message': 'Username and password are required'}, status=400)

        user = authenticate(username=username, password=password)

        if user is not None and user.is_staff:
            login(request, user)
            return JsonResponse({
                'success': True,
                'message': 'Admin login successful!',
                'redirect': '/admin-panel/liquor/'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Invalid admin credentials or insufficient permissions'
            }, status=401)

    # For non-AJAX GET requests, render the login page
    return render(request, 'custom_admin/login.html')


# ==================== ADMIN DASHBOARD ====================

@staff_member_required(login_url='admin_login')
def admin_dashboard(request):
    """Main admin dashboard with overview"""
    # Check if this is an AJAX request for data refresh
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        today = timezone.now().date()

        # Today's statistics
        today_orders = Order.objects.filter(created_at__date=today)
        today_revenue = today_orders.aggregate(total=Sum('total'))['total'] or 0
        pending_orders = Order.objects.filter(status='pending').count()
        out_for_delivery = Order.objects.filter(status='out_for_delivery').count()

        # This week's stats for revenue trend
        week_start = today - timedelta(days=today.weekday())
        weekly_orders = Order.objects.filter(created_at__date__gte=week_start)
        revenue_trend = weekly_orders.annotate(day=TruncDate('created_at')).values('day').annotate(
            revenue=Sum('total'),
            orders=Count('id')
        ).order_by('day')

        return JsonResponse({
            'success': True,
            'today_orders_count': today_orders.count(),
            'today_revenue': today_revenue,
            'pending_orders': pending_orders,
            'out_for_delivery': out_for_delivery,
            'daily_revenue': list(revenue_trend)
        })

    # Regular page load
    today = timezone.now().date()

    # Today's statistics
    today_orders = Order.objects.filter(created_at__date=today)
    today_revenue = today_orders.aggregate(total=Sum('total'))['total'] or 0
    pending_orders = Order.objects.filter(status='pending').count()
    preparing_orders = Order.objects.filter(status='preparing').count()
    out_for_delivery = Order.objects.filter(status='out_for_delivery').count()

    # Popular items today
    popular_today = OrderItem.objects.filter(
        order__created_at__date=today
    ).values(
        'food_item__name'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('price_at_order')
    ).order_by('-total_quantity')[:5]

    # This week's stats
    week_start = today - timedelta(days=today.weekday())
    weekly_orders = Order.objects.filter(created_at__date__gte=week_start)
    weekly_revenue = weekly_orders.aggregate(total=Sum('total'))['total'] or 0
    weekly_order_count = weekly_orders.count()
    average_order_value = weekly_revenue / weekly_order_count if weekly_order_count > 0 else 0
    revenue_trend = weekly_orders.annotate(day=TruncDate('created_at')).values('day').annotate(
        daily_revenue=Sum('total'),
        order_count=Count('id')
    ).order_by('day')

    # Peak hours (last 7 days)
    peak_hours = Order.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=7)
    ).annotate(hour=ExtractHour('created_at')).values('hour').annotate(
        order_count=Count('id')
    ).order_by('-order_count')[:5]

    context = {
        'today_orders_count': today_orders.count(),
        'today_revenue': today_revenue,
        'pending_orders': pending_orders,
        'preparing_orders': preparing_orders,
        'out_for_delivery': out_for_delivery,
        'popular_today': popular_today,
        'weekly_orders': weekly_orders.count(),
        'weekly_revenue': weekly_revenue,
        'average_order_value': average_order_value,
        'peak_hours': peak_hours,
        'revenue_trend': list(revenue_trend),
    }

    return render(request, 'custom_admin/liquor_dashboard.html', context)

@staff_member_required(login_url='admin_login')
def admin_dashboard_stats(request):
    """API endpoint to provide dashboard stats for refresh"""
    if request.method == 'GET':
        today = timezone.now().date()

        # Today's statistics
        today_orders = Order.objects.filter(created_at__date=today)
        today_revenue = today_orders.aggregate(total=Sum('total'))['total'] or 0
        pending_orders = Order.objects.filter(status='pending').count()
        out_for_delivery = Order.objects.filter(status='out_for_delivery').count()

        # This week's stats for revenue trend
        week_start = today - timedelta(days=today.weekday())
        weekly_orders = Order.objects.filter(created_at__date__gte=week_start)
        revenue_trend = (
            weekly_orders
            .annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(
                revenue=Sum('total'),
                orders=Count('id')
            )
            .order_by('day')
        )

        # Convert queryset into JSON-safe format
        trend_data = [
            {
                "day": str(item["day"]),               # date → string
                "revenue": float(item["revenue"] or 0),# decimal → float
                "orders": item["orders"]
            }
            for item in revenue_trend
        ]

        return JsonResponse({
            'success': True,
            'today_orders_count': today_orders.count(),
            'today_revenue': float(today_revenue or 0),
            'pending_orders': pending_orders,
            'out_for_delivery': out_for_delivery,
            'daily_revenue': trend_data
        }, safe=False)

    return JsonResponse({'success': False, 'message': 'Invalid request'})

# ==================== ORDER MANAGEMENT ====================

@staff_member_required(login_url='admin_login')
def admin_orders(request):
    """Order management page"""
    status_filter = request.GET.get('status', 'all')
    payment_method_filter = request.GET.get('payment_method', 'all')
    payment_status_filter = request.GET.get('payment_status', 'all')

    orders = Order.objects.all().select_related('user').prefetch_related('items')

    if status_filter != 'all':
        orders = orders.filter(status=status_filter)

    if payment_method_filter != 'all':
        orders = orders.filter(payment_method=payment_method_filter)

    if payment_status_filter != 'all':
        orders = orders.filter(payment_status=payment_status_filter)

    # Recent orders first
    orders = orders.order_by('-created_at')

    context = {
        'orders': orders[:50],  # Limit to recent 50
        'status_filter': status_filter,
        'payment_method_filter': payment_method_filter,
        'payment_status_filter': payment_status_filter,
    }

    return render(request, 'custom_admin/liquor_orders.html', context)

@staff_member_required(login_url='admin_login')
def get_new_orders(request):
    """API endpoint to check for new orders (for auto-refresh)"""
    last_check = request.GET.get('last_check')

    if last_check:
        last_check_time = parse_datetime(last_check)
        if last_check_time is not None and timezone.is_naive(last_check_time):
            last_check_time = timezone.make_aware(last_check_time, timezone.get_current_timezone())

        new_orders = Order.objects.filter(
            created_at__gt=last_check_time,
            status='pending'
        ) if last_check_time else Order.objects.filter(status='pending')
    else:
        new_orders = Order.objects.filter(status='pending')

    orders_data = []
    for order in new_orders:
        orders_data.append({
            'order_number': order.order_number,
            'user': order.user.username,
            'total': float(order.total),
            'hostel': order.hostel,
            'room': order.room_number,
            'phone': order.phone_number,
            'created_at': order.created_at.isoformat(),
        })

        # Send push for each new order
        send_push_to_all(
            title="New Order Received 🍔",
            body=f"Order #{order.order_number} by {order.user.username} for KES {order.total}",
            url=f"/admin-panel/liquor/orders/{order.id}/"  # optional admin link
        )

    return JsonResponse({
        'success': True,
        'new_orders_count': len(orders_data),
        'orders': orders_data,
        'timestamp': timezone.now().isoformat()
    })

@staff_member_required(login_url='admin_login')
def admin_order_detail(request, order_number):
    """View detailed order information"""
    order = get_object_or_404(Order.objects.select_related('user'), order_number=order_number)
    status_history = order.status_history.all()

    context = {
        'order': order,
        'status_history': status_history,
    }

    return render(request, 'custom_admin/order_detail.html', context)

@staff_member_required(login_url='admin_login')
def update_order_status(request):
    """Update order status"""
    if request.method == 'POST':
        data = json.loads(request.body)
        order_number = data.get('order_number')
        new_status = data.get('status')
        notes = data.get('notes', '')

        order = get_object_or_404(Order, order_number=order_number)

        # Update status
        old_status = order.status
        order.status = new_status

        # Set delivered timestamp and reduce stock
        if new_status == 'delivered' and old_status != 'delivered':
            order.delivered_at = timezone.now()

            # Reduce stock for liquor items
            for item in order.items.filter(food_item__store_type='liquor'):
                category = item.food_item.category
                if category.stock_quantity >= item.quantity:
                    category.stock_quantity -= item.quantity
                    category.save()
                else:
                    # Insufficient stock - this shouldn't happen in normal flow
                    # but handle gracefully
                    pass

        order.save()

        # Create status history entry
        OrderStatusHistory.objects.create(
            order=order,
            status=new_status,
            notes=notes or f'Status changed from {old_status} to {new_status}'
        )

        return JsonResponse({
            'success': True,
            'message': f'Order {order_number} status updated to {new_status}',
            'new_status': new_status,
            'status_display': order.get_status_display()
        })

    return JsonResponse({'success': False, 'message': 'Invalid request'})

@staff_member_required(login_url='admin_login')
def cancel_order(request):
    """Cancel an order"""
    if request.method == 'POST':
        data = json.loads(request.body)
        order_number = data.get('order_number')
        reason = data.get('reason', 'Cancelled by admin')

        order = get_object_or_404(Order, order_number=order_number)
        order.status = 'cancelled'
        order.cancellation_reason = reason
        order.save()

        # Create status history entry
        OrderStatusHistory.objects.create(
            order=order,
            status='cancelled',
            notes=reason
        )

        return JsonResponse({
            'success': True,
            'message': f'Order {order_number} cancelled'
        })

    return JsonResponse({'success': False, 'message': 'Invalid request'})

@staff_member_required(login_url='admin_login')
def get_payment_details(request, order_number):
    """Get payment details for an order"""
    order = get_object_or_404(Order, order_number=order_number)

    if order.payment_method != 'mpesa':
        return JsonResponse({'success': False, 'message': 'Payment details only available for M-PESA payments'})

    payment_details = {
        'mpesa_receipt_number': order.mpesa_receipt_number,
        'transaction_date': order.created_at.isoformat() if order.created_at else None,
        'phone_number': order.phone_number,
        'checkout_request_id': order.mpesa_checkout_request_id,
        'payment_completed_at': order.payment_completed_at.isoformat() if order.payment_completed_at else None,
    }

    return JsonResponse({
        'success': True,
        'payment_details': payment_details
    })

# ==================== LIQUOR ADMIN VIEWS ====================

@staff_member_required(login_url='admin_login')
def liquor_dashboard(request):
    """Liquor store admin dashboard"""
    # Check if this is an AJAX request for data refresh
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        today = timezone.now().date()

        # Today's liquor statistics
        today_orders = Order.objects.filter(
            created_at__date=today,
            items__food_item__store_type='liquor'
        ).distinct()
        today_revenue = OrderItem.objects.filter(
            order__created_at__date=today,
            food_item__store_type='liquor'
        ).aggregate(total=Sum('price_at_order'))['total'] or 0
        pending_orders = Order.objects.filter(
            status='pending',
            items__food_item__store_type='liquor'
        ).distinct().count()
        out_for_delivery = Order.objects.filter(
            status='out_for_delivery',
            items__food_item__store_type='liquor'
        ).distinct().count()

        # This week's liquor stats for revenue trend
        week_start = today - timedelta(days=today.weekday())
        weekly_orders = Order.objects.filter(
            created_at__date__gte=week_start,
            items__food_item__store_type='liquor'
        ).distinct()
        revenue_trend = OrderItem.objects.filter(
            order__created_at__date__gte=week_start,
            food_item__store_type='liquor'
        ).annotate(day=TruncDate('order__created_at')).values('day').annotate(
            revenue=Sum('price_at_order'),
            orders=Count('order', distinct=True)
        ).order_by('day')

        return JsonResponse({
            'success': True,
            'today_orders_count': today_orders.count(),
            'today_revenue': float(today_revenue),
            'pending_orders': pending_orders,
            'out_for_delivery': out_for_delivery,
            'daily_revenue': list(revenue_trend)
        })

    # Regular page load
    today = timezone.now().date()

    # Today's liquor statistics
    today_orders = Order.objects.filter(
        created_at__date=today,
        items__food_item__store_type='liquor'
    ).distinct()
    today_revenue = OrderItem.objects.filter(
        order__created_at__date=today,
        food_item__store_type='liquor'
    ).aggregate(total=Sum('price_at_order'))['total'] or 0
    pending_orders = Order.objects.filter(
        status='pending',
        items__food_item__store_type='liquor'
    ).distinct().count()
    preparing_orders = Order.objects.filter(
        status='preparing',
        items__food_item__store_type='liquor'
    ).distinct().count()
    out_for_delivery = Order.objects.filter(
        status='out_for_delivery',
        items__food_item__store_type='liquor'
    ).distinct().count()

    # Popular liquor items today
    popular_today = OrderItem.objects.filter(
        order__created_at__date=today,
        food_item__store_type='liquor'
    ).values(
        'food_item__name'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('price_at_order')
    ).order_by('-total_quantity')[:5]

    # This week's liquor stats
    week_start = today - timedelta(days=today.weekday())
    weekly_orders = Order.objects.filter(
        created_at__date__gte=week_start,
        items__food_item__store_type='liquor'
    ).distinct()
    weekly_revenue = OrderItem.objects.filter(
        order__created_at__date__gte=week_start,
        food_item__store_type='liquor'
    ).aggregate(total=Sum('price_at_order'))['total'] or 0
    weekly_order_count = weekly_orders.count()
    average_order_value = weekly_revenue / weekly_order_count if weekly_order_count > 0 else 0
    revenue_trend = OrderItem.objects.filter(
        order__created_at__date__gte=week_start,
        food_item__store_type='liquor'
    ).annotate(day=TruncDate('order__created_at')).values('day').annotate(
        daily_revenue=Sum('price_at_order'),
        order_count=Count('order', distinct=True)
    ).order_by('day')

    # Peak hours (last 7 days) for liquor orders
    peak_hours = Order.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=7),
        items__food_item__store_type='liquor'
    ).distinct().annotate(hour=ExtractHour('created_at')).values('hour').annotate(
        order_count=Count('id')
    ).order_by('-order_count')[:5]

    context = {
        'today_orders_count': today_orders.count(),
        'today_revenue': today_revenue,
        'pending_orders': pending_orders,
        'preparing_orders': preparing_orders,
        'out_for_delivery': out_for_delivery,
        'popular_today': popular_today,
        'weekly_orders': weekly_orders.count(),
        'weekly_revenue': weekly_revenue,
        'average_order_value': average_order_value,
        'peak_hours': peak_hours,
        'revenue_trend': list(revenue_trend),
        'store_type': 'liquor',
    }

    return render(request, 'custom_admin/liquor_dashboard.html', context)

@staff_member_required(login_url='admin_login')
def liquor_orders(request):
    """Liquor order management page"""
    status_filter = request.GET.get('status', 'all')

    orders = Order.objects.filter(
        items__food_item__store_type='liquor'
    ).distinct().select_related('user').prefetch_related('items')

    if status_filter != 'all':
        orders = orders.filter(status=status_filter)

    # Recent orders first
    orders = orders.order_by('-created_at')

    context = {
        'orders': orders[:50],  # Limit to recent 50
        'status_filter': status_filter,
        'store_type': 'liquor',
    }

    return render(request, 'custom_admin/liquor_orders.html', context)

@staff_member_required(login_url='admin_login')
def liquor_analytics(request):
    """Liquor analytics and reports"""
    # Date range
    days = int(request.GET.get('days', 7))
    start_date = timezone.now() - timedelta(days=days)

    # Liquor revenue over time
    daily_revenue = OrderItem.objects.filter(
        order__created_at__gte=start_date,
        food_item__store_type='liquor',
        order__status='delivered'
    ).annotate(day=TruncDate('order__created_at')).values('day').annotate(
        revenue=Sum('price_at_order'),
        orders=Count('order', distinct=True)
    ).order_by('day')

    # Top selling liquor items
    top_items = OrderItem.objects.filter(
        order__created_at__gte=start_date,
        food_item__store_type='liquor'
    ).values(
        'food_item__name',
        'food_item__category__name',
        'food_item__bottle_size'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('price_at_order')
    ).order_by('-total_quantity')[:10]

    # Top liquor customers
    top_customers = Order.objects.filter(
        created_at__gte=start_date,
        status='delivered',
        items__food_item__store_type='liquor'
    ).distinct().values(
        'user__username',
        'user__phone_number'
    ).annotate(
        total_orders=Count('id'),
        total_spent=Sum('total')
    ).order_by('-total_orders')[:10]

    # Liquor order status distribution
    status_distribution = Order.objects.filter(
        created_at__gte=start_date,
        items__food_item__store_type='liquor'
    ).distinct().values('status').annotate(
        count=Count('id')
    )

    # Calculate totals
    total_revenue = sum(float(item['revenue'] or 0) for item in daily_revenue)
    total_orders = sum(item['orders'] for item in daily_revenue)
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0

    # Peak hours for liquor orders
    peak_hours = Order.objects.filter(
        created_at__gte=start_date,
        items__food_item__store_type='liquor'
    ).distinct().annotate(hour=ExtractHour('created_at')).values('hour').annotate(
        order_count=Count('id')
    ).order_by('-order_count')[:10]

    # Liquor-specific metrics
    liquor_orders = Order.objects.filter(
        created_at__gte=start_date,
        items__food_item__store_type='liquor'
    ).distinct()

    liquor_revenue = OrderItem.objects.filter(
        order__created_at__gte=start_date,
        food_item__store_type='liquor'
    ).aggregate(total=Sum('price_at_order'))['total'] or 0

    liquor_items_sold = OrderItem.objects.filter(
        order__created_at__gte=start_date,
        food_item__store_type='liquor'
    ).aggregate(total=Sum('quantity'))['total'] or 0

    # Top selling liquor items (already calculated above)
    top_liquor_items = top_items

    # Liquor revenue trend (already calculated above)
    liquor_daily_revenue = daily_revenue

    context = {
        'daily_revenue': json.dumps(list(daily_revenue), default=str),
        'top_items': json.dumps(list(top_items), default=str),
        'top_customers': json.dumps(list(top_customers), default=str),
        'status_distribution': json.dumps(list(status_distribution), default=str),
        'days': days,
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'avg_order_value': avg_order_value,
        'peak_hours': json.dumps(list(peak_hours), default=str),
        # Liquor metrics
        'liquor_revenue': liquor_revenue,
        'liquor_orders_count': liquor_orders.count(),
        'liquor_items_sold': liquor_items_sold,
        'top_liquor_items': json.dumps(list(top_liquor_items), default=str),
        'liquor_daily_revenue': json.dumps(list(liquor_daily_revenue), default=str),
        'store_type': 'liquor',
    }

    return render(request, 'custom_admin/liquor_analytics.html', context)

# ==================== FOOD MENU MANAGEMENT ====================

@staff_member_required(login_url='admin_login')
def admin_menu(request):
    """Food menu management"""
    categories = FoodCategory.objects.filter(store_type='food')
    food_items = FoodItem.objects.filter(store_type='food').select_related('category')

    context = {
        'categories': categories,
        'food_items': food_items,
        'store_type': 'food',
    }

    return render(request, 'custom_admin/menu.html', context)

@staff_member_required(login_url='admin_login')
def admin_liquor(request):
    """Liquor store management"""
    categories = FoodCategory.objects.filter(store_type='liquor')
    food_items = FoodItem.objects.filter(store_type='liquor').select_related('category')

    context = {
        'categories': categories,
        'food_items': food_items,
        'store_type': 'liquor',
    }

    return render(request, 'custom_admin/liquor.html', context)

@staff_member_required(login_url='admin_login')
def admin_grocery(request):
    """Grocery store management"""
    categories = FoodCategory.objects.filter(store_type='grocery')
    food_items = FoodItem.objects.filter(store_type='grocery').select_related('category')

    context = {
        'categories': categories,
        'food_items': food_items,
        'store_type': 'grocery',
    }

    return render(request, 'custom_admin/grocery.html', context)

@staff_member_required(login_url='admin_login')
def toggle_food_availability(request):
    """Toggle food item availability"""
    if request.method == 'POST':
        data = json.loads(request.body)
        food_item_id = data.get('food_item_id')

        food_item = get_object_or_404(FoodItem, id=food_item_id)
        food_item.is_available = not food_item.is_available
        food_item.save()

        return JsonResponse({
            'success': True,
            'is_available': food_item.is_available,
            'message': f'{food_item.name} is now {"available" if food_item.is_available else "unavailable"}'
        })

    return JsonResponse({'success': False, 'message': 'Invalid request'})

@staff_member_required(login_url='admin_login')
def update_food_price(request):
    """Update food item price"""
    if request.method == 'POST':
        data = json.loads(request.body)
        food_item_id = data.get('food_item_id')
        new_price = data.get('price')

        food_item = get_object_or_404(FoodItem, id=food_item_id)
        food_item.price = new_price
        food_item.save()

        return JsonResponse({
            'success': True,
            'message': f'{food_item.name} price updated to KES {new_price}'
        })

    return JsonResponse({'success': False, 'message': 'Invalid request'})

@staff_member_required(login_url='admin_login')
def add_category(request):
    """Add a new food category"""
    if request.method == 'POST':
        data = json.loads(request.body)
        name = data.get('name')
        description = data.get('description', '')
        order = data.get('order', 0)
        stock_quantity = data.get('stock_quantity', 0)

        if not name:
            return JsonResponse({'success': False, 'message': 'Category name is required'})

        store_type = data.get('store_type', 'food')
        category = FoodCategory.objects.create(
            name=name,
            description=description,
            order=order,
            stock_quantity=stock_quantity,
            store_type=store_type
        )

        return JsonResponse({
            'success': True,
            'message': f'Category "{name}" added successfully',
            'category_id': category.id
        })

    return JsonResponse({'success': False, 'message': 'Invalid request'})

@staff_member_required(login_url='admin_login')
def edit_category(request):
    """Edit an existing food category"""
    if request.method == 'POST':
        data = json.loads(request.body)
        category_id = data.get('id')
        name = data.get('name')
        description = data.get('description', '')
        order = data.get('order', 0)
        stock_quantity = data.get('stock_quantity', 0)

        if not category_id or not name:
            return JsonResponse({'success': False, 'message': 'Category ID and name are required'})

        category = get_object_or_404(FoodCategory, id=category_id)
        category.name = name
        category.description = description
        category.order = order
        category.stock_quantity = stock_quantity
        category.save()

        return JsonResponse({
            'success': True,
            'message': f'Category "{name}" updated successfully'
        })

    return JsonResponse({'success': False, 'message': 'Invalid request'})

@staff_member_required(login_url='admin_login')
def delete_category(request):
    """Delete a food category"""
    if request.method == 'POST':
        data = json.loads(request.body)
        category_id = data.get('id')

        if not category_id:
            return JsonResponse({'success': False, 'message': 'Category ID is required'})

        category = get_object_or_404(FoodCategory, id=category_id)

        # Check if category has food items
        if category.fooditem_set.exists():
            return JsonResponse({
                'success': False,
                'message': 'Cannot delete category with existing food items. Please move or delete the items first.'
            })

        category_name = category.name
        category.delete()

        return JsonResponse({
            'success': True,
            'message': f'Category "{category_name}" deleted successfully'
        })

    return JsonResponse({'success': False, 'message': 'Invalid request'})

@staff_member_required(login_url='admin_login')
def add_food_item(request):
    """Add a new food item"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        category_id = request.POST.get('category')
        price = request.POST.get('price')
        prep_time = request.POST.get('prep_time')
        image = request.FILES.get('image')

        if not all([name, description, category_id, price, prep_time]):
            return JsonResponse({'success': False, 'message': 'All fields are required'})

        try:
            category = FoodCategory.objects.get(id=category_id)
        except FoodCategory.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Invalid category'})

        bottle_size = request.POST.get('bottle_size', '')
        store_type = request.POST.get('store_type', 'food')
        
        food_item = FoodItem.objects.create(
            name=name,
            description=description,
            category=category,
            price=price,
            prep_time=prep_time,
            image=image,
            bottle_size=bottle_size,
            store_type=store_type
        )

        return JsonResponse({
            'success': True,
            'message': f'Food item "{name}" added successfully',
            'item_id': food_item.id
        })

    return JsonResponse({'success': False, 'message': 'Invalid request'})

@staff_member_required(login_url='admin_login')
def edit_food_item(request):
    """Edit an existing food item"""
    if request.method == 'POST':
        item_id = request.POST.get('id')
        name = request.POST.get('name')
        description = request.POST.get('description')
        category_id = request.POST.get('category')
        price = request.POST.get('price')
        prep_time = request.POST.get('prep_time')
        image = request.FILES.get('image')

        if not item_id or not all([name, description, category_id, price, prep_time]):
            return JsonResponse({'success': False, 'message': 'All fields are required'})

        try:
            food_item = FoodItem.objects.get(id=item_id)
            category = FoodCategory.objects.get(id=category_id)
        except (FoodItem.DoesNotExist, FoodCategory.DoesNotExist):
            return JsonResponse({'success': False, 'message': 'Invalid food item or category'})

        food_item.name = name
        food_item.description = description
        food_item.category = category
        food_item.price = price
        food_item.prep_time = prep_time
        bottle_size = request.POST.get('bottle_size', '')
        if bottle_size:
            food_item.bottle_size = bottle_size
        if image:
            food_item.image = image
        food_item.save()

        return JsonResponse({
            'success': True,
            'message': f'Food item "{name}" updated successfully'
        })

    return JsonResponse({'success': False, 'message': 'Invalid request'})

@staff_member_required(login_url='admin_login')
def delete_food_item(request):
    """Delete a food item"""
    if request.method == 'POST':
        data = json.loads(request.body)
        item_id = data.get('id')

        if not item_id:
            return JsonResponse({'success': False, 'message': 'Food item ID is required'})

        food_item = get_object_or_404(FoodItem, id=item_id)
        item_name = food_item.name
        food_item.delete()

        return JsonResponse({
            'success': True,
            'message': f'Food item "{item_name}" deleted successfully'
        })

    return JsonResponse({'success': False, 'message': 'Invalid request'})

# ==================== ANALYTICS ====================

@staff_member_required(login_url='admin_login')
def admin_analytics(request):
    """Analytics and reports"""
    # Date range
    days = int(request.GET.get('days', 7))
    start_date = timezone.now() - timedelta(days=days)

    # Revenue over time
    daily_revenue = Order.objects.filter(
        created_at__gte=start_date,
        status='delivered'
    ).extra(
        select={'day': 'DATE(created_at)'}
    ).values('day').annotate(
        revenue=Sum('total'),
        orders=Count('id')
    ).order_by('day')

    # Top selling items (food and grocery only)
    top_items = OrderItem.objects.filter(
        order__created_at__gte=start_date,
        food_item__store_type__in=['food', 'grocery']
    ).values(
        'food_item__name',
        'food_item__category__name'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('price_at_order')
    ).order_by('-total_quantity')[:10]

    # Top customers
    top_customers = Order.objects.filter(
        created_at__gte=start_date,
        status='delivered'
    ).values(
        'user__username',
        'user__phone_number'
    ).annotate(
        total_orders=Count('id'),
        total_spent=Sum('total')
    ).order_by('-total_orders')[:10]

    # Order status distribution
    status_distribution = Order.objects.filter(
        created_at__gte=start_date
    ).values('status').annotate(
        count=Count('id')
    )

    # Calculate totals
    total_revenue = sum(item['revenue'] for item in daily_revenue)
    total_orders = sum(item['orders'] for item in daily_revenue)
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0

    # Peak hours
    peak_hours = (Order.objects.filter(created_at__gte=start_date).annotate(hour=ExtractHour('created_at')).values('hour').annotate(order_count=Count('id')).order_by('-order_count')[:10])

    # M-PESA Payment Analytics
    mpesa_orders = Order.objects.filter(
        created_at__gte=start_date,
        payment_method='mpesa'
    )

    # M-PESA revenue and success rate
    mpesa_revenue = mpesa_orders.filter(payment_status='completed').aggregate(total=Sum('total'))['total'] or 0
    mpesa_success_rate = (mpesa_orders.filter(payment_status='completed').count() / mpesa_orders.count() * 100) if mpesa_orders.count() > 0 else 0
    mpesa_avg_transaction = mpesa_revenue / mpesa_orders.filter(payment_status='completed').count() if mpesa_orders.filter(payment_status='completed').count() > 0 else 0

    # M-PESA payment timeline
    mpesa_payment_timeline = mpesa_orders.filter(payment_status='completed').annotate(day=TruncDate('payment_completed_at')).values('day').annotate(
        successful_payments=Count('id'),
        revenue=Sum('total')
    ).order_by('day')

    # Failed payment reasons
    failed_payments = mpesa_orders.filter(payment_status='failed').values('payment_failure_reason').annotate(
        count=Count('id')
    ).order_by('-count')[:5]

    # Peak payment hours
    peak_payment_hours = mpesa_orders.filter(payment_status='completed').annotate(hour=ExtractHour('payment_completed_at')).values('hour').annotate(
        payment_count=Count('id')
    ).order_by('-payment_count')[:10]

    # Liquor-specific metrics
    liquor_orders = Order.objects.filter(
        created_at__gte=start_date,
        items__food_item__store_type='liquor'
    ).distinct()

    liquor_revenue = OrderItem.objects.filter(
        order__created_at__gte=start_date,
        food_item__store_type='liquor'
    ).aggregate(total=Sum('price_at_order'))['total'] or 0

    liquor_items_sold = OrderItem.objects.filter(
        order__created_at__gte=start_date,
        food_item__store_type='liquor'
    ).aggregate(total=Sum('quantity'))['total'] or 0

    # Top selling liquor items
    top_liquor_items = OrderItem.objects.filter(
        order__created_at__gte=start_date,
        food_item__store_type='liquor'
    ).values(
        'food_item__name',
        'food_item__category__name',
        'food_item__bottle_size'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('price_at_order')
    ).order_by('-total_quantity')[:10]

    # Liquor revenue trend
    liquor_daily_revenue = (
    OrderItem.objects.filter(
        order__created_at__gte=start_date,
        food_item__store_type='liquor'
    )
    .annotate(day=TruncDate('order__created_at'))
    .values('day')
    .annotate(
        revenue=Sum('price_at_order'),
        orders=Count('order', distinct=True)
    )
    .order_by('day')
    )

    context = {
        'daily_revenue': json.dumps(list(daily_revenue), default=str),
        'top_items': json.dumps(list(top_items), default=str),
        'top_customers': json.dumps(list(top_customers), default=str),
        'status_distribution': json.dumps(list(status_distribution), default=str),
        'days': days,
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'avg_order_value': avg_order_value,
        'peak_hours': json.dumps(list(peak_hours), default=str),
        # M-PESA Payment metrics
        'mpesa_revenue': mpesa_revenue,
        'mpesa_success_rate': mpesa_success_rate,
        'mpesa_avg_transaction': mpesa_avg_transaction,
        'mpesa_payment_timeline': json.dumps(list(mpesa_payment_timeline), default=str),
        'failed_payments': json.dumps(list(failed_payments), default=str),
        'peak_payment_hours': json.dumps(list(peak_payment_hours), default=str),
        # Liquor metrics
        'liquor_revenue': liquor_revenue,
        'liquor_orders_count': liquor_orders.count(),
        'liquor_items_sold': liquor_items_sold,
        'top_liquor_items': json.dumps(list(top_liquor_items), default=str),
        'liquor_daily_revenue': json.dumps(list(liquor_daily_revenue), default=str),
    }

    return render(request, 'custom_admin/analytics.html', context)

# ==================== CUSTOMER MANAGEMENT ====================

@staff_member_required(login_url='admin_login')
def admin_customers(request):
    """Customer management"""
    customers = User.objects.filter(is_staff=False).annotate(
        total_orders=Count('orders'),
        total_spent=Sum('orders__total')
    ).order_by('-total_orders')

    total_customers = customers.count()
    avg_orders_per_customer = customers.aggregate(avg_orders=Avg('total_orders'))['avg_orders'] or 0

    context = {
        'customers': customers,
        'total_customers': total_customers,
        'active_customers': customers.filter(total_orders__gt=0).count(),
        'new_customers': customers.filter(date_joined__gte=timezone.now()-timedelta(days=30)).count(),
        'avg_orders_per_customer': avg_orders_per_customer,
    }

    return render(request, 'custom_admin/customers.html', context)

@staff_member_required(login_url='admin_login')
def admin_customer_detail(request, customer_id):
    customer = get_object_or_404(User, id=customer_id)
    # Fetch orders for the customer
    orders = Order.objects.filter(user=customer).order_by('-created_at')

    context = {
        'customer': customer,
        'orders': orders,
    }
    return render(request, 'custom_admin/customer_detail.html', context)

@staff_member_required(login_url='admin_login')
def get_customer_orders(request, customer_id):
    """API endpoint to get customer orders"""
    customer = get_object_or_404(User, id=customer_id)
    orders = Order.objects.filter(user=customer).order_by('-created_at')[:10]  # Limit to recent 10

    orders_data = []
    for order in orders:
        orders_data.append({
            'order_number': order.order_number,
            'created_at': order.created_at.isoformat(),
            'total': float(order.total),
            'status': order.status,
            'status_display': order.get_status_display(),
            'items': [
                {
                    'quantity': item.quantity,
                    'food_item': {
                        'name': item.food_item.name
                    }
                } for item in order.items.all()
            ]
        })

    return JsonResponse({
        'success': True,
        'orders': orders_data
    })

@staff_member_required(login_url='admin_login')
def send_customer_message(request):
    """Send message to customer"""
    if request.method == 'POST':
        data = json.loads(request.body)
        customer_id = data.get('customer_id')
        subject = data.get('subject')
        content = data.get('content')

        customer = get_object_or_404(User, id=customer_id)

        # Here you would implement actual message sending logic
        # For now, we'll just return success
        # You could integrate with email service, SMS, or in-app notifications

        return JsonResponse({
            'success': True,
            'message': f'Message sent to {customer.username}'
        })

    return JsonResponse({'success': False, 'message': 'Invalid request'})

@staff_member_required(login_url='admin_login')
def update_customer_status(request):
    """Update customer active status"""
    if request.method == 'POST':
        data = json.loads(request.body)
        customer_id = data.get('customer_id')
        is_active = data.get('is_active')

        customer = get_object_or_404(User, id=customer_id)
        customer.is_active = is_active
        customer.save()

        return JsonResponse({
            'success': True,
            'message': f'Customer {customer.username} {"activated" if is_active else "deactivated"} successfully'
        })

    return JsonResponse({'success': False, 'message': 'Invalid request'})

@staff_member_required(login_url='admin_login')
def admin_profile(request):
    """Admin profile page"""
    return render(request, 'custom_admin/profile.html')

@staff_member_required(login_url='admin_login')
def update_admin_profile(request):
    """Update admin profile information"""
    if request.method == 'POST':
        data = json.loads(request.body)
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()

        if not username or not email:
            return JsonResponse({
                'success': False,
                'message': 'Username and email are required'
            })

        # Check if username is already taken by another user
        user = request.user
        if User.objects.filter(username=username).exclude(id=user.id).exists():
            return JsonResponse({
                'success': False,
                'message': 'Username already taken'
            })

        # Update the admin user
        user.username = username
        user.email = email
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        user.save()

        return JsonResponse({
            'success': True,
            'message': 'Profile updated successfully'
        })

    return JsonResponse({'success': False, 'message': 'Invalid request'})

@staff_member_required(login_url='admin_login')
def update_admin_password(request):
    """Update admin password"""
    if request.method == 'POST':
        data = json.loads(request.body)
        old_password = data.get('old_password')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')

        if not old_password or not new_password or not confirm_password:
            return JsonResponse({
                'success': False,
                'message': 'All password fields are required'
            })

        if new_password != confirm_password:
            return JsonResponse({
                'success': False,
                'message': 'New passwords do not match'
            })

        if len(new_password) < 8:
            return JsonResponse({
                'success': False,
                'message': 'Password must be at least 8 characters long'
            })

        # Verify old password
        user = request.user
        if not user.check_password(old_password):
            return JsonResponse({
                'success': False,
                'message': 'Current password is incorrect'
            })

        # Set new password
        user.set_password(new_password)
        user.save()

        return JsonResponse({
            'success': True,
            'message': 'Password updated successfully'
        })

    return JsonResponse({'success': False, 'message': 'Invalid request'})
