"""
Serviço de envio de emails
Gerencia o envio de notificações por email aos usuários
"""
from flask_mail import Message
from flask import render_template_string
from app import mail
from threading import Thread


def send_async_email(app, msg):
    """Envia email de forma assíncrona"""
    with app.app_context():
        try:
            mail.send(msg)
        except Exception as e:
            # Log do erro (em produção, usar logger adequado)
            print(f"Erro ao enviar email: {str(e)}")


def send_email(subject, recipients, html_body, text_body=None):
    """
    Envia email

    Args:
        subject: Assunto do email
        recipients: Lista de destinatários
        html_body: Corpo do email em HTML
        text_body: Corpo do email em texto plano (opcional)
    """
    from flask import current_app

    # Se o email não estiver configurado, apenas loga
    if not current_app.config.get('MAIL_USERNAME'):
        print(f"[EMAIL SIMULADO] Para: {recipients}")
        print(f"[EMAIL SIMULADO] Assunto: {subject}")
        print(f"[EMAIL SIMULADO] Corpo: {text_body or 'Ver HTML'}")
        return

    msg = Message(
        subject=subject,
        recipients=recipients,
        html=html_body,
        body=text_body or html_body
    )

    # Enviar de forma assíncrona
    Thread(
        target=send_async_email,
        args=(current_app._get_current_object(), msg)
    ).start()


def send_approval_email(user):
    """Envia email de aprovação de cadastro para o usuário."""
    subject = "Cadastro aprovado - Cidadão Ativo"

    login_hint = ""
    if getattr(user, "is_citizen", False) and user.cpf:
        from app.services.cpf_validation import format_cpf  # import local para evitar ciclos

        login_hint = f"CPF: {format_cpf(user.cpf)}"
    elif user.email:
        login_hint = f"Email: {user.email}"

    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #007bff;">Cadastro aprovado!</h2>
                <p>Olá, <strong>{user.name}</strong>!</p>
                <p>Seu cadastro na plataforma <strong>Cidadão Ativo</strong> foi aprovado.</p>
                <p>Agora você já pode fazer login e começar a registrar chamados na sua cidade.</p>
                <p style="margin-top: 30px;">
                    <a href="http://localhost:5000/login"
                       style="background-color: #007bff; color: white; padding: 12px 24px;
                              text-decoration: none; border-radius: 4px; display: inline-block;">
                        Acessar plataforma
                    </a>
                </p>
                <p style="margin-top: 30px; color: #444;">
                    <strong>Como entrar:</strong><br>
                    {login_hint or "Use as credenciais definidas no cadastro."}<br>
                    Senha: a mesma definida durante o cadastro.
                </p>
                <hr style="margin: 30px 0; border: none; border-top: 1px solid #ddd;">
                <p style="color: #999; font-size: 12px;">
                    Este é um email automático da plataforma Cidadão Ativo. Por favor, não responda.
                </p>
            </div>
        </body>
    </html>
    """

    text_body = f"""
    Cadastro aprovado!

    Olá, {user.name}!

    Seu cadastro na plataforma Cidadão Ativo foi aprovado.

    Como entrar:
    - {login_hint or "Use as credenciais definidas no cadastro."}
    - Senha: a mesma definida durante o cadastro.

    Acesse: http://localhost:5000/login

    ---
    Este é um email automático da plataforma Cidadão Ativo.
    """

    send_email(subject, [user.email], html_body, text_body)


def send_status_change_email(report, old_status, new_status):
    """Envia email de mudança de status do chamado"""
    if not report.user or not report.user.email:
        return

    user = report.user
    subject = f"Atualização do Chamado #{report.id} - Cidadão Ativo"

    status_messages = {
        'visualizado': 'foi visualizado',
        'em_andamento': 'está sendo atendido',
        'concluido': 'foi concluído',
        'avaliado': 'foi avaliado',
        'rejeitado': 'foi rejeitado'
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
                    <p style="margin: 10px 0 0 0;"><strong>Status anterior:</strong> {old_status}</p>
                    <p style="margin: 10px 0 0 0;"><strong>Novo status:</strong> {new_status}</p>
                </div>

                <p style="margin-top: 30px;">
                    <a href="http://localhost:5000/report/{report.id}"
                       style="background-color: #007bff; color: white; padding: 12px 24px;
                              text-decoration: none; border-radius: 4px; display: inline-block;">
                        Ver Detalhes do Chamado
                    </a>
                </p>

                <hr style="margin: 30px 0; border: none; border-top: 1px solid #ddd;">
                <p style="color: #999; font-size: 12px;">
                    Este é um email automático da plataforma Cidadão Ativo. Por favor, não responda.
                </p>
            </div>
        </body>
    </html>
    """

    text_body = f"""
    Atualização do seu Chamado

    Olá, {user.name}!

    Seu chamado #{report.id} - {report.title} {status_msg}.

    Detalhes:
    - Categoria: {report.category}
    - Status anterior: {old_status}
    - Novo status: {new_status}

    Ver detalhes: http://localhost:5000/report/{report.id}

    ---
    Este é um email automático da plataforma Cidadão Ativo.
    """

    send_email(subject, [user.email], html_body, text_body)


def send_report_completed_email(report):
    """Envia email quando chamado é concluído (para cidadão avaliar)"""
    if not report.user or not report.user.email:
        return

    user = report.user
    subject = f"Chamado Concluído - Avalie! #{report.id} - Cidadão Ativo"

    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #28a745;">Chamado Concluído!</h2>
                <p>Olá, <strong>{user.name}</strong>!</p>
                <p>Temos uma ótima notícia! Seu chamado <strong>#{report.id} - {report.title}</strong> foi concluído pelo órgão responsável.</p>

                <div style="background-color: #d4edda; padding: 15px; border-radius: 4px; margin: 20px 0; border-left: 4px solid #28a745;">
                    <p style="margin: 0;"><strong>O que fazer agora?</strong></p>
                    <p style="margin: 10px 0 0 0;">Por favor, avalie o atendimento! Sua opinião é muito importante para melhorarmos os serviços públicos.</p>
                </div>

                <p style="margin-top: 30px;">
                    <a href="http://localhost:5000/report/{report.id}"
                       style="background-color: #28a745; color: white; padding: 12px 24px;
                              text-decoration: none; border-radius: 4px; display: inline-block;">
                        Avaliar Atendimento
                    </a>
                </p>

                <hr style="margin: 30px 0; border: none; border-top: 1px solid #ddd;">
                <p style="color: #999; font-size: 12px;">
                    Este é um email automático da plataforma Cidadão Ativo. Por favor, não responda.
                </p>
            </div>
        </body>
    </html>
    """

    text_body = f"""
    Chamado Concluído!

    Olá, {user.name}!

    Temos uma ótima notícia! Seu chamado #{report.id} - {report.title} foi concluído pelo órgão responsável.

    O que fazer agora?
    Por favor, avalie o atendimento! Sua opinião é muito importante para melhorarmos os serviços públicos.

    Avaliar atendimento: http://localhost:5000/report/{report.id}

    ---
    Este é um email automático da plataforma Cidadão Ativo.
    """

    send_email(subject, [user.email], html_body, text_body)
