"""Middlewares da aplicação."""
from django.shortcuts import redirect
from django.urls import reverse

# Caminhos que não exigem o aceite da política (incluindo a própria tela de aceite)
CONSENT_EXEMPT_PREFIXES = (
    '/privacidade', '/logout', '/static/', '/uploads/', '/api/', '/sw.js',
    '/manifest.webmanifest', '/offline', '/health', '/django-admin/',
)


class PrivacyConsentMiddleware:
    """
    Pede o aceite da política de privacidade a quem tem conta mas ainda não aceitou
    (contas criadas antes da política). Só intercepta navegação de páginas (GET).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if (
            request.method == 'GET'
            and user is not None
            and user.is_authenticated
            and user.privacy_accepted_at is None
            and not request.path.startswith(CONSENT_EXEMPT_PREFIXES)
        ):
            return redirect(f"{reverse('privacy_consent')}?next={request.get_full_path()}")
        return self.get_response(request)
