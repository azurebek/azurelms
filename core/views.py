from django.shortcuts import render


def page_not_found(request, exception=None):
    return render(request, "errors/404.html", status=404)


def permission_denied(request, exception=None):
    return render(request, "errors/403.html", status=403)


def server_error(request):
    return render(request, "errors/500.html", status=500)


def maintenance(request):
    return render(request, "errors/maintenance.html", status=503)


def offline(request):
    return render(request, "errors/offline.html")
