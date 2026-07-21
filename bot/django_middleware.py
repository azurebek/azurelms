class TelegramMiniAppFrameMiddleware:
    """Telegram orqali tasdiqlangan sessionlarni Web Telegram iframe'ida ochadi."""

    FRAME_ANCESTORS = (
        "frame-ancestors 'self' https://web.telegram.org https://*.telegram.org"
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not request.session.get("telegram_miniapp"):
            return response

        response.headers.pop("X-Frame-Options", None)
        csp = response.headers.get("Content-Security-Policy", "").strip()
        if "frame-ancestors" not in csp.lower():
            response.headers["Content-Security-Policy"] = "; ".join(
                part for part in (csp.rstrip(";"), self.FRAME_ANCESTORS) if part
            )
        return response
