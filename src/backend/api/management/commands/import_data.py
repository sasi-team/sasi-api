from django.core.management.base import BaseCommand
from etl.data_processor import HealthDataETL

class Command(BaseCommand):
    help = 'Run ETL process for health indicators'

    def handle(self, *args, **options):
        etl = HealthDataETL()
        try:
            etl.process_excel_file('assets/data/serie_historica.xlsx')
            self.stdout.write(self.style.SUCCESS('ETL completed successfully'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'ETL failed: {str(e)}'))