"""
Apaga comprovantes de residência que já cumpriram sua finalidade (LGPD).

O comprovante só é necessário até o órgão decidir o cadastro. Depois de
``RESIDENCE_PROOF_RETENTION_DAYS`` dias da aprovação ou recusa, o arquivo é
removido e a referência no cadastro é limpa. Agende a execução diária, por
exemplo: ``docker compose exec backend python manage.py purge_residence_proofs``.
"""
import os
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import User


class Command(BaseCommand):
    help = 'Remove comprovantes de residência de cadastros decididos há mais tempo que o prazo de guarda.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Só lista o que seria removido.')

    def handle(self, *args, dry_run=False, **options):
        cutoff = timezone.now() - timedelta(days=settings.RESIDENCE_PROOF_RETENTION_DAYS)
        users = User.objects.exclude(residence_proof_path__isnull=True).exclude(residence_proof_path='').filter(
            Q(is_approved=True, approved_at__lt=cutoff)
            | Q(approval_requests__status='rejected', approval_requests__resolved_at__lt=cutoff)
        ).distinct()

        media_root = os.path.realpath(settings.MEDIA_ROOT)
        removed = 0
        for user in users:
            path = os.path.realpath(os.path.join(media_root, user.residence_proof_path))
            if dry_run:
                self.stdout.write(f'[simulação] usuário {user.pk}: {user.residence_proof_path}')
                continue
            if path.startswith(media_root + os.sep) and os.path.exists(path):
                os.remove(path)
                folder = os.path.dirname(path)
                if folder != media_root and not os.listdir(folder):
                    os.rmdir(folder)
            user.residence_proof_path = None
            user.save(update_fields=['residence_proof_path'])
            removed += 1

        action = 'seriam removidos' if dry_run else 'removidos'
        total = users.count() if dry_run else removed
        self.stdout.write(self.style.SUCCESS(f'{total} comprovante(s) {action} (prazo: {settings.RESIDENCE_PROOF_RETENTION_DAYS} dias).'))
