from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import FoodItem

class StaticViewSitemap(Sitemap):
    priority = 1.0
    changefreq = "daily"

    def items(self):
        return ["homepage"]

    def location(self, item):
        return reverse(item)


class FoodItemSitemap(Sitemap):
    priority = 0.8
    changefreq = "weekly"

    def items(self):
        return FoodItem.objects.filter(is_available=True)

    def location(self, obj):
        return "/"  # homepage until you add slugs
