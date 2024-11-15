import pandas as pd
import numpy as np
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass
import json
from collections import defaultdict

@dataclass
class SheetStructure:
    """Classe para armazenar informações estruturais de cada aba"""
    sheet_name: str
    header_rows: int
    column_count: int
    row_count: int
    column_names: List[str]
    column_types: Dict[str, str]
    has_meta: bool
    has_notes: bool
    year_columns: List[str]
    unique_values_by_column: Dict[str, Set]
    missing_patterns: Dict[str, float]
    
    def to_dict(self):
        """Converte a estrutura para dicionário, convertendo sets para listas"""
        result = self.__dict__.copy()
        result['unique_values_by_column'] = {
            k: list(v) if isinstance(v, set) else v 
            for k, v in self.unique_values_by_column.items()
        }
        return result

class ExcelStructureAnalyzer:
    def __init__(self, excel_path: str):
        """
        Inicializa o analisador com o caminho do arquivo Excel.
        
        Args:
            excel_path: Caminho para o arquivo Excel
        """
        self.excel_path = excel_path
        self.excel = pd.ExcelFile(excel_path)
        self.sheet_names = self.excel.sheet_names
        self.structures = {}
        
    def detect_header_rows(self, df: pd.DataFrame) -> int:
        """
        Detecta quantas linhas fazem parte do cabeçalho.
        
        Args:
            df: DataFrame a ser analisado
        Returns:
            Número de linhas do cabeçalho
        """
        # Verifica se há linhas com "Meta" ou outros indicadores de cabeçalho
        header_rows = 0
        for idx, row in df.iterrows():
            if any(str(val).startswith(('Meta', 'Indicador', 'Fonte')) for val in row):
                header_rows = idx + 1
        return max(1, header_rows)
    
    def detect_year_columns(self, df: pd.DataFrame) -> List[str]:
        """
        Identifica colunas que representam anos.
        
        Args:
            df: DataFrame a ser analisado
        Returns:
            Lista de colunas que representam anos
        """
        year_columns = []
        for col in df.columns:
            # Verifica diferentes formatos de anos nas colunas
            col_str = str(col)
            if col_str.isdigit() and 1990 <= int(col_str) <= 2030:
                year_columns.append(col)
            elif any(str(val).isdigit() and 1990 <= int(str(val)) <= 2030 
                    for val in df[col].dropna().astype(str)):
                year_columns.append(col)
        return year_columns
    
    def analyze_sheet(self, sheet_name: str) -> SheetStructure:
        """
        Analisa a estrutura de uma aba específica.
        
        Args:
            sheet_name: Nome da aba a ser analisada
        Returns:
            Estrutura da aba
        """
        # Lê os primeiros registros para análise inicial
        df_preview = pd.read_excel(self.excel_path, sheet_name=sheet_name, nrows=5)
        header_rows = self.detect_header_rows(df_preview)
        
        # Lê a planilha completa pulando as linhas de cabeçalho identificadas
        df = pd.read_excel(self.excel_path, sheet_name=sheet_name, skiprows=header_rows-1)
        
        # Remove linhas que são totalmente nulas
        df = df.dropna(how='all')
        
        # Detecta se há notas no final
        has_notes = any(str(val).startswith(('*', 'NOTA', 'Fonte')) 
                       for val in df.iloc[-5:].values.flatten())
        
        # Identifica colunas de anos
        year_columns = self.detect_year_columns(df)
        
        # Analisa valores únicos (limitando para não sobrecarregar a memória)
        unique_values = {}
        for col in df.columns:
            unique_vals = set(df[col].dropna().unique()[:10])  # Limita a 10 valores únicos
            unique_values[str(col)] = unique_vals
            
        # Analisa padrões de dados faltantes
        missing_patterns = {
            str(col): (df[col].isnull().sum() / len(df) * 100)
            for col in df.columns
        }
        
        return SheetStructure(
            sheet_name=sheet_name,
            header_rows=header_rows,
            column_count=len(df.columns),
            row_count=len(df),
            column_names=list(df.columns),
            column_types={str(col): str(dtype) for col, dtype in df.dtypes.items()},
            has_meta=any('Meta' in str(val) for val in df_preview.values.flatten()),
            has_notes=has_notes,
            year_columns=year_columns,
            unique_values_by_column=unique_values,
            missing_patterns=missing_patterns
        )
    
    def analyze_all_sheets(self) -> Dict[str, SheetStructure]:
        """
        Analisa todas as abas do Excel.
        
        Returns:
            Dicionário com as estruturas de todas as abas
        """
        for sheet_name in self.sheet_names:
            print(f"Analisando aba: {sheet_name}")
            self.structures[sheet_name] = self.analyze_sheet(sheet_name)
        return self.structures
    
    def compare_structures(self) -> Dict:
        """
        Compara as estruturas entre as diferentes abas.
        
        Returns:
            Dicionário com as diferenças encontradas
        """
        if not self.structures:
            self.analyze_all_sheets()
            
        comparison = {
            'header_variations': defaultdict(list),
            'column_count_variations': defaultdict(list),
            'year_column_variations': defaultdict(list),
            'common_columns': set.intersection(*[
                set(s.column_names) for s in self.structures.values()
            ]),
            'all_columns': set.union(*[
                set(s.column_names) for s in self.structures.values()
            ]),
            'type_variations': defaultdict(dict)
        }
        
        # Analisa variações
        for sheet_name, structure in self.structures.items():
            comparison['header_variations'][structure.header_rows].append(sheet_name)
            comparison['column_count_variations'][structure.column_count].append(sheet_name)
            comparison['year_column_variations'][tuple(structure.year_columns)].append(sheet_name)
            
            # Analisa variações de tipo por coluna
            for col in structure.column_names:
                col_type = structure.column_types.get(str(col))
                if col not in comparison['type_variations']:
                    comparison['type_variations'][col] = defaultdict(list)
                comparison['type_variations'][col][col_type].append(sheet_name)
        
        # Converte defaultdicts para dicts normais para melhor visualização
        comparison = {k: dict(v) if isinstance(v, defaultdict) else v 
                     for k, v in comparison.items()}
        
        return comparison
    
    def generate_report(self) -> str:
        """
        Gera um relatório detalhado das análises.
        
        Returns:
            Relatório formatado em string
        """
        if not self.structures:
            self.analyze_all_sheets()
            
        comparison = self.compare_structures()
        
        report = ["=== Relatório de Análise Estrutural das Planilhas ===\n"]
        
        # Resumo geral
        report.append(f"Total de abas analisadas: {len(self.structures)}\n")
        
        # Variações de cabeçalho
        report.append("\n=== Variações de Cabeçalho ===")
        for rows, sheets in comparison['header_variations'].items():
            report.append(f"\n{len(sheets)} abas com {rows} linhas de cabeçalho:")
            report.append(f"  Abas: {', '.join(sheets)}")
            
        # Variações de colunas
        report.append("\n\n=== Variações de Número de Colunas ===")
        for count, sheets in comparison['column_count_variations'].items():
            report.append(f"\n{len(sheets)} abas com {count} colunas:")
            report.append(f"  Abas: {', '.join(sheets)}")
            
        # Colunas comuns
        report.append("\n\n=== Colunas Comuns a Todas as Abas ===")
        for col in sorted(comparison['common_columns']):
            report.append(f"  - {col}")
            
        # Variações de tipo por coluna
        report.append("\n\n=== Variações de Tipo por Coluna ===")
        for col, types in comparison['type_variations'].items():
            if len(types) > 1:  # Só mostra se houver variação
                report.append(f"\nColuna: {col}")
                for dtype, sheets in types.items():
                    report.append(f"  - Tipo {dtype} em {len(sheets)} abas")
        
        return "\n".join(report)
    
    def save_analysis(self, output_path: str):
        """
        Salva a análise completa em um arquivo JSON.
        
        Args:
            output_path: Caminho para salvar o arquivo JSON
        """
        if not self.structures:
            self.analyze_all_sheets()
            
        analysis = {
            'structures': {
                name: structure.to_dict() 
                for name, structure in self.structures.items()
            },
            'comparison': self.compare_structures()
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)

# Exemplo de uso
if __name__ == "__main__":
    analyzer = ExcelStructureAnalyzer('data/serie_historica.xlsx')
    
    # Analisa todas as abas
    structures = analyzer.analyze_all_sheets()
    
    # Gera e imprime o relatório
    report = analyzer.generate_report()
    print(report)
    
    # Salva a análise completa
    analyzer.save_analysis('analise_estrutural.json')