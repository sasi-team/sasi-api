from django.core.management.base import BaseCommand
from etl.etl_estoque import EstoqueETL

class Command(BaseCommand):
    help = 'Run ETL process for health indicators'

    def handle(self, *args, **options):
        etl = EstoqueETL()
        try:
            etl.run()
            self.stdout.write(self.style.SUCCESS('ETL completed successfully'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'ETL failed: {str(e)}'))