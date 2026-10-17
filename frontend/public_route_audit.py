"""Har nomli route'ning joriy xulqi: kim nimani oladi (PUB1.1a).

Registry (`frontend/public_policy.py`) maqsadni aytadi, bu modul esa haqiqatni
o'lchaydi: anonim, tizimga kirgan va faolsizlantirilgan foydalanuvchi uchun GET
natijasi, anonim HEAD/POST, va public yuzada maqsad bilan joriy javob farqi.
Natija test fixture'ida snapshot sifatida saqlanadi — xulq o'zgarsa test
ko'rsatadi va snapshot ongli ravishda yangilanadi.

Faqat test muhitida ishlatiladi: so'rovlar POST ham yuboradi.
"""

from django.test import Client
from django.urls import Resolver404, resolve, reverse

from frontend.public_policy import CacheClass, PUBLIC, classify, route_inventory, surface_by_name

# Fixture'da bo'lmagan obyekt identifikatori: private route lookup'i 404 beradi,
# natija baza sequence'iga bog'liq bo'lmaydi.
MISSING_ID = 999999
MAX_REDIRECTS = 5


def build_url(name, converters, kwargs_for):
    kwargs = {param: kwargs_for(name, param) for param in converters}
    return reverse(name, kwargs=kwargs)


def _route_name(path):
    try:
        match = resolve(path)
    except Resolver404:
        return path
    return match.view_name


def describe(response):
    """`200`, `302>login` kabi deterministik qisqa ko'rinish (URL'dagi id'siz)."""
    location = response.get("Location", "")
    if location:
        return f"{response.status_code}>{_route_name(location.split('?', 1)[0])}"
    return str(response.status_code)


def final_hop(client, url):
    """Redirect zanjirining oxiri: (status, route nomi)."""
    response = client.get(url)
    hops = 0
    while response.status_code in (301, 302, 303, 307, 308) and hops < MAX_REDIRECTS:
        url = response["Location"]
        response = client.get(url)
        hops += 1
    return response.status_code, _route_name(url.split("?", 1)[0])


def _declared_differences(policy, response, observed_methods):
    """Maqsad bilan joriy javob farqi — PUB1.1b–d uchun dalil, xato emas."""
    notes = []
    for method in ("GET", "HEAD", "POST"):
        accepted = observed_methods[method]
        declared = method in policy.methods
        if accepted and not declared:
            notes.append(f"{method} qabul qilinadi, registryda yo'q")
        if declared and not accepted:
            notes.append(f"{method} registryda bor, lekin 405")
    if "GET" in policy.methods and response is not None:
        cache = response.get("Cache-Control", "")
        if policy.cache_class in {CacheClass.SENSITIVE_NO_STORE, CacheClass.STATUS_NO_STORE} and "no-store" not in cache:
            notes.append("no-store yo'q")
        if policy.index_policy == "noindex":
            body = response.content.decode("utf-8", "ignore").lower() if not response.streaming else ""
            robots = response.get("X-Robots-Tag", "").lower()
            if "noindex" not in robots and 'name="robots" content="noindex' not in body:
                notes.append("noindex belgisi yo'q")
    return notes


def observe(kwargs_for, *, authenticated_user, deactivated_user):
    """Har route uchun bitta qator (dict). Snapshot va invariant testlari uchun."""
    surfaces = surface_by_name()
    # Har yangi Client middleware zanjirini qayta quradi (sekin): bir marta
    # yaratiladi, anonimlarning cookie'si har route oldidan tozalanadi.
    anonymous, probe, member, deactivated = Client(), Client(), Client(), Client()
    member.force_login(authenticated_user)
    deactivated.force_login(deactivated_user)
    rows = []
    for name, _pattern, converters in route_inventory():
        url = build_url(name, converters, kwargs_for)
        anonymous.cookies.clear()
        probe.cookies.clear()

        anon_get = anonymous.get(url)
        head = probe.head(url)
        probe.cookies.clear()
        post = probe.post(url)
        row = {
            "name": name,
            "class": classify(name),
            "anonymous": describe(anon_get),
            "authenticated": describe(member.get(url)),
            "deactivated": describe(deactivated.get(url)),
            "head": describe(head),
            "post": describe(post),
        }
        policy = surfaces.get(name)
        if policy is not None:
            observed = {"GET": anon_get.status_code != 405, "HEAD": head.status_code != 405, "POST": post.status_code != 405}
            row["differences"] = _declared_differences(policy, anon_get if observed["GET"] else None, observed)
        rows.append(row)
    return rows


def public_names():
    return {name for name, _pattern, _converters in route_inventory() if classify(name) == PUBLIC}
