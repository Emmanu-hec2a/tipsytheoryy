# from django.core.management.base import BaseCommand
# from django.contrib.auth import get_user_model
# from django.utils import timezone
# from decimal import Decimal
# from django.conf import settings

# from urbanfoods.models import Order, OrderItem, FoodItem
# from urbanfoods.utils import notify_new_order, notify_low_stock, send_telegram_message

# User = get_user_model()


# class Command(BaseCommand):
#     help = "Create a test liquor order and trigger notify_new_order()"

#     def handle(self, *args, **options):
#         self.stdout.write(self.style.WARNING("Creating test order..."))

#         # 1. Create or get test user
#         user, created = User.objects.get_or_create(
#             username="testcustomer",
#             defaults={
#                 "email": "testcustomer@example.com",
#                 "first_name": "Test",
#                 "last_name": "Customer",
#             }
#         )

#         if created:
#             self.stdout.write(self.style.SUCCESS("Test user created"))
#         else:
#             self.stdout.write("Using existing test user")

#         # 2. Get a liquor item
#         item = FoodItem.objects.filter(store_type="liquor").first()

#         if not item:
#             self.stdout.write(self.style.ERROR(
#                 "No liquor FoodItem found. Create one first."
#             ))
#             return

#         # 3. Create order
#         order = Order.objects.create(
#             user=user,
#             phone_number="0718258821",
#             hostel="Honolulu",
#             room_number="112",
#             delivery_notes="TEST ORDER – PLEASE IGNORE",
#             subtotal=Decimal("1000.00"),
#             delivery_fee=Decimal("20.00"),
#             total=Decimal("1020.00"),
#             store_type="liquor",
#             status="pending",
#             estimated_delivery=timezone.now() + timezone.timedelta(minutes=15)
#         )

#         # 4. Create order item
#         OrderItem.objects.create(
#             order=order,
#             food_item=item,
#             quantity=2,
#             price_at_order=item.price
#         )

#         self.stdout.write(self.style.SUCCESS(
#             f"Order {order.order_number} created"
#         ))

#         # 5. Trigger notification
#         success = notify_new_order(order)

#         if success:
#             self.stdout.write(self.style.SUCCESS(
#                 "notify_new_order() executed successfully"
#             ))
#         else:
#             self.stdout.write(self.style.ERROR(
#                 "notify_new_order() failed"
#             ))

#     help = "Send Telegram low stock alert for liquor products"

#     def add_arguments(self, parser):
#         parser.add_argument(
#             '--id',
#             type=int,
#             help='Test low stock alert for a specific FoodItem ID'
#         )

#     def handle(self, *args, **options):
#         item_id = options.get('id', 3)

#         if item_id:
#             try:
#                 item = FoodItem.objects.get(id=item_id)
#             except FoodItem.DoesNotExist:
#                 self.stdout.write(self.style.ERROR(f"❌ FoodItem with ID {item_id} not found"))
#                 return

#             self.stdout.write(self.style.WARNING(f"Testing low stock alert for: {item.name} (Stock: {item.stock})"))
#             notify_low_stock(item)
#             self.stdout.write(self.style.SUCCESS("✅ Telegram notification sent (if stock ≤ threshold)"))
#             return

#         # Bulk test for all liquor items below threshold
#         low_stock_items = FoodItem.objects.filter(
#             store_type='liquor',
#             stock__lte=5
#         )

#         if not low_stock_items.exists():
#             self.stdout.write(self.style.WARNING("⚠️ No liquor items are currently low on stock"))
#             return

#         for item in low_stock_items:
#             notify_low_stock(item)
#             self.stdout.write(self.style.SUCCESS(f"✅ Alert sent for {item.name} (Stock: {item.stock})"))

#         self.stdout.write(self.style.SUCCESS("🎉 Low stock test completed"))
