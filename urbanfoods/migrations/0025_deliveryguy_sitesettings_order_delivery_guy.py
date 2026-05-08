# Generated migration for DeliveryGuy, SiteSettings, and Order.delivery_guy

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('urbanfoods', '0024_order_review_prompt_dismissed_at_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='DeliveryGuy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('phone_number', models.CharField(max_length=15)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name_plural': 'Delivery Guys',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='SiteSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('delivery_fee', models.DecimalField(decimal_places=2, default=50, help_text='Delivery fee in KES', max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name_plural': 'Site Settings',
            },
        ),
        migrations.AddField(
            model_name='order',
            name='delivery_guy',
            field=models.ForeignKey(blank=True, help_text='Assign a delivery person to this order', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='orders', to='urbanfoods.deliveryguy'),
        ),
    ]
