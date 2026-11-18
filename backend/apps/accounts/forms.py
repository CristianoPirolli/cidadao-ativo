"""Formulários de conta que dependem dos formulários de autenticação do Django."""
from django import forms
from django.contrib.auth.forms import PasswordResetForm
from django.template import loader

from apps.accounts.models import User
from apps.accounts.services.auth import AuthenticationError, parse_login_identifier
from apps.core.services.email import send_email


class PasswordRecoveryForm(PasswordResetForm):
    """
    Recuperação de senha por CPF ou e-mail.

    O link vai sempre para o e-mail cadastrado na conta. A resposta da tela é a
    mesma exista a conta ou não, para não revelar quais CPFs estão cadastrados.
    """

    email = forms.CharField(
        label='CPF ou e-mail',
        max_length=254,
        widget=forms.TextInput(attrs={'autocomplete': 'username', 'autocapitalize': 'none'}),
    )

    def get_users(self, identifier):
        try:
            field, value = parse_login_identifier(identifier)
        except AuthenticationError:
            return []
        user = User.objects.filter(**{field: value}, is_active=True).exclude(email__isnull=True).exclude(email='').first()
        return [user] if user and user.has_usable_password() else []

    def send_mail(self, subject_template_name, email_template_name, context, from_email, to_email,
                  html_email_template_name=None):
        subject = ''.join(loader.render_to_string(subject_template_name, context).splitlines())
        text_body = loader.render_to_string(email_template_name, context)
        html_body = loader.render_to_string(html_email_template_name, context) if html_email_template_name else text_body
        send_email(subject, [to_email], html_body, text_body)
