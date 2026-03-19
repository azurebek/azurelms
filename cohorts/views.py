from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
import datetime
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
    
    # Check if there is already a pending receipt
    has_pending_receipt = PaymentReceipt.objects.filter(
        enrollment=enrollment, 
        is_verified=False
    ).exists()
    
    # Calculate period_start and period_end for this payment
    today = timezone.now().date()
    if enrollment.status == 'active' and enrollment.next_payment_deadline and enrollment.next_payment_deadline > today:
        # Extend from current deadline
        tentative_start = enrollment.next_payment_deadline
    else:
        # Start immediately
        tentative_start = today
        
    tentative_end = tentative_start + datetime.timedelta(days=30)
    
    if request.method == 'POST':
        if has_pending_receipt:
            messages.error(request, "Sizda allaqachon tasdiqlanmagan to'lov cheki mavjud. Iltimos, administrator tasdiqlashini kuting.")
            return redirect('cohorts:checkout', course_id=course.id)
            
        # Chekni saqlaymiz
        receipt_image = request.FILES.get('receipt_image')
        # Security: Do not trust client's amount. Use course.price.
        amount_paid = course.price
        
        if not receipt_image:
            messages.error(request, "Iltimos, to'lov chek rasmini yuklang.")
            return render(request, 'cohorts/checkout.html', {
                'course': course, 
                'enrollment': enrollment,
                'has_pending_receipt': has_pending_receipt,
                'period_start': tentative_start,
                'period_end': tentative_end
            })
            
        # Ma'lumotlarni saqlash
        PaymentReceipt.objects.create(
            enrollment=enrollment,
            receipt_image=receipt_image,
            amount=amount_paid,
            period_start=tentative_start,
            period_end=tentative_end
        )
        
        return redirect('cohorts:checkout_success')

    return render(request, 'cohorts/checkout.html', {
        'course': course, 
        'enrollment': enrollment,
        'has_pending_receipt': has_pending_receipt,
        'period_start': tentative_start,
        'period_end': tentative_end
    })

@login_required
def checkout_success_view(request):
    return render(request, 'cohorts/checkout_success.html')
