"""Public route javob siyosati: method, cache, robots, referrer (PUB1.1d).

`frontend/public_policy.py` registridagi `CacheClass` va method to'plami shu
middleware orqali **bitta joyda** qo'llanadi — view'lar o'z sarlavhasini
alohida yozmaydi, legacy va V1 renderer bir xil javob oladi.

Matritsa (`§5.3`):

* `SENSITIVE_NO_STORE` — `private, no-store`, `Pragma: no-cache`,
  `X-Robots-Tag: noindex…`, `Referrer-Policy: no-referrer`, ETag yo'q;
* `STATUS_NO_STORE` va har 4xx/5xx — `no-store`, `X-Robots-Tag: noindex`;
* `PUBLIC_CONTENT` / `PUBLIC_QUERY` — mehmonga va cookie qo'ymaydigan javobda
  `private, no-cache`: brauzer qayta tekshiradi (ETag → 304), umumiy (shared)
  cache **yo'q**. Kirgan foydalanuvchi sahifasi (sarlavhada uning ismi) yoki
  cookie (CSRF) qo'yadigan javob `private, no-store` — shaxsiy narsa diskda
  qolmaydi. Shared cache faqat anonim-invariant proyeksiya isbotlangach;
* preview (`?preview=1`) — `private, no-store`, noindex.

Registrdagi method'dan boshqa so'rov (OPTIONS'dan tashqari) `405` oladi.
Global CSP bu yerda o'zgartirilmaydi.
"""

from django.http import HttpResponseNotAllowed
from django.utils.cache import get_conditional_response, set_response_etag

from frontend.public_policy import CacheClass, surface_by_name

SENSITIVE_HEADERS = {
    "Cache-Control": "private, no-store, max-age=0",
    "Pragma": "no-cache",
    "X-Robots-Tag": "noindex, nofollow, noarchive",
    "Referrer-Policy": "no-referrer",
}
NO_STORE_HEADERS = {
    "Cache-Control": "no-store, max-age=0",
    "X-Robots-Tag": "noindex, nofollow",
}
PREVIEW_HEADERS = {
    "Cache-Control": "private, no-store, max-age=0",
    "X-Robots-Tag": "noindex, nofollow",
}
REVALIDATE_HEADERS = {"Cache-Control": "private, no-cache"}
PERSONAL_HEADERS = {"Cache-Control": "private, no-store, max-age=0"}
CLASS_HEADERS = {
    CacheClass.SENSITIVE_NO_STORE: SENSITIVE_HEADERS,
    CacheClass.STATUS_NO_STORE: NO_STORE_HEADERS,
    CacheClass.PUBLIC_QUERY: REVALIDATE_HEADERS,
    CacheClass.PUBLIC_CONTENT: REVALIDATE_HEADERS,
}
# Public sahifaga brauzer imkoniyatlari kerak emas (imtihon mikrofoni private route'da).
PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"


def policy_for(request):
    match = getattr(request, "resolver_match", None)
    return surface_by_name().get(getattr(match, "view_name", None))


def headers_for(request, response, policy):
    if policy.cache_class == CacheClass.SENSITIVE_NO_STORE:
        return SENSITIVE_HEADERS
    if response.status_code >= 400:
        return NO_STORE_HEADERS
    if request.GET.get("preview") == "1":
        return PREVIEW_HEADERS
    headers = CLASS_HEADERS.get(policy.cache_class, NO_STORE_HEADERS)
    if headers is REVALIDATE_HEADERS:
        user = getattr(request, "user", None)
        if (user is not None and user.is_authenticated) or response.cookies:
            return PERSONAL_HEADERS
    return headers


class PublicResponsePolicyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def process_view(self, request, view_func, view_args, view_kwargs):
        policy = policy_for(request)
        if policy is not None and request.method not in policy.methods and request.method != "OPTIONS":
            # CSRF'dan oldin: GET-only sahifaga POST jim render bo'lmaydi.
            return HttpResponseNotAllowed(sorted(policy.methods))
        return None

    def __call__(self, request):
        response = self.get_response(request)
        policy = policy_for(request)
        if policy is None:
            return response
        headers = headers_for(request, response, policy)
        for name, value in headers.items():
            response[name] = value
        response.headers.setdefault("Permissions-Policy", PERMISSIONS_POLICY)
        if headers is REVALIDATE_HEADERS:
            return self._conditional(request, response)
        if "ETag" in response:
            del response["ETag"]
        return response

    @staticmethod
    def _conditional(request, response):
        if request.method not in ("GET", "HEAD") or response.status_code != 200 or response.streaming:
            return response
        set_response_etag(response)
        return get_conditional_response(request, etag=response["ETag"], response=response) or response
