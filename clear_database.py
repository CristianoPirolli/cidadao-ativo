#!/usr/bin/env python
"""
Script para limpar todos os dados do banco de dados
Útil para resetar o banco antes de apresentações (Mostra Tech)
"""
import sys
from app import app, db
from app.models.models import Report, User, ReportHistory, Notification, ApprovalRequest

def clear_all_data():
    """Remove todos os dados de todas as tabelas"""
    with app.app_context():
        try:
            print("\n" + "="*60)
            print("LIMPEZA DO BANCO DE DADOS - CIDADAO ATIVO")
            print("="*60)

            # Confirmar ação
            print("\n[!] ATENCAO: Esta acao ira EXCLUIR TODOS os dados do banco!")
            print("   - Todas as denuncias")
            print("   - Todos os usuarios")
            print("   - Todo o historico")
            print("   - Todas as notificacoes")
            print("   - Todas as solicitacoes de aprovacao")
            print("\nEsta acao NAO pode ser desfeita!\n")

            confirm = input("Digite 'CONFIRMAR' para continuar: ")

            if confirm != 'CONFIRMAR':
                print("\n[X] Operacao cancelada.")
                return False

            print("\n[*] Iniciando limpeza do banco de dados...\n")

            # Contar registros antes da exclusão
            reports_count = Report.query.count()
            users_count = User.query.count()
            history_count = ReportHistory.query.count()
            notifications_count = Notification.query.count()
            approvals_count = ApprovalRequest.query.count()

            print(f"[*] Registros encontrados:")
            print(f"   - Denuncias: {reports_count}")
            print(f"   - Usuarios: {users_count}")
            print(f"   - Historicos: {history_count}")
            print(f"   - Notificacoes: {notifications_count}")
            print(f"   - Solicitacoes de aprovacao: {approvals_count}")
            print(f"   TOTAL: {reports_count + users_count + history_count + notifications_count + approvals_count}\n")

            # Deletar todos os registros (ordem importa devido às FKs)
            print("[*] Deletando dados...")

            # 1. Notificações (referencia User e Report)
            print("   -> Notificacoes...", end=" ")
            Notification.query.delete()
            print("OK")

            # 2. Histórico de denúncias (referencia Report e User)
            print("   -> Historico de denuncias...", end=" ")
            ReportHistory.query.delete()
            print("OK")

            # 3. Solicitações de aprovação (referencia User)
            print("   -> Solicitacoes de aprovacao...", end=" ")
            ApprovalRequest.query.delete()
            print("OK")

            # 4. Denúncias (referencia User)
            print("   -> Denuncias...", end=" ")
            Report.query.delete()
            print("OK")

            # 5. Usuários (última tabela - é referenciada por outras)
            # Primeiro, remover a auto-referência (approved_by)
            print("   -> Removendo auto-referencias de usuarios...", end=" ")
            db.session.execute(db.text("UPDATE user SET approved_by = NULL"))
            print("OK")

            print("   -> Usuarios...", end=" ")
            User.query.delete()
            print("OK")

            # Commit das alterações
            print("\n[*] Salvando alteracoes...", end=" ")
            db.session.commit()
            print("OK")

            print("\n" + "="*60)
            print("[OK] BANCO DE DADOS LIMPO COM SUCESSO!")
            print("="*60)
            print(f"\n[*] Registros excluidos:")
            print(f"   - Denuncias: {reports_count}")
            print(f"   - Usuarios: {users_count}")
            print(f"   - Historicos: {history_count}")
            print(f"   - Notificacoes: {notifications_count}")
            print(f"   - Solicitacoes: {approvals_count}")
            print(f"\n[OK] Seu banco esta pronto para novos dados!")
            print("\n[*] Dicas para a Mostra Tech:")
            print("   1. Crie um novo admin: flask create-admin")
            print("   2. Ou use o admin padrao: flask create-dev-admin")
            print("   3. Registre novos orgaos e cidadaos atraves da interface\n")

            return True

        except Exception as e:
            db.session.rollback()
            print(f"\n[X] ERRO ao limpar banco de dados: {str(e)}")
            print("\n[*] Tente verificar:")
            print("   - Se o banco de dados esta acessivel")
            print("   - Se nao ha processos travados no banco")
            print("   - Se as tabelas existem no banco\n")
            return False

def main():
    """Função principal"""
    success = clear_all_data()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
