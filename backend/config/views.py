"""
Config-level views (e.g. API root, SPA catch-all).
"""
import os
from django.http import JsonResponse, HttpResponse
from django.conf import settings


# Minimal 1x1 transparent PNG (so /logo.png never 404s when requested from backend)
_LOGO_PNG_PLACEHOLDER = bytes([
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00, 0x00, 0x0D,
    0x49, 0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
    0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4, 0x89, 0x00, 0x00, 0x00,
    0x0A, 0x49, 0x44, 0x41, 0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,
    0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00, 0x00, 0x00, 0x00, 0x49,
    0x45, 0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82
])
_LOGO_SVG_PLACEHOLDER = (
    b'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1" viewBox="0 0 1 1"/>'
)


def serve_logo(request, filename):
    """Serve logo from backend/logos/ if present, else a tiny placeholder to avoid 404."""
    if request.method != 'GET':
        return HttpResponse(status=405)
    logos_dir = os.path.join(settings.BASE_DIR, 'logos')
    path = os.path.join(logos_dir, filename)
    if os.path.isfile(path):
        with open(path, 'rb') as f:
            content = f.read()
        content_type = 'image/svg+xml' if filename.lower().endswith('.svg') else 'image/png'
        return HttpResponse(content, content_type=content_type)
    if filename.lower().endswith('.svg'):
        return HttpResponse(_LOGO_SVG_PLACEHOLDER, content_type='image/svg+xml')
    return HttpResponse(_LOGO_PNG_PLACEHOLDER, content_type='image/png')


def health(request):
    """
    Health check for load balancers and Front Door (GET/HEAD).
    Returns 200 with no PHI; do not log request details in production.
    """
    if request.method not in ('GET', 'HEAD'):
        return HttpResponse(status=405)
    return JsonResponse({'status': 'ok'}, status=200)


def api_root(request):
    """Respond to GET /api/ so the API base URL does not 404."""
    if request.method != 'GET':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)
    return JsonResponse({
        'api': 'ok',
        'auth': '/api/auth/',
        'sessions': '/api/sessions/',
        'compliance': '/api/compliance/',
        'docs': '/api/docs/',
    })


def serve_spa(request, path=''):
    """
    Serve the SPA: for non-API paths, return index.html so client-side routing works.
    API paths (/api/...) are handled by urlpatterns; this view is only for catch-all.
    """
    build_dir = getattr(settings, 'FRONTEND_BUILD_DIR', None)
    if not build_dir or not os.path.isdir(build_dir):
        return JsonResponse({'detail': 'SPA build not configured'}, status=503)
    index_path = os.path.join(build_dir, 'index.html')
    if not os.path.isfile(index_path):
        return JsonResponse({'detail': 'index.html not found'}, status=503)
    with open(index_path, 'r', encoding='utf-8') as f:
        return HttpResponse(f.read(), content_type='text/html')
