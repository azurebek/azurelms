import os
from io import BytesIO
from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFont


def generate_certificate_image(certificate_instance):
    # Shablon va shrift yo'llari
    template_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'blank_certificate.jpg')
    font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'arial.ttf')

    # Agar shablon topilmasa, ishni to'xtatish
    if not os.path.exists(template_path) or not os.path.exists(font_path):
        print("❌ Sertifikat shabloni yoki shrift topilmadi!")
        return

    # Bo'sh rasmni ochish
    img = Image.open(template_path)
    draw = ImageDraw.Draw(img)

    # Shrift kattaliklari (Bularni o'zingizning rasmingiz o'lchamiga qarab o'zgartirasiz)
    title_font = ImageFont.truetype(font_path, 80)
    text_font = ImageFont.truetype(font_path, 40)
    id_font = ImageFont.truetype(font_path, 25)

    # Matnlarni tayyorlash
    student_name = f"{certificate_instance.student.first_name} {certificate_instance.student.last_name}".strip()
    if not student_name:
        student_name = certificate_instance.student.username.upper()

    course_name = certificate_instance.course.title
    cert_id = str(certificate_instance.certificate_id)

    # 1. O'quvchi ismini yozish (Kordinatalar: X (chapdan), Y (tepadan))
    draw.text((400, 500), student_name, font=title_font, fill="black")

    # 2. Kurs nomini yozish
    draw.text((400, 650), f"Tugatgan kursi: {course_name}", font=text_font, fill="#333333")

    # 3. Noyob ID raqamini pastki burchakka yozish
    draw.text((100, 1000), f"Sertifikat ID: {cert_id}", font=id_font, fill="gray")

    # Tayyor rasmni xotiraga saqlash
    buffer = BytesIO()
    img.save(buffer, format='JPEG')

    # Rasmni Sertifikat jadvalidagi "file" maydoniga biriktirish
    file_name = f"{student_name}_{course_name}_cert.jpg".replace(" ", "_")
    certificate_instance.file.save(file_name, ContentFile(buffer.getvalue()), save=False)