"""Páginas públicas e endpoints de infraestrutura."""
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
