import os
from django.core.exceptions import ValidationError

def validate_file_size(value):
    """
    Validates that the uploaded file size is not larger than 5 MB.
    """
    filesize = value.size
    
    # 5 MB limit
    if filesize > 5 * 1024 * 1024:
        raise ValidationError("Fayl hajmi 5MB dan oshmasligi kerak.")
    return value

def validate_image_extension(value):
    """
    Strictly validates that the uploaded file has an allowed image extension.
    """
    ext = os.path.splitext(value.name)[1].lower()
    valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
    if not ext in valid_extensions:
        raise ValidationError("Faqat shu formatdagi fayllarga ruxsat beriladi: .jpg, .jpeg, .png, .webp")
    return value
