"""Páginas públicas e endpoints de infraestrutura."""
from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


def index(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/welcome.html')


@never_cache
@require_GET
def healthcheck(request):
    """Usado pelo Docker/Nginx para verificar se a aplicação e o banco respondem."""
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
    except Exception:
        return JsonResponse({'status': 'error', 'database': 'unavailable'}, status=503)
    return JsonResponse({'status': 'ok', 'database': 'ok'})


def privacy_policy(request):
    return render(request, 'core/privacy.html', {
        'controller_name': settings.PRIVACY_CONTROLLER_NAME,
        'contact_email': settings.PRIVACY_CONTACT_EMAIL,
        'retention_days': settings.RESIDENCE_PROOF_RETENTION_DAYS,
    })
