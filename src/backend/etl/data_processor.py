import pandas as pd
import logging
from pathlib import Path
from typing import Dict, List, Optional
from django.db import transaction
from api.models import Cidade, Indicador, MacroRegiao, RegiaoSaude, ValorIndicador
import re

class HealthDataETL:
    def __init__(self):
        self.data_dir = Path('assets/data')
        self.indicadores_dir = Path('assets/indicadores')
        self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('etl.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def clean_numeric_value(self, value) -> Optional[float]:
        """Limpa e converte valores numéricos"""
        if pd.isna(value):
            return None
        try:
            cleaned = str(value).replace(',', '.').strip()
            return float(cleaned)
        except (ValueError, TypeError):
            return None

    def validate_sheet_structure(self, df: pd.DataFrame) -> bool:
        """Valida se a planilha possui as colunas necessárias"""
        required_cols = ['Macrorregião de Saúde', 'Região de Saúde', 'Cod. IBGE', 'Município']
        return all(col in df.columns for col in required_cols)

    @transaction.atomic
    def process_excel_file(self, xlsx_path: str):
        """Processo principal de ETL"""
        try:
            self.logger.info(f"Iniciando processo ETL para {xlsx_path}")
            
            xl = pd.ExcelFile(xlsx_path)
            metadata_df = self.extract_metadata(xl)
            self.save_metadata(metadata_df)
            
            for sheet_name in xl.sheet_names:
                if not self.is_valid_indicator_sheet(sheet_name):
                    continue
                    
                self.logger.info(f"Processando planilha: {sheet_name}")
                df = self.process_indicator_sheet(xl, sheet_name)
                if df is not None:
                    self.save_indicator_data(sheet_name, df)
            
            self.import_to_database()
            
            self.logger.info("Processo ETL concluído com sucesso")
            
        except Exception as e:
            self.logger.error(f"Processo ETL falhou: {str(e)}")
            raise

    def extract_metadata(self, xl: pd.ExcelFile) -> pd.DataFrame:
        """Extrai metadados (título, subtítulo, fonte) das planilhas"""
        metadata = []
        
        for sheet_name in xl.sheet_names:
            if not self.is_valid_indicator_sheet(sheet_name):
                continue
                
            df = xl.parse(sheet_name, header=None)
            metadata.append({
                'nome_arquivo': sheet_name.lower().replace(" ", "_"),
                'titulo': df.iloc[0, 0],
                'subtitulo': df.iloc[1, 0],
                'fonte': self.extract_source(df)
            })
            
        return pd.DataFrame(metadata)

    def extract_source(self, df: pd.DataFrame) -> Optional[str]:
        """Extrai informações da fonte do dataframe"""
        for i in range(min(10, len(df))):
            cell = df.iloc[-(i+1), 0]
            if isinstance(cell, str) and 'fonte:' in cell.lower():
                return cell.strip()
        return None

    def extract_year_columns(self, df: pd.DataFrame) -> List[str]:
        """Extrai colunas que representam anos"""
        return [col for col in df.columns if re.match(r'^\d{4}$', str(col))]

    def process_indicator_sheet(self, xl: pd.ExcelFile, sheet_name: str) -> Optional[pd.DataFrame]:
        """Processa planilha de indicador individual"""
        try:
            df = xl.parse(sheet_name, header=2)
            
            if not self.validate_sheet_structure(df):
                self.logger.warning(f"Estrutura de planilha inválida: {sheet_name}")
                return None
                
            df = df.dropna(subset=['Cod. IBGE'])
            df['Cod. IBGE'] = df['Cod. IBGE'].astype(int)
            
            year_cols = self.extract_year_columns(df)
            for col in year_cols:
                df[col] = df[col].apply(self.clean_numeric_value)
                
            return df
            
        except Exception as e:
            self.logger.error(f"Erro ao processar planilha {sheet_name}: {str(e)}")
            return None

    def is_valid_indicator_sheet(self, sheet_name: str) -> bool:
        """Verifica se o nome da planilha corresponde ao padrão de indicador válido"""
        return bool(re.match(r'^indicador_\d+$', sheet_name.lower().replace(" ", "_")))

    @transaction.atomic
    def import_to_database(self):
        """Importa dados processados para o banco de dados"""
        try:
            self.import_regions_and_cities()
            
            self.import_indicators()
            
            self.import_indicator_values()
            
        except Exception as e:
            self.logger.error(f"Importação para o banco de dados falhou: {str(e)}")
            raise

    def save_metadata(self, df: pd.DataFrame):
        """Salva metadados em CSV"""
        output_path = self.data_dir / 'titulo_subtitulo.csv'
        df.to_csv(output_path, index=False, encoding='utf-8')

    def save_indicator_data(self, sheet_name: str, df: pd.DataFrame):
        """Salva dados de indicadores processados em CSV"""
        output_path = self.indicadores_dir / f'{sheet_name.lower().replace(" ", "_")}.csv'
        df.to_csv(output_path, index=False, encoding='utf-8')
        

    def import_regions_and_cities(self):
        """Importa dados de cidades e regiões de saúde"""
        try:
            df_indicador = pd.read_csv(self.indicadores_dir / 'indicador_3.csv')
            
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
            
            df_cidades = pd.read_csv(self.data_dir / 'municipios.csv')
            for _, row in df_cidades.iterrows():
                codigo_ibge = row['codigo_ibge']
                codigo_ibge_sem_digito = str(codigo_ibge)[:-1]
                
                regiao_saude = cidade_regiao_map.get(codigo_ibge_sem_digito)
                if regiao_saude:
                    Cidade.objects.get_or_create(
                        codigo_ibge=str(codigo_ibge),
                        defaults={
                            'nome': row['nome'],
                            'latitude': row['latitude'],
                            'longitude': row['longitude'],
                            'regiao_saude': regiao_saude
                        }
                    )
            
            self.logger.info("Cidades e regiões importadas com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao importar cidades e regiões: {str(e)}")
            raise

    def import_indicators(self):
        """Importa metadados dos indicadores"""
        try:
            df = pd.read_csv(self.data_dir / 'titulo_subtitulo.csv')
            
            for _, row in df.iterrows():
                Indicador.objects.get_or_create(
                    nome_arquivo=row['nome_arquivo'],
                    defaults={
                        'titulo': row['titulo'],
                        'subtitulo': row['subtitulo'],
                        'fonte': row['fonte']
                    }
                )
            
            self.logger.info("Metadados dos indicadores importados com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao importar metadados dos indicadores: {str(e)}")
            raise

    def import_indicator_values(self):
        """Importa valores dos indicadores"""
        try:
            indicator_files = list(self.indicadores_dir.glob('indicador_*.csv'))
            
            for file_path in indicator_files:
                indicador_nome = file_path.stem
                df = pd.read_csv(file_path)
                
                try:
                    indicador = Indicador.objects.get(nome_arquivo=indicador_nome)
                except Indicador.DoesNotExist:
                    self.logger.warning(f"Indicador não encontrado: {indicador_nome}")
                    continue
                
                for _, row in df.iterrows():
                    codigo_ibge = str(row['Cod. IBGE'])
                    try:
                        cidade = Cidade.objects.get(codigo_ibge__startswith=codigo_ibge)
                        
                        for ano in range(2010, 2021):
                            ano_str = str(ano)
                            if ano_str in df.columns:
                                valor = self.clean_numeric_value(row[ano_str])
                                if valor is not None:
                                    ValorIndicador.objects.get_or_create(
                                        cidade=cidade,
                                        indicador=indicador,
                                        ano=ano,
                                        defaults={'valor': valor}
                                    )
                                    
                    except Cidade.DoesNotExist:
                        self.logger.warning(f"Cidade não encontrada para o código IBGE: {codigo_ibge}")
                        continue
            
            self.logger.info("Valores dos indicadores importados com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao importar valores dos indicadores: {str(e)}")
            raise

def run_etl():
    """Executa o processo ETL"""
    etl = HealthDataETL()
    xlsx_path = 'assets/data/serie_historica.xlsx'
    etl.process_excel_file(xlsx_path)

if __name__ == "__main__":
    run_etl()