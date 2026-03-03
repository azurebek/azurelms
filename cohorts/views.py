from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from courses.models import Course
from .models import Cohort, Enrollment, PaymentReceipt

@login_required
def checkout_view(request, course_id):
    course = get_object_or_404(Course, id=course_id, is_active=True)
    
    # Guruh mavjudligini tekshiramiz (eng so"nggi qo"shilgan faol guruhni olamiz)
    cohort = course.cohorts.filter(is_active=True).last()
    
    if not cohort:
        messages.error(request, "Ayni paytda bu kurs bo'yicha ochiq guruh yo'q.")
        return redirect('course_detail', pk=course.id)
        
    # O'quvchi bu kursga allaqachon a'zo bo'lganmi?
    enrollment, created = Enrollment.objects.get_or_create(
        student=request.user,
        cohort=cohort,
        defaults={'status': 'pending'}
    )
    
    if request.method == 'POST':
        # Chekni saqlaymiz
        receipt_image = request.FILES.get('receipt_image')
        amount_paid = request.POST.get('amount')
        
        if not receipt_image or not amount_paid:
            messages.error(request, "Iltimos, to'lov summasi va chek rasmini yuklang.")
            return render(request, 'cohorts/checkout.html', {'course': course, 'enrollment': enrollment})
            
        # Ma'lumotlarni saqlash
        PaymentReceipt.objects.create(
            enrollment=enrollment,
            receipt_image=receipt_image,
            amount=amount_paid
        )
        
        return redirect('cohorts:checkout_success')

    return render(request, 'cohorts/checkout.html', {'course': course, 'enrollment': enrollment})

@login_required
def checkout_success_view(request):
    return render(request, 'cohorts/checkout_success.html')
