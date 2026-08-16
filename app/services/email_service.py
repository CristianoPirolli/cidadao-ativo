"""
Serviço de envio de emails
Gerencia o envio de notificações por email aos usuários
"""
from threading import Thread

from django.conf import settings
from django.core.mail import EmailMultiAlternatives


def _send_async(msg: EmailMultiAlternatives) -> None:
    try:
        msg.send(fail_silently=False)
    except Exception as e:
        print(f"Erro ao enviar email: {e}")


def send_email(subject: str, recipients: list, html_body: str, text_body: str = None) -> None:
    if not getattr(settings, 'EMAIL_HOST_USER', ''):
        print(f"[EMAIL SIMULADO] Para: {recipients}")
        print(f"[EMAIL SIMULADO] Assunto: {subject}")
        print(f"[EMAIL SIMULADO] Corpo: {text_body or 'Ver HTML'}")
        return

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body or html_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients,
    )
    msg.attach_alternative(html_body, 'text/html')
    Thread(target=_send_async, args=(msg,), daemon=True).start()


def send_approval_email(user) -> None:
    """Envia email de aprovação de cadastro para o usuário."""
    if not user.email:
        return

    login_hint = ''
    if getattr(user, 'is_citizen', False) and user.cpf:
        from app.services.cpf_validation import format_cpf
        login_hint = f'CPF: {format_cpf(user.cpf)}'
    elif user.email:
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


def send_status_change_email(report, old_status: str, new_status: str) -> None:
    """Envia email de mudança de status do chamado."""
    if not report.user or not report.user.email:
        return

    user = report.user
    status_messages = {
        'visualizado': 'foi visualizado',
        'em_andamento': 'está sendo atendido',
        'concluido': 'foi concluído',
        'avaliado': 'foi avaliado',
        'rejeitado': 'foi rejeitado',
    }
    status_msg = status_messages.get(new_status, f'mudou para {new_status}')

    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #007bff;">Atualização do seu Chamado</h2>
                <p>Olá, <strong>{user.name}</strong>!</p>
                <p>Seu chamado <strong>#{report.id} - {report.title}</strong> {status_msg}.</p>
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 4px; margin: 20px 0;">
                    <p style="margin: 0;"><strong>Categoria:</strong> {report.category}</p>
                    <p style="margin: 10px 0 0;"><strong>Status anterior:</strong> {old_status}</p>
                    <p style="margin: 10px 0 0;"><strong>Novo status:</strong> {new_status}</p>
                </div>
            </div>
        </body>
    </html>
    """

    text_body = (
        f"Atualização do seu Chamado\n\n"
        f"Olá, {user.name}!\n\n"
        f"Seu chamado #{report.id} - {report.title} {status_msg}.\n\n"
        f"Categoria: {report.category}\n"
        f"Status anterior: {old_status}\n"
        f"Novo status: {new_status}\n"
    )

    send_email(
        f'Atualização do Chamado #{report.id} - Cidadão Ativo',
        [user.email],
        html_body,
        text_body,
    )


def send_report_completed_email(report) -> None:
    """Envia email quando chamado é concluído (para o cidadão avaliar)."""
    if not report.user or not report.user.email:
        return

    user = report.user

    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #28a745;">Chamado Concluído!</h2>
                <p>Olá, <strong>{user.name}</strong>!</p>
                <p>Seu chamado <strong>#{report.id} - {report.title}</strong> foi concluído pelo órgão responsável.</p>
                <div style="background-color: #d4edda; padding: 15px; border-radius: 4px; margin: 20px 0; border-left: 4px solid #28a745;">
                    <p style="margin: 0;"><strong>O que fazer agora?</strong></p>
                    <p style="margin: 10px 0 0;">Por favor, avalie o atendimento!</p>
                </div>
            </div>
        </body>
    </html>
    """

    text_body = (
        f"Chamado Concluído!\n\n"
        f"Olá, {user.name}!\n\n"
        f"Seu chamado #{report.id} - {report.title} foi concluído.\n\n"
        f"Por favor, avalie o atendimento!\n"
    )

    send_email(
        f'Chamado Concluído - Avalie! #{report.id} - Cidadão Ativo',
        [user.email],
        html_body,
        text_body,
    )
