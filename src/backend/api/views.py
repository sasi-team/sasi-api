from django.shortcuts import render
from django.http import JsonResponse
from django.views import View
import pandas as pd
import json
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import re

# Create your views here.

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


class GenerateMapView(View):
    def get(self, request, *args, **kwargs):
        indicador = request.GET.get('indicador')
        ano = request.GET.get('ano')
        if not indicador or not ano:
            return JsonResponse({'error': 'Indicador and ano are required parameters'}, status=400)
        
        if indicador not in indicadores_dic:
            return JsonResponse({'error': f'Indicador {indicador} not found'}, status=404)
        
        try:
            geojson_path = "../../assets/data/geojs-29-mun.json"
            indicador_csv_path = f"../../assets/indicadores/{indicador}.csv"
            titulo_subtitulo_csv_path = "../../assets/data/titulo_subtitulo.csv"
            params = indicadores_dic[indicador]
            
            # Carregar dados
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
            
            # Obter valores min/max
            min_val, max_val = get_max_min_values(df_indicador, ano)
            
            # Adicionar informações aos polígonos
            for feature in geojson_data['features']:
                codigo_ibge = feature['properties']['id']
                municipio = feature['properties']['name']
                valor = get_indicator_value(df_indicador, codigo_ibge, ano)
                fill_color = color_gradient_picker(valor, min_val, max_val, params["invert_color_scale"])
                feature['properties'].update({
                    'valor': valor,
                    'fillColor': fill_color,
                    'titulo': titulo,
                    'fonte': fonte,
                    'meta_estadual_valor': meta_estadual_valor,
                    'prefix_meta': params["prefix_meta"],
                    'sufix_meta': params["sufix_meta"]
                })
            
            return JsonResponse(geojson_data)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

class IndicatorsListView(View):
    def get(self, request, *args, **kwargs):
        try:
            titulo_subtitulo_csv_path = "../../assets/data/titulo_subtitulo.csv"
            df_titulo_subtitulo = pd.read_csv(titulo_subtitulo_csv_path).fillna("")
            indicators = df_titulo_subtitulo[['nome_arquivo', 'titulo']].to_dict(orient='records')
            return JsonResponse(indicators, safe=False)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

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


def color_gradient_picker(valor, min_val=0, max_val=100, invert=False):
    norm = mcolors.Normalize(vmin=min_val, vmax=max_val)
    cmap = plt.get_cmap("RdYlGn")
    if invert:
        cmap = cmap.reversed()
    rgba_color = cmap(norm(valor))
    hex_color = mcolors.rgb2hex(rgba_color)
    return hex_color
