"""Decorators de controle de acesso reutilizados pelas views."""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def role_required(check, message, redirect_to='dashboard'):
    """Exige login e que ``check(user)`` seja verdadeiro.

    Caso contrário, exibe ``message`` e redireciona para ``redirect_to``.
    """

    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not check(request.user):
                messages.error(request, message)
                return redirect(redirect_to)
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


admin_required = role_required(
    lambda u: u.is_admin, 'Acesso negado. Área exclusiva para administradores.'
)
agency_required = role_required(
    lambda u: u.is_agency, 'Acesso negado. Área exclusiva para órgãos competentes.'
)
citizen_required = role_required(
    lambda u: u.is_citizen, 'Acesso negado. Área exclusiva para cidadãos.'
)
owner_required = role_required(
    lambda u: u.is_platform_owner, 'Acesso restrito ao dono da plataforma.'
)
