# urbanfoods/notifications.py
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

local_time = timezone.localtime(timezone.now())

def send_admin_order_notification(order):
    """Send email notification to admin when a new order is received"""
    subject = f'🔔 New Order: {order.order_number}'
    
    # Get order items
    items_list = "\n".join([
        f"  - {item.food_item.name} x{item.quantity} @ KES {item.price_at_order}"
        for item in order.items.all()
    ])
    
    # Plain text version
    message = f'''
New Order Received!

Order Details:
--------------
Order Number: {order.order_number}
Store Type: {order.store_type.upper()}
Status: {order.status.upper()}

Customer Information:
--------------------
Name: {order.user.get_full_name() or order.user.username}
Email: {order.user.email}
Phone: {order.phone_number}

Delivery Details:
----------------
Hostel: {order.hostel}
Room Number: {order.room_number}
Delivery Notes: {order.delivery_notes or 'None'}

Order Summary:
-------------
{items_list}

Subtotal: KES {order.subtotal}
Delivery Fee: KES {order.delivery_fee}
Total Amount: KES {order.total}

Payment:
--------
Payment Method: {order.payment_method.upper()}
Payment Type: {order.payment_type.upper()}
Payment Status: {order.payment_status.upper()}

Estimated Delivery: {order.estimated_delivery.strftime('%I:%M %p')}

View order details at:
https://tipsytheoryy.com/admin-panel/orders/

---
TipsyTheoryy Admin System
    '''
    
    # HTML version
    items_html = "".join([
        f'''
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.1); color: #e5e7eb;">{item.food_item.name}</td>
            <td style="padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.1); text-align: center; color: #e5e7eb;">{item.quantity}</td>
            <td style="padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.1); text-align: right; color: #e5e7eb;">KES {item.price_at_order}</td>
            <td style="padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.1); text-align: right; font-weight: bold; color: #fbbf24;">KES {item.quantity * item.price_at_order}</td>
        </tr>
        '''
        for item in order.items.all()
    ])

    html_message = f'''
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                margin: 0;
                padding: 0;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #e5e7eb;
            }}
            .glassmorphism {{
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                border: 1px solid rgba(255, 255, 255, 0.2);
                box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
                border-radius: 16px;
            }}
            .gradient-header {{
                background: linear-gradient(135deg, #ea580c, #dc2626);
                border-radius: 16px 16px 0 0;
            }}
            .modern-table {{
                border-collapse: collapse;
                width: 100%;
                margin: 20px 0;
                border-radius: 12px;
                overflow: hidden;
            }}
            .modern-table th {{
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                padding: 15px;
                text-align: left;
                font-weight: 600;
                color: #fbbf24;
                border-bottom: 1px solid rgba(255, 255, 255, 0.2);
            }}
            .modern-btn {{
                display: inline-block;
                padding: 15px 30px;
                background: linear-gradient(135deg, #ea580c, #dc2626);
                color: white;
                text-decoration: none;
                border-radius: 12px;
                font-weight: 600;
                font-size: 16px;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(234, 88, 12, 0.4);
            }}
            .modern-btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(234, 88, 12, 0.6);
            }}
            .info-card {{
                background: rgba(255, 255, 255, 0.05);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 20px;
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>
        <div style="max-width: 700px; margin: 20px auto; padding: 20px;">
            <div class="glassmorphism">
                <div class="gradient-header" style="padding: 30px; text-align: center;">
                    <h1 style="color: white; margin: 0; font-size: 28px; font-weight: 700;">🔔 New Order Alert!</h1>
                    <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0; font-size: 16px;">Fresh order just came in</p>
                </div>

                <div style="padding: 30px;">
                    <div class="info-card">
                        <h2 style="color: #fbbf24; margin: 0 0 15px 0; font-size: 22px;">Order #{order.order_number}</h2>
                        <div style="display: flex; gap: 20px; flex-wrap: wrap;">
                            <div><strong style="color: #e5e7eb;">Store:</strong> <span style="color: #60a5fa;">{order.store_type.upper()}</span></div>
                            <div><strong style="color: #e5e7eb;">Status:</strong> <span style="color: #fbbf24; font-weight: bold;">{order.status.upper()}</span></div>
                        </div>
                    </div>

                    <h3 style="color: #60a5fa; margin: 30px 0 15px 0; font-size: 18px; border-bottom: 2px solid #60a5fa; padding-bottom: 8px;">👤 Customer Details</h3>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                        <div><strong style="color: #e5e7eb;">Name:</strong><br>{order.user.get_full_name() or order.user.username}</div>
                        <div><strong style="color: #e5e7eb;">Email:</strong><br>{order.user.email}</div>
                        <div><strong style="color: #e5e7eb;">Phone:</strong><br>{order.phone_number}</div>
                        <div><strong style="color: #e5e7eb;">Hostel:</strong><br>{order.hostel}</div>
                    </div>

                    <h3 style="color: #60a5fa; margin: 30px 0 15px 0; font-size: 18px; border-bottom: 2px solid #60a5fa; padding-bottom: 8px;">📍 Delivery Info</h3>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                        <div><strong style="color: #e5e7eb;">Room:</strong><br>{order.room_number}</div>
                        <div><strong style="color: #e5e7eb;">Notes:</strong><br>{order.delivery_notes or 'None'}</div>
                        <div><strong style="color: #e5e7eb;">ETA:</strong><br><span style="color: #34d399; font-weight: bold;">15 mins</span></div>
                        <div><strong style="color: #e5e7eb;">Payment:</strong><br><span style="color: #fbbf24;">{order.payment_method.upper()}</span></div>
                    </div>

                    <h3 style="color: #60a5fa; margin: 30px 0 15px 0; font-size: 18px; border-bottom: 2px solid #60a5fa; padding-bottom: 8px;">🛒 Order Items</h3>
                    <table class="modern-table">
                        <thead>
                            <tr>
                                <th>Item</th>
                                <th style="text-align: center;">Qty</th>
                                <th style="text-align: right;">Price</th>
                                <th style="text-align: right;">Total</th>
                            </tr>
                        </thead>
                        <tbody>
                            {items_html}
                            <tr style="background: rgba(255,255,255,0.05);">
                                <td colspan="3" style="padding: 15px; text-align: right; font-weight: bold; color: #e5e7eb;">Subtotal:</td>
                                <td style="padding: 15px; text-align: right; font-weight: bold; color: #fbbf24;">KES {order.subtotal}</td>
                            </tr>
                            <tr style="background: rgba(255,255,255,0.05);">
                                <td colspan="3" style="padding: 15px; text-align: right; color: #e5e7eb;">Delivery Fee:</td>
                                <td style="padding: 15px; text-align: right; color: #e5e7eb;">KES {order.delivery_fee}</td>
                            </tr>
                            <tr style="background: linear-gradient(135deg, #ea580c, #dc2626); color: white;">
                                <td colspan="3" style="padding: 18px; text-align: right; font-size: 18px; font-weight: bold;">TOTAL:</td>
                                <td style="padding: 18px; text-align: right; font-size: 18px; font-weight: bold;">KES {order.total}</td>
                            </tr>
                        </tbody>
                    </table>

                    <div style="text-align: center; margin: 40px 0;">
                        <a href="https://tipsytheoryy.com/admin-panel/orders/" class="modern-btn">
                            📊 View All Orders →
                        </a>
                    </div>

                    <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.2);">
                        <p style="color: rgba(255,255,255,0.7); font-size: 12px; margin: 0;">
                            Tipsy Theoryy Admin System<br>
                            Sent {timezone.localtime(timezone.now()).strftime('%B %d, %Y at %I:%M %p')}
                        </p>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [settings.ADMIN_NOTIFICATION_EMAIL],
            fail_silently=False,
            html_message=html_message,
        )
        return True
    except Exception as e:
        print(f"Failed to send admin notification email: {e}")
        return False


def send_customer_order_confirmation(order):
    """Send order confirmation email to customer"""
    subject = f'Order Confirmation - {order.order_number}'
    
    # Get order items
    items_list = "\n".join([
        f"  - {item.food_item.name} x{item.quantity} @ KES {item.price_at_order}"
        for item in order.items.all()
    ])
    
    payment_instructions = ""
    if order.payment_method == 'cash':
        if order.store_type == 'liquor':
            payment_instructions = f'''
Payment Instructions:
--------------------
Please complete payment using M-PESA Paybill:
Business Number: 8330098 - NETWIX
Account Number: {order.order_number}
Amount: KES {order.total}

Your order will be processed once payment is confirmed.
please ignore this if already paid.
'''
        else:
            payment_instructions = f'''
Payment Instructions:
--------------------
Please complete payment using M-PESA Till Number:
Till Number: 6960814 - MOSES ONKUNDI ATINDA
Amount: KES {order.total}

Your order will be processed once payment is confirmed.
please ignore this if already paid.
'''
    
    # Plain text version
    message = f'''
Thank you for your order!

Hi {order.user.get_full_name() or order.user.username},

Your order has been received and is being processed.

Order Details:
--------------
Order Number: {order.order_number}
Order Date: {timezone.localtime(order.created_at).strftime('%B %d, %Y at %I:%M %p')}

Payment Method: {order.payment_method.upper()}

Delivery Information:
--------------------
Hostel: {order.hostel}
Room Number: {order.room_number}
Phone: {order.phone_number}
Estimated Delivery: {
    timezone.localtime(order.estimated_delivery).strftime('%I:%M %p')
    if order.estimated_delivery else '15 mins'
}

Order Summary:
-------------
{items_list}

Subtotal: KES {order.subtotal}
Delivery Fee: KES {order.delivery_fee}
Total Amount: KES {order.total}
Estimated Delivery: {
    timezone.localtime(order.estimated_delivery).strftime('%I:%M %p')
    if order.estimated_delivery else '15 mins'
}

{payment_instructions}

You can track your order status at:
https://tipsytheoryy/orders/

If you have any questions, please contact us | Call 0110345054.

Thank you for choosing Tipsy Theoryy!

---
Tipsy Theoryy
    '''
    
    # HTML version
    items_html = "".join([
        f'''
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.1); color: #e5e7eb;">{item.food_item.name}</td>
            <td style="padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.1); text-align: center; color: #e5e7eb;">{item.quantity}</td>
            <td style="padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.1); text-align: right; color: #e5e7eb;">KES {item.price_at_order}</td>
            <td style="padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.1); text-align: right; font-weight: bold; color: #fbbf24;">KES {item.quantity * item.price_at_order}</td>
        </tr>
        '''
        for item in order.items.all()
    ])

    payment_html = ""
    if order.payment_method == 'cash':
        payment_type = "Paybill" if order.store_type == 'liquor' else "Till Number"
        payment_number = "8330098 - NETWIX" if order.store_type == 'liquor' else "6960814 - MOSES ONKUNDI ATINDA"
        account_info = f'<p style="margin: 5px 0; color: #e5e7eb;"><strong>Account Number:</strong> {order.order_number}</p>' if order.store_type == 'liquor' else ""
        payment_html = f'''
        <div class="info-card" style="background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 20px; margin: 20px 0;">
            <h3 style="color: #fbbf24; margin: 0 0 15px 0; font-size: 18px;">💳 Payment Required</h3>
            <p style="margin: 10px 0; color: #e5e7eb;"><strong>Please complete payment using M-PESA {payment_type}:</strong></p>
            <p style="margin: 5px 0; font-size: 1.2em; color: #60a5fa; font-weight: bold;">{payment_number}</p>
            {account_info}
            <p style="margin: 5px 0; color: #e5e7eb;"><strong>Amount:</strong> <span style="color: #34d399; font-size: 1.3em; font-weight: bold;">KES {order.total}</span></p>
            <p style="margin: 10px 0 0 0; font-size: 0.9em; color: rgba(255,255,255,0.7);">Your order will be processed once payment is confirmed by our team.</p>
        </div>
        '''

    html_message = f'''
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                margin: 0;
                padding: 0;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #e5e7eb;
            }}
            .glassmorphism {{
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                border: 1px solid rgba(255, 255, 255, 0.2);
                box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
                border-radius: 16px;
            }}
            .gradient-header {{
                background: linear-gradient(135deg, #ea580c, #dc2626);
                border-radius: 16px 16px 0 0;
            }}
            .modern-table {{
                border-collapse: collapse;
                width: 100%;
                margin: 20px 0;
                border-radius: 12px;
                overflow: hidden;
            }}
            .modern-table th {{
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                padding: 15px;
                text-align: left;
                font-weight: 600;
                color: #fbbf24;
                border-bottom: 1px solid rgba(255, 255, 255, 0.2);
            }}
            .modern-btn {{
                display: inline-block;
                padding: 15px 30px;
                background: linear-gradient(135deg, #ea580c, #dc2626);
                color: white;
                text-decoration: none;
                border-radius: 12px;
                font-weight: 600;
                font-size: 16px;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(234, 88, 12, 0.4);
            }}
            .modern-btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(234, 88, 12, 0.6);
            }}
            .info-card {{
                background: rgba(255, 255, 255, 0.05);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 20px;
                margin: 20px 0;
            }}
            .help-card {{
                background: rgba(59, 130, 246, 0.1);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(59, 130, 246, 0.2);
                border-radius: 12px;
                padding: 20px;
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>
        <div style="max-width: 700px; margin: 20px auto; padding: 20px;">
            <div class="glassmorphism">
                <div class="gradient-header" style="padding: 30px; text-align: center;">
                    <h1 style="color: white; margin: 0; font-size: 28px; font-weight: 700;">🎉 Order Confirmed!</h1>
                    <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0; font-size: 16px;">Thank you for choosing Tipsy Theoryy</p>
                </div>

                <div style="padding: 30px;">
                    <p style="font-size: 18px; margin: 0 0 20px 0; color: #e5e7eb;">Hi <strong style="color: #fbbf24;">{order.user.get_full_name() or order.user.username}</strong>,</p>
                    <p style="color: rgba(255,255,255,0.8); margin: 0 0 30px 0; line-height: 1.6;">Your order has been received and is being processed. Here are your order details:</p>

                    <div class="info-card">
                        <h2 style="color: #fbbf24; margin: 0 0 15px 0; font-size: 22px;">Order #{order.order_number}</h2>
                        <div style="display: flex; gap: 20px; flex-wrap: wrap;">
                            <div><strong style="color: #e5e7eb;">Date:</strong> <span style="color: #60a5fa;">{timezone.localtime(order.created_at).strftime('%B %d, %Y')}</span></div>
                            <div><strong style="color: #e5e7eb;">Time:</strong> <span style="color: #60a5fa;">{timezone.localtime(order.created_at).strftime('%I:%M %p')}</span></div>
                            <div><strong style="color: #e5e7eb;">Status:</strong> <span style="color: #fbbf24; font-weight: bold;">{order.status.upper()}</span></div>
                        </div>
                    </div>

                    <h3 style="color: #60a5fa; margin: 30px 0 15px 0; font-size: 18px; border-bottom: 2px solid #60a5fa; padding-bottom: 8px;">📍 Delivery Details</h3>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                        <div><strong style="color: #e5e7eb;">Hostel:</strong><br>{order.hostel}</div>
                        <div><strong style="color: #e5e7eb;">Room:</strong><br>{order.room_number}</div>
                        <div><strong style="color: #e5e7eb;">Phone:</strong><br>{order.phone_number}</div>
                        <div><strong style="color: #e5e7eb;">ETA:</strong><br><span style="color: #34d399; font-weight: bold;">15 mins</span></div>
                    </div>

                    <h3 style="color: #60a5fa; margin: 30px 0 15px 0; font-size: 18px; border-bottom: 2px solid #60a5fa; padding-bottom: 8px;">🛒 Order Items</h3>
                    <table class="modern-table">
                        <thead>
                            <tr>
                                <th>Item</th>
                                <th style="text-align: center;">Qty</th>
                                <th style="text-align: right;">Price</th>
                                <th style="text-align: right;">Total</th>
                            </tr>
                        </thead>
                        <tbody>
                            {items_html}
                            <tr style="background: rgba(255,255,255,0.05);">
                                <td colspan="3" style="padding: 15px; text-align: right; font-weight: bold; color: #e5e7eb;">Subtotal:</td>
                                <td style="padding: 15px; text-align: right; font-weight: bold; color: #fbbf24;">KES {order.subtotal}</td>
                            </tr>
                            <tr style="background: rgba(255,255,255,0.05);">
                                <td colspan="3" style="padding: 15px; text-align: right; color: #e5e7eb;">Delivery Fee:</td>
                                <td style="padding: 15px; text-align: right; color: #e5e7eb;">KES {order.delivery_fee}</td>
                            </tr>
                            <tr style="background: linear-gradient(135deg, #ea580c, #dc2626); color: white;">
                                <td colspan="3" style="padding: 18px; text-align: right; font-size: 18px; font-weight: bold;">TOTAL:</td>
                                <td style="padding: 18px; text-align: right; font-size: 18px; font-weight: bold;">KES {order.total}</td>
                            </tr>
                        </tbody>
                    </table>

                    <div style="margin: 20px 0; color: #e5e7eb;"><strong>Payment Method:</strong> <span style="color: #fbbf24;">{order.payment_method.upper()}</span></div>

                    {payment_html}

                    <div style="text-align: center; margin: 40px 0;">
                        <a href="https://tipsytheoryy.com/orders/" class="modern-btn">
                            📍 Track Your Order →
                        </a>
                    </div>

                    <div class="help-card">
                        <p style="margin: 0; color: #60a5fa; font-weight: 600; font-size: 16px;">💡 Need Help?</p>
                        <p style="margin: 8px 0 0 0; color: rgba(255,255,255,0.8);">If you have any questions about your order, please contact our support team. | Call 0110345054</p>
                    </div>

                    <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.2);">
                        <p style="color: rgba(255,255,255,0.7); font-size: 12px; margin: 0;">
                            Thank you for choosing Urban Dreams Cafe!<br>
                            This email was sent to {order.user.email}<br>
                            Sent {timezone.localtime(timezone.now()).strftime('%B %d, %Y at %I:%M %p')}
                        </p>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [order.user.email],
            fail_silently=False,
            html_message=html_message,
        )
        return True
    except Exception as e:
        print(f"Failed to send customer confirmation email: {e}")
        return False