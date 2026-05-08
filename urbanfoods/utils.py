# utils.py
import json
from pywebpush import webpush
from .models import PushSubscription

VAPID_PRIVATE_KEY = "MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgfWfJbjUWsfxd1GxLRwsiVoMo/T5nbZTZKKpa1WUnNA+hRANCAAT9nGX9yf5vW6dwFkKkn6s8rTsIGKiHBwSrGubbo98BtVVfrkwkSMp3v1S9koIv6JigRJ9vLRYFU0b5Zzk3mfdB"
VAPID_CLAIMS = {"sub": "mailto:petniqueke@gmail.com"}

def send_push_to_all(title, body, url="/"):
    subscriptions = PushSubscription.objects.all()
    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": sub.keys
                },
                data=json.dumps({"title": title, "body": body, "url": url}),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims=VAPID_CLAIMS
            )
        except Exception as e:
            print("Push failed for subscription:", sub.endpoint, e)

# utils.py
import requests
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

def format_phone(phone):
    phone = phone.replace(" ", "")
    if phone.startswith("0"):
        phone = "+254" + phone[1:]
    return phone


def _send_telegram_message_single(message, buttons=None):
    try:
        bot_token = getattr(settings, 'TELEGRAM_BOTT_TOKEN', None)
        chat_id = getattr(settings, 'TELEGRAM_CHATT_ID', None)

        if not bot_token or not chat_id:
            logger.warning("Telegram credentials not configured")
            return False

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True
        }

        if buttons:
            payload['reply_markup'] = json.dumps({
                "inline_keyboard": buttons
            })

        response = requests.post(url, data=payload, timeout=10)

        if response.status_code == 200:
            logger.info("✅ Telegram message sent")
            return True
        else:
            logger.error(f"❌ Telegram failed: {response.text}")
            return False

    except Exception as e:
        logger.error(f"❌ Telegram error: {e}")
        return False

def send_telegram_message(message, buttons=None):
    try:
        bot_token = getattr(settings, 'TELEGRAM_BOTT_TOKEN', None)
        chat_ids = getattr(settings, 'TELEGRAM_CHATT_IDS', None)
        if not chat_ids:
            chat_ids = getattr(settings, 'TELEGRAM_CHATT_ID', None)

        if isinstance(chat_ids, str):
            chat_ids = [chat_id.strip() for chat_id in chat_ids.split(',') if chat_id.strip()]

        if not bot_token or not chat_ids:
            logger.warning("Telegram credentials not configured")
            return False

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

        base_payload = {
            'text': message,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True
        }

        if buttons:
            base_payload['reply_markup'] = json.dumps({
                "inline_keyboard": buttons
            })

        sent_count = 0
        for chat_id in chat_ids:
            payload = {
                **base_payload,
                'chat_id': chat_id,
            }

            response = requests.post(url, data=payload, timeout=10)

            if response.status_code == 200:
                sent_count += 1
                logger.info(f"Telegram message sent to {chat_id}")
            else:
                logger.error(f"Telegram failed for {chat_id}: {response.text}")

        return sent_count > 0

    except Exception as e:
        logger.error(f"Telegram error: {e}")
        return False


def notify_new_order(order):
    try:
        items_list = []
        for item in order.items.all():
            line_total = item.price_at_order * item.quantity
            items_list.append(
                f"  • {item.food_item.name} x{item.quantity} — KES {line_total}"
            )

        items_text = "\n".join(items_list) if items_list else "  No items"
        customer_name = order.user.username if order.user else "N/A"

        message = f"""
🆕 <b>NEW ORDER RECEIVED!</b>

📦 <b>Order #{order.order_number}</b>
━━━━━━━━━━━━━━━━━━━━
👤 <b>Customer:</b> {customer_name}
📱 <b>Phone:</b> {order.phone_number or 'N/A'}
🏠 <b>Location:</b> {order.hostel or 'N/A'}
🚪 <b>Room:</b> {order.room_number or 'N/A'}

📝 <b>Items:</b>
{items_text}

💵 <b>TOTAL:</b> KES {order.total}
⏰ {timezone.localtime(order.created_at).strftime('%I:%M %p, %d %b %Y')}

━━━━━━━━━━━━━━━━━━━━
🔔 Awaiting payment confirmation
        """.strip()

        # ✅ Admin order link
        admin_url = f"{settings.SITE_URL}/admin-panel/liquor/orders/{order.order_number}/"

        # ✅ Phone dialer link (works on Telegram mobile)
        phone_number = phone_number = format_phone(order.phone_number) if order.phone_number else ""
        phone_url = f"tel:{phone_number}" if phone_number else None

        # ✅ Inline buttons
        buttons = [
            [
                {"text": "View in Admin", "url": admin_url}
            ]
        ]

        formatted_phone = format_phone(order.phone_number) if order.phone_number else "N/A"
        # Optional WhatsApp button
        if order.phone_number:
            wa_url = f"https://wa.me/{formatted_phone.replace('+','')}"
            buttons.append([
                {"text": "WhatsApp Customer", "url": wa_url}
            ])

        return send_telegram_message(message, buttons=buttons)

    except Exception as e:
        logger.error(f"Error creating order notification: {e}")
        return False


def notify_payment_received(order):
    customer_name = order.user.username if order.user else "N/A"

    message = f"""
✅ <b>PAYMENT CONFIRMED</b>

📦 Order #{order.order_number}
👤 {customer_name}
💰 KES {order.total}

Status: Ready for delivery 🚀
    """.strip()

    return send_telegram_message(message)


def notify_order_delivered(order):
    customer_name = order.user.username if order.user else "N/A"

    message = f"""
🎉 <b>ORDER DELIVERED</b>

📦 Order #{order.order_number}
👤 {customer_name}
💰 KES {order.total}

Status: Completed ✅
    """.strip()

    return send_telegram_message(message)

def notify_low_stock(product):
    """Send Telegram alert for a single low stock product"""
    threshold = getattr(product, 'low_stock_threshold', 2)
    message = f"""
⚠️ <b>LOW STOCK ALERT</b>

🍾 <b>{product.name}</b>
📦 Remaining Stock: <b>{product.stock}</b>
🏷️ Threshold: {threshold}
🏷 Category: {product.category.name}

Restock soon!
    """.strip()

    admin_url = f"{settings.SITE_URL}/admin-panel/liquor/menu/"

    buttons = [[{"text": "Restock", "url": admin_url}]]

    return send_telegram_message(message, buttons=buttons)


def check_and_notify_low_stock():
    """
    Check all products for low stock and send Telegram alerts.
    This function checks products where stock < low_stock_threshold (default 2).
    Should be called periodically or after order processing.
    """
    from .models import FoodItem
    from django.db import models
    
    # Get all products with stock below their threshold
    low_stock_products = FoodItem.objects.filter(
        stock__gt=0  # Only check products that have stock (ignore out of stock)
    ).filter(
        stock__lt=models.F('low_stock_threshold')
    )
    
    if not low_stock_products.exists():
        logger.info("No low stock products found")
        return False
    
    alert_count = 0
    for product in low_stock_products:
        try:
            notify_low_stock(product)
            alert_count += 1
        except Exception as e:
            logger.error(f"Failed to send low stock alert for {product.name}: {e}")
    
    if alert_count > 0:
        logger.info(f"✅ Sent {alert_count} low stock alerts")
    
    return alert_count > 0

