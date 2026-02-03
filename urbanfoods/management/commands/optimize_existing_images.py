from django.core.management.base import BaseCommand
from urbanfoods.models import FoodItem
from PIL import Image
import os

class Command(BaseCommand):
    help = 'Optimize existing images IN-PLACE without changing paths'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be optimized without actually doing it',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No files will be modified\n'))
        
        items = FoodItem.objects.exclude(image='')
        total = items.count()
        
        self.stdout.write(f'Found {total} products with images\n')
        
        optimized = 0
        skipped = 0
        errors = 0
        total_saved = 0
        
        for item in items:
            if not item.image:
                continue
            
            try:
                # Get the actual file path
                image_path = item.image.path
                
                # Check if file exists
                if not os.path.exists(image_path):
                    self.stdout.write(self.style.WARNING(f'⚠️  File not found: {item.name}'))
                    skipped += 1
                    continue
                
                # Get original size
                original_size = os.path.getsize(image_path)
                
                # Skip if already small (likely already optimized)
                if original_size < 250000:  # 250 KB
                    self.stdout.write(f'⏭️  Already optimized: {item.name} ({original_size/1024:.1f} KB)')
                    skipped += 1
                    continue
                
                self.stdout.write(f'\n📦 Processing: {item.name}')
                self.stdout.write(f'   Original: {original_size/1024:.1f} KB')
                self.stdout.write(f'   Path: {image_path}')
                
                if not dry_run:
                    # Open image
                    img = Image.open(image_path)
                    
                    # Convert to RGB if needed
                    if img.mode in ("RGBA", "LA", "P"):
                        background = Image.new("RGB", img.size, (255, 255, 255))
                        if img.mode in ("RGBA", "LA"):
                            background.paste(img, mask=img.split()[-1])
                        else:
                            background.paste(img)
                        img = background
                    
                    # Resize if too large
                    max_size = (800, 800)
                    if img.width > max_size[0] or img.height > max_size[1]:
                        img.thumbnail(max_size, Image.Resampling.LANCZOS)
                    
                    # Create temporary file
                    temp_path = image_path + '.tmp'
                    
                    # Save optimized version to temp file
                    img.save(
                        temp_path,
                        format='JPEG',
                        quality=85,
                        optimize=True,
                        progressive=True
                    )
                    
                    # Get new size
                    new_size = os.path.getsize(temp_path)
                    
                    # Replace original with optimized (SAME PATH!)
                    os.replace(temp_path, image_path)
                    
                    saved = original_size - new_size
                    total_saved += saved
                    
                    self.stdout.write(self.style.SUCCESS(
                        f'   ✅ Optimized: {new_size/1024:.1f} KB (saved {saved/1024:.1f} KB, -{(saved/original_size)*100:.1f}%)'
                    ))
                    optimized += 1
                else:
                    self.stdout.write(self.style.WARNING('   (Would optimize in real mode)'))
                
            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(f'   ❌ Error: {str(e)}'))
        
        # Summary
        self.stdout.write('\n' + '='*60)
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN SUMMARY:'))
        else:
            self.stdout.write(self.style.SUCCESS('OPTIMIZATION COMPLETE!'))
        self.stdout.write(f'Total products: {total}')
        self.stdout.write(self.style.SUCCESS(f'✅ Optimized: {optimized}'))
        self.stdout.write(f'⏭️  Skipped: {skipped}')
        if errors > 0:
            self.stdout.write(self.style.ERROR(f'❌ Errors: {errors}'))
        if not dry_run and total_saved > 0:
            self.stdout.write(self.style.SUCCESS(f'💾 Total saved: {total_saved/1024/1024:.2f} MB'))
        self.stdout.write('='*60)