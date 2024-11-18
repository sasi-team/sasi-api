import pandas as pd
from django.db import transaction
from api.models import Cidade, Indicador, MacroRegiao, RegiaoSaude, ValorIndicador
from django.core.management.base import BaseCommand

def clean_value(value):
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

@transaction.atomic
def import_cities_and_regions():
    df_indicador = pd.read_csv('../../assets/indicadores/indicador_3.csv')  # Use qualquer indicador como base
    
    cidade_regiao_map = {}
    
    for _, row in df_indicador.iterrows():
        macro_nome = row['Macrorregião de Saúde']
        regiao_nome = row['Região de Saúde']
        codigo_ibge = str(row['Cod. IBGE'])
        
        macro_regiao, _ = MacroRegiao.objects.get_or_create(nome=macro_nome)
        regiao_saude, _ = RegiaoSaude.objects.get_or_create(
            nome=regiao_nome,
            macro_regiao=macro_regiao
        )
        
        cidade_regiao_map[codigo_ibge] = regiao_saude
    
    df_cidades = pd.read_csv('../../assets/data/municipios.csv')
    
    for _, row in df_cidades.iterrows():
        codigo_ibge = row['codigo_ibge']
        codigo_ibge_sem_digito = str(codigo_ibge)[:-1]
        
        regiao_saude = cidade_regiao_map.get(codigo_ibge_sem_digito)
        
        Cidade.objects.create(
            codigo_ibge=str(codigo_ibge),
            nome=row['nome'],
            latitude=row['latitude'],
            longitude=row['longitude'],
            regiao_saude=regiao_saude
        )

def import_indicators():
    df = pd.read_csv('../../assets/data/titulo_subtitulo.csv')
    
    for _, row in df.iterrows():
        Indicador.objects.create(
            nome_arquivo=row['nome_arquivo'],
            titulo=row['titulo'],
            subtitulo=row['subtitulo'],
            fonte=row['fonte']
        )

@transaction.atomic
def import_indicator_values(indicador_nome):
    df = pd.read_csv(f'../../assets/indicadores/{indicador_nome}.csv')
    indicador = Indicador.objects.get(nome_arquivo=indicador_nome)
    
    for _, row in df.iterrows():
        codigo_ibge = str(row['Cod. IBGE'])
        try:
            cidade = Cidade.objects.get(codigo_ibge__startswith=codigo_ibge)
            
            for ano in range(2010, 2021):
                ano_str = str(ano)
                if ano_str in df.columns:
                    valor = clean_value(row[ano_str])
                    if valor is not None:
                        ValorIndicador.objects.create(
                            cidade=cidade,
                            indicador=indicador,
                            ano=ano,
                            valor=valor
                        )
        except Cidade.DoesNotExist:
            print(f"Cidade não encontrada para o código IBGE: {codigo_ibge}")
            continue

class Command(BaseCommand):
    help = 'Importando dados para o banco de dados'

    def handle(self, *args, **options):
        self.stdout.write('importando cidades e regiões...')
        try:
            import_cities_and_regions()
        except Exception as e:
            self.stdout.write(f'Erro ao importando cidades e regiões: {str(e)}')
                    
        self.stdout.write('importando indicadores...')
        try:
            import_indicators()
        except Exception as e:
            self.stdout.write(f'Erro ao importando indicadores: {str(e)}')        
        pd_indicadores = pd.read_csv('../../assets/data/titulo_subtitulo.csv')
        indicadores = pd_indicadores['nome_arquivo'].tolist()
        
        for indicador in indicadores:
            self.stdout.write(f'Importando dados de: {indicador}...')
            try:
                import_indicator_values(indicador)
            except Exception as e:
                self.stdout.write(f'Erro ao importar dados de: {indicador}: {str(e)}')
        
        self.stdout.write('Importação finalizada com sucesso!')