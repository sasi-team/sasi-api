import pandas as pd
import re
import csv

# Função para limpar conteúdo de células
def clean_cell_content(cell):
    if pd.isna(cell):
        return None
    cell = str(cell)
    cell = re.sub(r',+$', '', cell)
    cell = cell.replace('"', '"').replace('"', '"').replace("'", '"')
    cell = ' '.join(cell.split())
    return cell

# Função para extrair a fonte do texto usando regex
def extract_source(text):
    if pd.isna(text):
        return None
    text = clean_cell_content(text)
    if not text:
        return None

    patterns = [
        r'(?i)Fonte:\s*(.*?)(?:$|\.{2,})',
        r'(?i)Fonte:\s*([^\.]+\.[^\.]+)',
        r'(?i)Fonte:\s*(.+)'
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return clean_cell_content(match.group(1).strip())

    return None

def is_valid_indicador_name(name):
    return re.match(r'^nome_\d+$', name) is not None

# Função para processar o arquivo Excel e extrair título, subtítulo e fonte
def process_excel_file(xlsx_file):
    sheet_names = pd.read_excel(xlsx_file, sheet_name=None, header=None)
    df_titulo = pd.DataFrame(columns=['nome_arquivo', 'titulo', 'subtitulo', 'fonte'])

    for sheet_name, df in sheet_names.items():
        safe_sheet_name = sheet_name.replace(" ", "_").replace("/", "_")
        if not is_valid_indicador_name(safe_sheet_name):
            continue
        titulo = clean_cell_content(df.iloc[0, 0])
        subtitulo = clean_cell_content(df.iloc[1, 0])

        source_info = None
        for i in range(min(10, len(df))):
            if isinstance(df.iloc[-(i+1), 0], str):
                potential_source = extract_source(df.iloc[-(i+1), 0])
                if potential_source:
                    source_info = potential_source
                    break

        new_row = pd.DataFrame([{
            'nome_arquivo': safe_sheet_name,
            'titulo': titulo,
            'subtitulo': subtitulo,
            'fonte': source_info
        }])

        df_titulo = pd.concat([df_titulo, new_row], ignore_index=True)

    df_titulo.to_csv('assets/data/titulo_subtitulo.csv', index=False, encoding='utf-8', quotechar='"', quoting=csv.QUOTE_ALL)
    return df_titulo

# Função para salvar cada aba do Excel em arquivos CSV individuais
def save_sheets_to_csv(xlsx_file):
    sheets = pd.read_excel(xlsx_file, sheet_name=None, header=2)  # Define a linha 3 como cabeçalho
    for sheet_name, df in sheets.items():
        safe_sheet_name = sheet_name.replace(" ", "_").replace("/", "_")
        if not is_valid_indicador_name(safe_sheet_name):
            continue
        
        # Verificar se as colunas críticas estão presentes
        critical_columns = ['Macrorregião de Saúde', 'Região de Saúde', 'Cod. IBGE', 'Município']
        if all(col in df.columns for col in critical_columns):
            # Limpar registros que não tenham informações nas colunas críticas
            df.dropna(subset=critical_columns, inplace=True)
            # Converter a coluna 'Cod. IBGE' para inteiro
            df['Cod. IBGE'] = df['Cod. IBGE'].astype(int)
        else:
            print(f"Aba {sheet_name} não contém todas as colunas críticas.")
        
        output_file = f'./assets/indicadores/{safe_sheet_name}.csv'
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f'Aba {sheet_name} salva em {output_file}')

# Uso do script
if __name__ == "__main__":
    xlsx_file = './assets/data/serie_historica.xlsx'
    
    # Processa o arquivo e gera o CSV com títulos e fontes
    resultado = process_excel_file(xlsx_file)
    print(resultado)
    
    # Salva as abas do Excel como arquivos CSV
    save_sheets_to_csv(xlsx_file)
