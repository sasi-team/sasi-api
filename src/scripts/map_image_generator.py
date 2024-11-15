import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import json
import re
import os
import textwrap
import matplotlib.patches as patches
import argparse
from constants import GEOJSON_PATH, TITULO_SUBTITULO_CSV_PATH

# Definição dos anos e indicadores
anos = [
    "2010",
    "2011",
    "2012",
    "2013",
    "2014",
    "2015",
    "2016",
    "2017",
    "2018",
    "2019",
    "2020",
]

indicadores_dic = {
    "indicador_3":  { "prefix_meta": " ", "sufix_meta": "%", "invert_color_scale": False },
    "indicador_5":  { "prefix_meta": "  ", "sufix_meta": "%", "invert_color_scale": False },
    "indicador_6": { "prefix_meta": "  ", "sufix_meta": "%", "invert_color_scale": False }, 
    "indicador_8":{ "prefix_meta": "Redução de ", "sufix_meta": "%", "invert_color_scale": True },
    "indicador_9":{ "prefix_meta": "  ", "sufix_meta": "%", "invert_color_scale": True },
    "Indicador_13": { "prefix_meta": "  ", "sufix_meta": "%", "invert_color_scale": False },
    "Indicador_14": { "prefix_meta": "  ", "sufix_meta": "%", "invert_color_scale": True },
    "Indicador_15": { "prefix_meta": "  ", "sufix_meta": "%", "invert_color_scale": True },
    "Indicador_16": { "prefix_meta": "  ", "sufix_meta": "%", "invert_color_scale": True },
    "indicador_23": { "prefix_meta": "  ", "sufix_meta": "%", "invert_color_scale": False },
}

# Função para mapear um valor para uma cor em um gradiente
def color_gradient_picker(valor, min_val=0, max_val=100, invert=False):
    norm = mcolors.Normalize(vmin=min_val, vmax=max_val)
    cmap =plt.colormaps.get_cmap("RdYlGn")
    
    if invert:
        cmap = cmap.reversed()
    
    rgba_color = cmap(norm(valor))
    hex_color = mcolors.rgb2hex(rgba_color)
    return hex_color

# Função para buscar o valor do indicador com base no ano e no código IBGE
def get_indicator_value(df, codigo_ibge, ano):
    ano = ano.rstrip('*')
    if len(str(codigo_ibge)) > 6:
        codigo_ibge = str(codigo_ibge)[:-1]        
    
    try:
        # Verificar se o código IBGE está no DataFrame
        if codigo_ibge in df['Cod. IBGE'].values:
            # Verificar se o ano está no DataFrame
            if ano in df.columns:
                valor = df[df['Cod. IBGE'] == codigo_ibge][ano].values[0]
            else:
                # print(f"Ano {ano} não encontrado no DataFrame.")
                valor = 0
        else:
            # print(f"Código IBGE {codigo_ibge} não encontrado no DataFrame.")
            valor = 0
    except Exception as e:
        print(f"Erro ao buscar valor para código IBGE {codigo_ibge} e ano {ano}: {e}")
        valor = 0
    
    return valor

# Função para extrair o valor da meta
def extract_meta_value(meta_text):
    match = re.search(r'(\d+(\.\d+)?)(?=%|)', meta_text)
    if match:
        return float(match.group(1))
    match = re.search(r'Redução\s*(\d+(\.\d+)?)%', meta_text)
    if match:
        return float(match.group(1))
    match = re.search(r'Meta Estadual:\s*(\d+(\.\d+)?)%', meta_text)
    if match:
        return float(match.group(1))
    match = re.search(r'Meta Estadual:\s*(\d+(\.\d+)?)', meta_text)
    if match:
        return float(match.group(1))
    return 0

# Função para carregar dados do GeoJSON
def load_geojson(geojson_path):
    with open(geojson_path, "r", encoding="utf-8") as file:
        geojson_data = json.load(file)
    return geojson_data

# Função para carregar dados do CSV
def load_csv_data(csv_path):
    return pd.read_csv(csv_path)

# Função para ajustar o código IBGE
def adjust_cod_ibge(df):
    df["Cod. IBGE"] = df["Cod. IBGE"].astype(str)
    return df

# Função para criar o GeoDataFrame
def create_geodataframe(geojson_data):
    return gpd.GeoDataFrame.from_features(geojson_data["features"])

# Função para adicionar valores dos indicadores ao GeoDataFrame
def add_indicator_values(gdf, df_indicador, ano):
    gdf["valor"] = gdf["id"].apply(lambda x: get_indicator_value(df_indicador, x, ano))
    gdf['valor'] = pd.to_numeric(gdf['valor'], errors='coerce').fillna(0)
    return gdf

# Função para obter valores mínimos e máximos
def get_max_min_values(df, year):
    year = year.rstrip('*')
    min_val = df[year].min()
    max_val = df[year].max()
    return min_val, max_val

# Função para criar o mapa
def create_map(gdf, min_val, max_val, meta_estadual_valor, titulo, ano, fonte, prefix_meta, sufix_meta, indicador, invert_colors=False):
    fig, ax = plt.subplots(1, 1, figsize=(15, 15))
    gdf.boundary.plot(ax=ax, linewidth=1)
    
    # Colorir os municípios com base nos valores dos indicadores
    gdf["color"] = gdf["valor"].apply(lambda x: color_gradient_picker(x, min_val, max_val, invert=invert_colors))
    gdf.plot(ax=ax, color=gdf["color"])
    
    # Adicionar a legenda
    cmap = plt.colormaps.get_cmap("RdYlGn")
    if invert_colors:
        cmap = cmap.reversed()
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=min_val, vmax=max_val))
    sm._A = []
    cbar = fig.colorbar(sm, ax=ax, shrink=0.5, aspect=10, pad=0.02)
    cbar.set_label("Valor do Indicador", fontsize=12)
    
    # Adicionar a meta na barra de cores
    meta_norm = (meta_estadual_valor - min_val) / (max_val - min_val)
    cbar.ax.axhline(meta_norm, color="blue", linewidth=4)
    cbar.ax.add_patch(patches.Rectangle((1.05, meta_norm - 0.02), 0.05, 0.04, color="blue", transform=cbar.ax.transAxes, clip_on=False))
    
    # Adicionar o título e a meta
    wrapped_title = textwrap.fill(f"Mapa de Indicadores de Saúde - Bahia \n {titulo} \n Ano: {ano}", width=60)
    plt.title(wrapped_title, fontsize=16)
    plt.text(
        0.5,
        -0.1,
        f"{prefix_meta}Meta Estadual: {meta_estadual_valor} {sufix_meta}",
        ha="center",
        va="center",
        transform=ax.transAxes,
        fontsize=12,
    )
    plt.text(
        0.5,
        -0.15,
        f"Fonte: {fonte} \n Processamento: SASI - 2024",
        ha="center",
        va="center",
        transform=ax.transAxes,
        fontsize=10,
    )
    
    # Salvar o mapa como uma imagem
    plt.savefig(f"imagens/mapa_bahia_{indicador}_{ano}.png", dpi=300, bbox_inches="tight")

# Função principal para gerar o mapa
def generate_map(geojson_path, indicador_csv_path, titulo_subtitulo_csv_path, ano, indicador, prefix_meta, sufix_meta, invert_colors=False):
    try:
        # Carregar dados
        geojson_data = load_geojson(geojson_path)
        df_indicador = load_csv_data(indicador_csv_path)
        df_titulo_subtitulo = load_csv_data(titulo_subtitulo_csv_path).fillna("")
        
        # Extrair título e meta estadual
        titulo = df_titulo_subtitulo[df_titulo_subtitulo["nome_arquivo"] == indicador]["titulo"].values[0]
        meta_estadual = df_titulo_subtitulo[df_titulo_subtitulo["nome_arquivo"] == indicador]["subtitulo"].values[0]
        fonte = df_titulo_subtitulo[df_titulo_subtitulo["nome_arquivo"] == indicador]["fonte"].values[0]
        meta_estadual_valor = float(extract_meta_value(meta_estadual))
        print(f"Meta Estadual do Indicador : {meta_estadual_valor}")
        
        # Ajustar o código IBGE
        df_indicador = adjust_cod_ibge(df_indicador)
        
        # Criar o GeoDataFrame
        gdf = create_geodataframe(geojson_data)
        
        # Adicionar valores dos indicadores ao GeoDataFrame
        gdf = add_indicator_values(gdf, df_indicador, ano)
        
        # Obter valores mínimos e máximos
        min_val, max_val = get_max_min_values(df_indicador, ano)
        min_val = float(min_val)
        max_val = float(max_val)
        
        print(f"Valor mínimo: {min_val}")
        print(f"Valor máximo: {max_val}")
        
        # Criar o mapa
        create_map(gdf, min_val, max_val, meta_estadual_valor, titulo, ano, fonte, prefix_meta, sufix_meta, indicador, invert_colors)
    except Exception as e:
        print(f"Erro ao gerar o mapa para o indicador {indicador} no ano {ano}: {e}")

# Parâmetros
geojson_path = GEOJSON_PATH
titulo_subtitulo_csv_path = TITULO_SUBTITULO_CSV_PATH

# Configurar argparse
parser = argparse.ArgumentParser(description="Gerar mapas de indicadores de saúde.")
parser.add_argument("--indicador", type=str, help="Nome do indicador para gerar o mapa. Se não for especificado, gera todos os indicadores.")
args = parser.parse_args()

# Gerar mapas para todos os indicadores e anos ou para um indicador específico
if args.indicador:
    if args.indicador in indicadores_dic:
        for ano in anos:
            indicador_csv_path = f"assets/indicadores/{args.indicador}.csv"
            params = indicadores_dic[args.indicador]
            generate_map(
                geojson_path,
                indicador_csv_path,
                titulo_subtitulo_csv_path,
                ano,
                args.indicador,
                params["prefix_meta"],
                params["sufix_meta"],
                params["invert_color_scale"]
            )
    else:
        print(f"Indicador {args.indicador} não encontrado.")
else:
    for ano in anos:
        for indicador, params in indicadores_dic.items():
            indicador_csv_path = f"assets/indicadores/{indicador}.csv"
            generate_map(
                geojson_path,
                indicador_csv_path,
                titulo_subtitulo_csv_path,
                ano,
                indicador,
                params["prefix_meta"],
                params["sufix_meta"],
                params["invert_color_scale"]
            )