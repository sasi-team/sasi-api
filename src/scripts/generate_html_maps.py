import pandas as pd
import folium
import json
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import argparse
import re
from constants import GEOJSON_PATH, TITULO_SUBTITULO_CSV_PATH

# Definição dos anos e indicadores
anos = [
    "2010", "2011", "2012", "2013", "2014", "2015",
    "2016", "2017", "2018", "2019", "2020",
]

indicadores_dic = {
    "indicador_3": { "prefix_meta": " ", "sufix_meta": "%", "invert_color_scale": False },
    "indicador_5": { "prefix_meta": "  ", "sufix_meta": "%", "invert_color_scale": False },
    "indicador_6": { "prefix_meta": "  ", "sufix_meta": "%", "invert_color_scale": False },
    "indicador_9": { "prefix_meta": "  ", "sufix_meta": "%", "invert_color_scale": True },
    "Indicador_13": { "prefix_meta": "  ", "sufix_meta": "%", "invert_color_scale": False },
    "Indicador_14": { "prefix_meta": "  ", "sufix_meta": "%", "invert_color_scale": True },
    "Indicador_15": { "prefix_meta": "  ", "sufix_meta": "%", "invert_color_scale": True },
    "Indicador_16": { "prefix_meta": "  ", "sufix_meta": "%", "invert_color_scale": True },
    "indicador_23": { "prefix_meta": "  ", "sufix_meta": "%", "invert_color_scale": False },
}

def color_gradient_picker(valor, min_val=0, max_val=100, invert=False):
    norm = mcolors.Normalize(vmin=min_val, vmax=max_val)
    cmap = plt.get_cmap("RdYlGn")
    if invert:
        cmap = cmap.reversed()
    rgba_color = cmap(norm(valor))
    hex_color = mcolors.rgb2hex(rgba_color)
    return hex_color

def get_max_min_values(df, year):
    year = year.rstrip('*')
    min_val = df[year].min()
    max_val = df[year].max()
    return min_val, max_val

def get_indicator_value(df, codigo_ibge, ano):
    if len(str(codigo_ibge)) > 6:
        codigo_ibge = str(codigo_ibge)[:-1]
    try:
        if codigo_ibge in df['Cod. IBGE'].values:
            if ano in df.columns:
                valor = df[df['Cod. IBGE'] == codigo_ibge][ano].values[0]
            else:
                valor = 0
        else:
            valor = 0
    except Exception as e:
        print(f"Erro ao buscar valor para código IBGE {codigo_ibge} e ano {ano}: {e}")
        valor = 0
    return valor

def style_function(feature, df_indicador, min_val, max_val, ano, invert_colors):
    codigo_ibge = feature['properties']['id']
    valor = get_indicator_value(df_indicador, codigo_ibge, ano)
    fill_color = color_gradient_picker(valor, min_val, max_val, invert_colors)
    return {
        'fillColor': fill_color,
        'color': '#000000',
        'weight': 0.1,
        'fillOpacity': 0.7
    }

def highlight_function(feature):
    return {
        'fillOpacity': 0.9,
        'weight': 2,
        'color': '#000000'
    }

def add_title_and_info(map_obj, titulo, ano, fonte, meta_estadual_valor, prefix_meta, sufix_meta):
    title_html = f'''
    <div style="position: fixed; top: 10px; left: 50%;
                transform: translateX(-50%); z-index:9999;
                background-color: white; padding: 10px;
                border: 2px solid grey; border-radius: 5px;
                opacity: 0.9; text-align: center; max-width: 80%;">
        <h3 style="margin: 0;">Mapa de Indicadores de Saúde - Bahia</h3>
        <h4 style="margin: 10px 0;">{titulo}</h4>
        <p style="margin: 5px 0;">Ano: {ano}</p>
        <p style="margin: 5px 0;">{prefix_meta}Meta Estadual: {meta_estadual_valor}{sufix_meta}</p>
        <p style="margin: 5px 0; font-size: 0.9em;">Fonte: {fonte}</p>
        <p style="margin: 5px 0; font-size: 0.9em;">Processamento: SASI - 2024</p>
    </div>
    '''
    map_obj.get_root().html.add_child(folium.Element(title_html))

def add_custom_legend(map_obj, min_val, max_val, meta_estadual_valor):
    legend_html = f'''
    <div style="position: fixed; bottom: 50px; right: 50px; width: 200px;
                border: 2px solid grey; z-index:9999; background-color: white;
                padding: 10px; border-radius: 5px; opacity: 0.9;">
        <p style="margin-bottom:10px"><strong>Valor do Indicador (%)</strong></p>
        <div style="display: flex; align-items: center; margin-bottom:5px">
            <div style="background: #d73027; width: 20px; height: 20px; margin-right: 5px;"></div>
            <span>Mínimo: {min_val:.1f}</span>
        </div>
        <div style="display: flex; align-items: center; margin-bottom:5px">
            <div style="background: #fee08b; width: 20px; height: 20px; margin-right: 5px;"></div>
            <span>Médio: {(min_val + max_val)/2:.1f}</span>
        </div>
        <div style="display: flex; align-items: center; margin-bottom:5px">
            <div style="background: #1a9850; width: 20px; height: 20px; margin-right: 5px;"></div>
            <span>Máximo: {max_val:.1f}</span>
        </div>
        <div style="display: flex; align-items: center; margin-top:10px">
            <div style="background: blue; width: 20px; height: 3px; margin-right: 5px;"></div>
            <span>Meta: {meta_estadual_valor:.1f}%</span>
        </div>
    </div>
    '''
    map_obj.get_root().html.add_child(folium.Element(legend_html))

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

def generate_interactive_map(geojson_path, indicador_csv_path, titulo_subtitulo_csv_path, ano, indicador, prefix_meta, sufix_meta, invert_colors=False):
    try:
        # Carregar dados
        print("Carregando dados...")
        with open(geojson_path, 'r', encoding='utf-8') as file:
            geojson_data = json.load(file)
        
        df_indicador = pd.read_csv(indicador_csv_path)
        df_indicador['Cod. IBGE'] = df_indicador['Cod. IBGE'].astype(str)
        
        df_titulo_subtitulo = pd.read_csv(titulo_subtitulo_csv_path).fillna("")
        
        # Extrair informações
        titulo = df_titulo_subtitulo[df_titulo_subtitulo['nome_arquivo'] == indicador]['titulo'].values[0]
        fonte = df_titulo_subtitulo[df_titulo_subtitulo['nome_arquivo'] == indicador]['fonte'].values[0]
        meta_estadual = df_titulo_subtitulo[df_titulo_subtitulo['nome_arquivo'] == indicador]['subtitulo'].values[0]
        meta_estadual_valor = extract_meta_value(meta_estadual)
        
        print(f"Título: {titulo}")
        print(f"Fonte: {fonte}")
        print(f"Meta Estadual: {meta_estadual_valor}")
        
        # Criar mapa base
        mapa = folium.Map(location=[-12.5, -41.7], zoom_start=7)
        df_indicador = adjust_cod_ibge(df_indicador)

        # Obter valores min/max
        min_val, max_val = get_max_min_values(df_indicador, ano)
        
        print(f"Valor mínimo: {min_val}")
        print(f"Valor máximo: {max_val}")
        
        # Adicionar tooltips
        for feature in geojson_data['features']:
            codigo_ibge = feature['properties']['id']
            municipio = feature['properties']['name']
            valor = get_indicator_value(df_indicador, codigo_ibge, ano)
            feature['properties']['tooltip'] = (
            f"Município: {municipio}<br>"
            f"Código IBGE: {codigo_ibge}<br>"
            f"Valor do Indicador: {valor:.2f}%"
        )
    except Exception as e:
        print(f"Erro ao gerar mapa interativo: {e}")
        return None

    # Configurar tooltip
    tooltip = folium.GeoJsonTooltip(
        fields=['tooltip'],
        aliases=[''],
        localize=True,
        sticky=True,
        labels=False,
        style="""
            background-color: white;
            border: 2px solid black;
            border-radius: 3px;
            box-shadow: 3px;
            font-family: arial;
            font-size: 12px;
            padding: 10px;
        """,
        max_width=800
    )
    
    # Adicionar camada GeoJSON
    gjson = folium.GeoJson(
        geojson_data,
        style_function=lambda x: style_function(x, df_indicador, min_val, max_val, ano, invert_colors),
        highlight_function=highlight_function,
        tooltip=tooltip
    )
    gjson.add_to(mapa)
    
    # Adicionar título e legendas
    add_title_and_info(mapa, titulo, ano, fonte, meta_estadual_valor, prefix_meta, sufix_meta)
    add_custom_legend(mapa, min_val, max_val, meta_estadual_valor)
    
    # Salvar mapahtml
    output_path = f"assets/html/teste/mapa_bahia_{indicador}_{ano}.html"
    mapa.save(output_path)
    print(f"Mapa interativo gerado em: {output_path}")
    return output_path

# Função para limpar valores não numéricos
def clean_non_numeric_values(df):
    for col in df.columns:
        if col != "Cod. IBGE":
            df[col] = df[col].replace({
                '≥': '', 'Reduzir em': '', 'Proposto Escalonamento': '', 'e': '', ',': '.'
            }, regex=True)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

# Função para ajustar o código IBGE
def adjust_cod_ibge(df):
    df["Cod. IBGE"] = df["Cod. IBGE"].astype(str)
    df = clean_non_numeric_values(df)
    return df

# Função principal para gerar o mapa
def generate_map(geojson_path, indicador_csv_path, titulo_subtitulo_csv_path, ano, indicador, prefix_meta, sufix_meta, invert_colors=False):
    try:
        print("Iniciando geração do mapa...")
        output_path = generate_interactive_map(
            geojson_path=geojson_path,
            indicador_csv_path=indicador_csv_path,
            titulo_subtitulo_csv_path=titulo_subtitulo_csv_path,
            ano=ano,
            indicador=indicador,
            prefix_meta=prefix_meta,
            sufix_meta=sufix_meta,
            invert_colors=invert_colors
        )
        if output_path:
            print(f"Mapa gerado com sucesso em: {output_path}")
        else:
            print(f"Erro ao gerar o mapa para o indicador {indicador} no ano {ano}")
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
