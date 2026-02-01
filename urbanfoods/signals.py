from django.db.models.signals import pre_save
from django.dispatch import receiver
from PIL import Image
import requests
from io import BytesIO
from .models import Product  # Change to your model

@receiver(pre_save, sender=Product)
def optimize_image_on_save(sender, instance, **kwargs):
    """
    Automatically optimize image URL when product is saved
    Works for Cloudinary URLs stored as text
    """
    if instance.image_url and 'cloudinary.com' in instance.image_url:
        # Check if already optimized
        if '/upload/c_fill' not in instance.image_url:
            # Add Cloudinary transformations to existing URL
            instance.image_url = instance.image_url.replace(
                '/upload/',
                '/upload/c_fill,w_800,h_800,q_auto:good,f_auto/'
            )
            print(f"Auto-optimized image for: {instance.name}")