"""V1 listening source policy: no external hosts, remote fetch or CSP widening."""
from urllib.parse import urljoin, urlsplit


def listening_media_url(section, request):
    value = section.media_url or ''
    if section.section_type != 'listening' or not value or any(ord(c) <= 32 or c == '\\' for c in value):
        return ''
    try:
        base = urlsplit(request.build_absolute_uri('/'))
        source = urlsplit(urljoin(base.geturl(), value))
        def origin(url):
            return url.scheme.lower(), url.hostname, url.port or (443 if url.scheme == 'https' else 80)
        if source.scheme not in ('http', 'https') or source.username is not None or source.password is not None:
            return ''
        if origin(source) != origin(base):
            return ''
        return source.geturl()
    except ValueError:
        return ''
