"""Paginação compartilhada pelas listagens."""
from django.core.paginator import Paginator


def paginate(request, queryset, per_page):
    """Página pedida em ``?page=`` (números inválidos caem na primeira/última página)."""
    return Paginator(queryset, per_page).get_page(request.GET.get('page'))
