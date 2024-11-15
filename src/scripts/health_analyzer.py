import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import List, Dict, Optional
import warnings
warnings.filterwarnings('ignore')

class HealthDataAnalyzer:
    def __init__(self, excel_path: str):
        """
        Inicializa o analisador com o caminho do arquivo Excel.
        
        Args:
            excel_path: Caminho para o arquivo Excel
        """
        self.excel_path = excel_path
        self.sheets = pd.ExcelFile(excel_path).sheet_names
        
    def load_sheet(self, sheet_name: str, skip_rows: int = 1) -> pd.DataFrame:
        """
        Carrega uma aba específica do Excel com tratamento básico.
        
        Args:
            sheet_name: Nome da aba
            skip_rows: Número de linhas para pular
        """
        df = pd.read_excel(self.excel_path, sheet_name=sheet_name, skiprows=skip_rows)
        
        # Remove linhas que são totalmente NaN e linhas de notas
        df = df.dropna(how='all')
        if 'Macrorregião de Saúde' in df.columns:
            df = df[~df['Macrorregião de Saúde'].astype(str).str.contains('NOTAS:|\\*', na=False, regex=True)]
        
        return df
    
    def get_data_quality_report(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Gera um relatório de qualidade dos dados.
        
        Args:
            df: DataFrame a ser analisado
        """
        quality_report = pd.DataFrame({
            'tipo': df.dtypes,
            'nulos': df.isnull().sum(),
            'nulos_pct': (df.isnull().sum() / len(df) * 100).round(2),
            'únicos': df.nunique(),
            'exemplo': df.iloc[0]
        })
        return quality_report
    
    def analyze_time_series(self, df: pd.DataFrame, start_year: int = 2010, end_year: int = 2020) -> Dict:
        """
        Analisa a série temporal dos indicadores.
        
        Args:
            df: DataFrame com os dados
            start_year: Ano inicial
            end_year: Ano final
        """
        years = list(range(start_year, end_year + 1))
        year_columns = [str(year) for year in years if str(year) in df.columns]
        
        if not year_columns:
            raise ValueError("Nenhuma coluna de ano encontrada no DataFrame para o intervalo especificado.")
        
        # Estatísticas básicas por ano
        yearly_stats = df[year_columns].agg(['mean', 'median', 'std', 'min', 'max']).round(2)
        
        # Variação percentual ano a ano
        yearly_variation = df[year_columns].pct_change(axis=1).mean().round(4) * 100
        
        return {
            'estatisticas_anuais': yearly_stats,
            'variacao_percentual': yearly_variation
        }
    
    def plot_regional_comparison(self, df: pd.DataFrame, year: str, 
                               region_column: str = 'Macrorregião de Saúde',
                               figsize: tuple = (12, 6)):
        """
        Plota comparação entre regiões para um ano específico.
        
        Args:
            df: DataFrame com os dados
            year: Ano para análise
            region_column: Coluna com as regiões
            figsize: Tamanho da figura
        """
        plt.figure(figsize=figsize)
        
        regional_means = df.groupby(region_column)[str(year)].mean().sort_values(ascending=True)
        
        sns.barplot(x=regional_means.values, y=regional_means.index)
        plt.title(f'Média do Indicador por Região - {year}')
        plt.xlabel('Valor Médio')
        plt.tight_layout()
        plt.show()
        
        return regional_means
    
    def identify_outliers(self, df: pd.DataFrame, year: str, 
                         region_column: str = 'Macrorregião de Saúde') -> pd.DataFrame:
        """
        Identifica outliers nos dados usando o método IQR.
        
        Args:
            df: DataFrame com os dados
            year: Ano para análise
            region_column: Coluna com as regiões
        """
        def get_outliers(group):
            q1 = group[year].quantile(0.25)
            q3 = group[year].quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            return group[(group[year] < lower_bound) | (group[year] > upper_bound)]
        
        outliers = df.groupby(region_column).apply(get_outliers)
        return outliers.reset_index(drop=True)
    
    def trend_analysis(self, df: pd.DataFrame, municipio: str,
                      start_year: int = 2010, end_year: int = 2020,
                      plot: bool = True) -> Dict:
        """
        Analisa a tendência temporal para um município específico.
        
        Args:
            df: DataFrame com os dados
            municipio: Nome do município
            start_year: Ano inicial
            end_year: Ano final
            plot: Se deve gerar o gráfico
        """
        years = list(range(start_year, end_year + 1))
        year_columns = [str(year) for year in years]
        
        mun_data = df[df['Município'] == municipio][year_columns].iloc[0]
        
        if plot:
            plt.figure(figsize=(10, 5))
            plt.plot(years, mun_data.values, marker='o')
            plt.title(f'Tendência do Indicador - {municipio}')
            plt.xlabel('Ano')
            plt.ylabel('Valor')
            plt.grid(True)
            plt.show()
        
        # Calcula estatísticas de tendência
        trend_stats = {
            'variacao_total': ((mun_data.iloc[-1] / mun_data.iloc[0] - 1) * 100).round(2),
            'media': mun_data.mean().round(2),
            'tendencia': 'crescente' if mun_data.iloc[-1] > mun_data.iloc[0] else 'decrescente',
            'valor_inicial': mun_data.iloc[0],
            'valor_final': mun_data.iloc[-1]
        }
        
        return trend_stats
    
    def generate_summary_report(self, df: pd.DataFrame, year: str) -> pd.DataFrame:
        """
        Gera um relatório resumido com os principais indicadores por região.
        
        Args:
            df: DataFrame com os dados
            year: Ano para análise
        """
        summary = df.groupby('Macrorregião de Saúde').agg({
            'Município': 'count',
            str(year): ['mean', 'median', 'std', 'min', 'max']
        }).round(2)
        
        summary.columns = ['n_municipios', 'media', 'mediana', 'desvio_padrao', 'minimo', 'maximo']
        return summary
    
    def find_missing_data_patterns(self, df: pd.DataFrame, 
                                 start_year: int = 2010, 
                                 end_year: int = 2020) -> pd.DataFrame:
        """
        Identifica padrões de dados faltantes ao longo dos anos.
        
        Args:
            df: DataFrame com os dados
            start_year: Ano inicial
            end_year: Ano final
        """
        years = list(range(start_year, end_year + 1))
        year_columns = [str(year) for year in years]
        
        missing_patterns = df[year_columns].isnull().sum()
        missing_patterns = pd.DataFrame({
            'ano': missing_patterns.index,
            'registros_faltantes': missing_patterns.values,
            'percentual_faltante': (missing_patterns.values / len(df) * 100).round(2)
        })
        
        return missing_patterns.sort_values('registros_faltantes', ascending=False)

# Exemplo de uso
if __name__ == "__main__":
    # Inicialização
    analyzer = HealthDataAnalyzer('data/serie_historica.xlsx')
    
    # Carregando uma aba específica
    df = analyzer.load_sheet('Indicador 1')
    
    # Relatório de qualidade dos dados
    quality_report = analyzer.get_data_quality_report(df)
    print("\nRelatório de Qualidade dos Dados:")
    print(quality_report)
    
    # Análise temporal
    time_analysis = analyzer.analyze_time_series(df)
    print("\nAnálise Temporal:")
    print(time_analysis['estatisticas_anuais'])
    
    # Identificação de outliers
    outliers = analyzer.identify_outliers(df, '2020')
    print("\nOutliers identificados para 2020:")
    print(outliers)
    
    # Análise de tendência para um município específico
    trend = analyzer.trend_analysis(df, "Salvador")
    print("\nAnálise de Tendência - Salvador:")
    print(trend)