import os
from PIL import Image
from django.conf import settings
from pathlib import Path
from uuid import uuid4

def get_file_path(instance, filename, folder):
    """
    Generate a unique file path for uploaded files.
    Args:
        instance: Model instance the file is attached to
        filename: Original filename
        folder: Target subfolder in media directory
    Returns:
        Path string for the file
    """
    ext = filename.split('.')[-1]
    filename = f"{uuid4().hex}.{ext}"
    return os.path.join(folder, filename)

def get_product_image_path(instance, filename):
    """Generate path for product images."""
    return get_file_path(instance, filename, 'products')

def get_profile_image_path(instance, filename):
    """Generate path for profile pictures."""
    return get_file_path(instance, filename, 'profile_pics')

def get_banner_image_path(instance, filename):
    """Generate path for banner images."""
    return get_file_path(instance, filename, 'banners')

def get_document_path(instance, filename):
    """Generate path for document uploads."""
    return get_file_path(instance, filename, 'documents')

def create_thumbnail(image_path, size=(300, 300)):
    """
    Create a thumbnail from an image.
    Args:
        image_path: Path to the original image
        size: Tuple of (width, height) for thumbnail
    Returns:
        Path to the created thumbnail
    """
    img = Image.open(image_path)
    
    # Convert RGBA to RGB if necessary
    if img.mode in ('RGBA', 'LA'):
        background = Image.new('RGB', img.size, 'white')
        background.paste(img, mask=img.split()[-1])
        img = background
    
    # Create thumbnail
    img.thumbnail(size)
    
    # Generate thumbnail path
    path = Path(image_path)
    thumbnail_dir = settings.MEDIA_ROOT / 'thumbnails'
    thumbnail_path = thumbnail_dir / f"thumb_{path.name}"
    
    # Save thumbnail
    img.save(thumbnail_path, 'JPEG', quality=85)
    
    return f"thumbnails/thumb_{path.name}"

def get_thumbnail_url(image_url):
    """
    Get the URL for an image's thumbnail.
    Args:
        image_url: URL of the original image
    Returns:
        URL of the thumbnail
    """
    if not image_url:
        return None
        
    path = Path(image_url)
    return f"thumbnails/thumb_{path.name}"

def clean_unused_media():
    """
    Clean up unused media files.
    This should be run periodically to remove orphaned files.
    """
    # Implementation depends on your specific needs
    pass
