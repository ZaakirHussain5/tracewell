from django.core.management.base import BaseCommand

from traces.seed import load_demo


class Command(BaseCommand):
    help = "Replace the Strata Ops demo project with seeded agent traces."

    def handle(self, *args, **options):
        summary = load_demo()
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {summary['traces']} traces and {summary['spans']} spans "
                f"into {summary['project']}."
            )
        )
