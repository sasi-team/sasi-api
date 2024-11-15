import pandas as pd
import folium
from folium.plugins import HeatMap

# Função para criar o mapa de calor
def create_heatmap(year):
    # Carregar os dados dos indicadores
    df_indicador_3 = pd.read_csv('./assets/indicadores/indicador_3.csv')

    # Carregar os dados de coordenadas das cidades
    df_coords = pd.read_csv('coordenadas_cidades.csv')

    # Verificar se as colunas necessárias estão presentes
    required_columns = ['Cod. IBGE', 'Município', str(year)]
    if not all(col in df_indicador_3.columns for col in required_columns):
        raise ValueError(f"Colunas necessárias ausentes em df_indicador_3: {required_columns}")

    required_columns_coords = ['codigo_ibge', 'latitude', 'longitude']
    if not all(col in df_coords.columns for col in required_columns_coords):
        raise ValueError(f"Colunas necessárias ausentes em df_coords: {required_columns_coords}")

    # Ajustar o código IBGE da tabela de coordenadas para remover o último dígito
    df_coords['codigo_ibge'] = df_coords['codigo_ibge'].astype(str).str[:-1].astype(int)

    # Converter a coluna 'Cod. IBGE' para inteiro
    df_indicador_3['Cod. IBGE'] = df_indicador_3['Cod. IBGE'].astype(int)

    # Mesclar os dados dos indicadores com as coordenadas das cidades
    df_merged = pd.merge(df_indicador_3, df_coords, left_on='Cod. IBGE', right_on='codigo_ibge')

    # Verificar se a mesclagem foi bem-sucedida
    if df_merged.empty:
        raise ValueError("A mesclagem dos dados resultou em um DataFrame vazio. Verifique os dados de entrada.")

    # Criar um mapa centrado na Bahia
    map_bahia = folium.Map(location=[-12.9704, -38.5124], zoom_start=6)

    # Criar uma lista de pontos de calor
    heat_data = [[row['latitude'], row['longitude'], row[str(year)]] for _, row in df_merged.iterrows() if pd.notna(row['latitude']) and pd.notna(row['longitude'])]

    # Adicionar a camada de mapa de calor
    HeatMap(heat_data).add_to(map_bahia)

    # Salvar o mapa em um arquivo HTML
    map_bahia.save(f'mapa_indicadores_{year}.html')

# Solicitar o ano ao usuário
year = input("Digite o ano para exibir o mapa de calor (2010-2020): ")
create_heatmap(year)
