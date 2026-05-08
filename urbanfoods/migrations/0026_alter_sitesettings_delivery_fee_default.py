# Generated manually to align the SiteSettings default delivery fee with the storefront.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('urbanfoods', '0025_deliveryguy_sitesettings_order_delivery_guy'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sitesettings',
            name='delivery_fee',
            field=models.DecimalField(
                decimal_places=2,
                default=20,
                help_text='Delivery fee in KES',
                max_digits=10,
            ),
        ),
    ]
