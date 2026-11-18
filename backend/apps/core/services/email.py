"""Envio de e-mails de notificação aos usuários."""
import logging
from threading import Thread

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def _send_async(msg: EmailMultiAlternatives) -> None:
    try:
        msg.send(fail_silently=False)
    except Exception:
        logger.exception('Erro ao enviar e-mail para %s', msg.to)


def send_email(subject: str, recipients: list, html_body: str, text_body: str = None) -> None:
    if not getattr(settings, 'EMAIL_HOST_USER', ''):
        logger.info('[E-MAIL SIMULADO] Para: %s | Assunto: %s\n%s', recipients, subject, text_body or html_body)
        return

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body or html_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients,
    )
    msg.attach_alternative(html_body, 'text/html')
    Thread(target=_send_async, args=(msg,), daemon=True).start()


def send_templated_email(subject: str, recipients: list, template: str, context: dict) -> None:
    """Envia ``<template>.txt`` e ``<template>.html`` (com escape automático dos dados do usuário)."""
    text_body = render_to_string(f'{template}.txt', context)
    html_body = render_to_string(f'{template}.html', context)
    send_email(subject, recipients, html_body, text_body)


def send_approval_email(user) -> None:
    """Envia email de aprovação de cadastro para o usuário."""
    if not user.email:
        return

    login_hint = ''
    if getattr(user, 'is_citizen', False) and user.cpf:
        from apps.core.services.cpf import format_cpf
        login_hint = f'CPF: {format_cpf(user.cpf)}'
    else:
        login_hint = f'Email: {user.email}'

    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #007bff;">Cadastro aprovado!</h2>
                <p>Olá, <strong>{user.name}</strong>!</p>
                <p>Seu cadastro na plataforma <strong>Cidadão Ativo</strong> foi aprovado.</p>
                <p>Agora você já pode fazer login e começar a registrar chamados na sua cidade.</p>
                <p style="margin-top: 30px;">
                    <strong>Como entrar:</strong><br>
                    {login_hint or 'Use as credenciais definidas no cadastro.'}<br>
                    Senha: a mesma definida durante o cadastro.
                </p>
            </div>
        </body>
    </html>
    """

    text_body = (
        f"Cadastro aprovado!\n\n"
        f"Olá, {user.name}!\n\n"
        f"Seu cadastro na plataforma Cidadão Ativo foi aprovado.\n\n"
        f"Como entrar:\n"
        f"- {login_hint or 'Use as credenciais definidas no cadastro.'}\n"
        f"- Senha: a mesma definida durante o cadastro.\n"
    )

    send_email('Cadastro aprovado - Cidadão Ativo', [user.email], html_body, text_body)
