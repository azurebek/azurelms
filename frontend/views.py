from django.shortcuts import redirect
from django.utils.cache import patch_cache_control
from .public_content import about_projection, current_renderer, home_projection
from .public_v1 import render_public
from .models import LegalPage


def home_view(request):
    """Mehmon uchun bosh sahifa; kirgan foydalanuvchi dashboard'ga.

    Ma'lumot `frontend/public_content.py` proyeksiyasidan: renderer faqat
    o'zi chizadiganini oladi, tartib deterministik (PUB1.2b).
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    # Renderer bir marta tanlanadi: proyeksiya va shablon ayni qarordan.
    renderer = current_renderer()
    return render_public(request, 'index.html', home_projection(renderer), renderer=renderer)


def about_view(request):
    renderer = current_renderer()
    return render_public(request, 'about.html', about_projection(renderer), renderer=renderer)


def legal_page_view(request, page_type):
    # Owner yozmagan sahifa yaratilmaydi va umumiy namuna matn siyosat sifatida
    # chiqmaydi: halol "hali e'lon qilinmagan" javobi, indekslanmaydi (PUB1.0e).
    # Maxfiylik va shartlar faqat amaldagi tasdiqlangan versiyadan (PUB1.5a);
    # FAQ huquqiy hujjat emas — `LegalPage`da qoladi.
    from . import legal_revisions

    context = {"active_legal_page": page_type}
    if page_type in legal_revisions.KINDS:
        page = legal_revisions.effective_revision(page_type)
        if page is not None:
            context.update(legal_version=page.version_label, legal_effective_at=page.effective_at)
    else:
        page = LegalPage.published(page_type)
    context.update(legal_page=page, legal_title=page.title if page else LegalPage.UNAVAILABLE_TITLES[page_type])
    response = render_public(request, "legal_page.html", context)
    if page is None:
        response.status_code = 503
        response["X-Robots-Tag"] = "noindex"
        patch_cache_control(response, no_store=True)
    return response
