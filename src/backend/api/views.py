from django.shortcuts import render
from django.http import JsonResponse
from django.views import View
from django.db import models
from .models import (
    Indicador,
    Cidade,
    MacroRegiao,
    RegiaoSaude,
    ValorIndicador,
    Estabelecimento,
    TipoUnidade,
)
import pandas as pd
import json
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import re
import requests
from rest_framework.views import APIView


indicadores_dic = {
    "indicador_3": {"prefix_meta": " ", "sufix_meta": "%", "invert_color_scale": False},
    "indicador_5": {
        "prefix_meta": "  ",
        "sufix_meta": "%",
        "invert_color_scale": False,
    },
    "indicador_6": {
        "prefix_meta": "  ",
        "sufix_meta": "%",
        "invert_color_scale": False,
    },
    "indicador_9": {"prefix_meta": "  ", "sufix_meta": "%", "invert_color_scale": True},
    "Indicador_13": {
        "prefix_meta": "  ",
        "sufix_meta": "%",
        "invert_color_scale": False,
    },
    "Indicador_14": {
        "prefix_meta": "  ",
        "sufix_meta": "%",
        "invert_color_scale": True,
    },
    "Indicador_15": {
        "prefix_meta": "  ",
        "sufix_meta": "%",
        "invert_color_scale": True,
    },
    "Indicador_16": {
        "prefix_meta": "  ",
        "sufix_meta": "%",
        "invert_color_scale": True,
    },
    "indicador_23": {
        "prefix_meta": "  ",
        "sufix_meta": "%",
        "invert_color_scale": False,
    },
}


def extract_meta_value(meta_text):
    match = re.search(r"(\d+(\.\d+)?)(?=%|)", meta_text)
    if match:
        return float(match.group(1))
    match = re.search(r"Redução\s*(\d+(\.\d+)?)%", meta_text)
    if match:
        return float(match.group(1))
    match = re.search(r"Meta Estadual:\s*(\d+(\.\d+)?)%", meta_text)
    if match:
        return float(match.group(1))
    match = re.search(r"Meta Estadual:\s*(\d+(\.\d+)?)", meta_text)
    if match:
        return float(match.group(1))
    return 0


class GenerateMapView(View):
    def get(self, request, *args, **kwargs):
        id_indicador = request.GET.get("id_indicador")
        ano = request.GET.get("ano")
        if not id_indicador or not ano:
            return JsonResponse(
                {"error": "Indicador and ano are required parameters"}, status=400
            )

        try:
            indicador_obj = Indicador.objects.get(id=id_indicador)
            if not indicadores_dic.get(indicador_obj.nome_arquivo):
                return JsonResponse(
                    {"error": f"Dados do indicador indisponíveis"}, status=404
                )
            valores_indicador = ValorIndicador.objects.filter(
                indicador=indicador_obj, ano=ano
            )
            if not valores_indicador.exists():
                return JsonResponse(
                    {
                        "error": f"No data found for indicador {id_indicador} and ano {ano}"
                    },
                    status=404,
                )

            geojson_path = "./assets/data/geojs-29-mun.json"
            params = indicadores_dic[indicador_obj.nome_arquivo]

            # Carregar dados
            with open(geojson_path, "r", encoding="utf-8") as file:
                geojson_data = json.load(file)

            titulo = indicador_obj.titulo
            fonte = indicador_obj.fonte
            meta_estadual = indicador_obj.subtitulo
            meta_estadual_valor = extract_meta_value(meta_estadual)

            # Obter valores min/max
            min_val = valores_indicador.aggregate(models.Min("valor"))["valor__min"]
            max_val = valores_indicador.aggregate(models.Max("valor"))["valor__max"]

            # Adicionar informações aos polígonos
            for feature in geojson_data["features"]:
                codigo_ibge = feature["properties"]["id"]
                municipio = feature["properties"]["name"]
                valor = valores_indicador.filter(
                    cidade__codigo_ibge=codigo_ibge
                ).first()
                valor = valor.valor if valor else 0
                fill_color = color_gradient_picker(
                    valor, min_val, max_val, params["invert_color_scale"]
                )
                feature["properties"].update(
                    {
                        "valor": valor,
                        "fillColor": fill_color,
                        "titulo": titulo,
                        "fonte": fonte,
                        "meta_estadual_valor": meta_estadual_valor,
                        "prefix_meta": params["prefix_meta"],
                        "sufix_meta": params["sufix_meta"],
                    }
                )

            return JsonResponse(geojson_data)
        except Indicador.DoesNotExist:
            return JsonResponse(
                {"error": f"Indicador {id_indicador} not found"}, status=404
            )
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


class IndicadorListView(View):
    def get(self, request, *args, **kwargs):
        try:
            indicador = Indicador.objects.values()
            return JsonResponse(list(indicador), safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


def get_max_min_values(df, year):
    year = year.rstrip("*")
    min_val = df[year].min()
    max_val = df[year].max()
    return min_val, max_val


def get_indicador_value(df, codigo_ibge, ano):
    if len(str(codigo_ibge)) > 6:
        codigo_ibge = str(codigo_ibge)[:-1]
    try:
        if codigo_ibge in df["Cod. IBGE"].values:
            if ano in df.columns:
                valor = df[df["Cod. IBGE"] == codigo_ibge][ano].values[0]
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


class EstabelecimentosSaudeProxy(APIView):
    def get(self, request):
        base_url = "https://apidadosabertos.saude.gov.br/cnes/estabelecimentos"
        params = request.query_params
        response = requests.get(base_url, params=params)
        return JsonResponse(response.json(), safe=False)


class EstabelecimentosView(APIView):
    def get(self, request):
        filters = self.build_filters(request)
        estabelecimentos = Estabelecimento.objects.filter(**filters).values(
            "codigo_cnes",
            "nome_fantasia",
            "endereco_estabelecimento",
            "numero_estabelecimento",
            "bairro_estabelecimento",
            "codigo_cep_estabelecimento",
            "latitude_estabelecimento_decimo_grau",
            "longitude_estabelecimento_decimo_grau",
            "numero_telefone_estabelecimento",
            "descricao_turno_atendimento",
            "estabelecimento_faz_atendimento_ambulatorial_sus",
            "estabelecimento_possui_centro_cirurgico",
            "estabelecimento_possui_servico_apoio",
            "estabelecimento_possui_atendimento_ambulatorial",
            "codigo_municipio",
            "numero_cnpj_entidade",
            "nome_razao_social",
            "natureza_organizacao_entidade",
            "tipo_gestao",
            "descricao_nivel_hierarquia",
            "descricao_esfera_administrativa",
            "codigo_tipo_unidade",
            "endereco_email_estabelecimento",
            "numero_cnpj",
            "codigo_identificador_turno_atendimento",
            "codigo_estabelecimento_saude",
            "codigo_uf",
            "descricao_natureza_juridica_estabelecimento",
            "codigo_motivo_desabilitacao_estabelecimento",
            "estabelecimento_possui_centro_obstetrico",
            "estabelecimento_possui_centro_neonatal",
            "estabelecimento_possui_atendimento_hospitalar",
            "codigo_atividade_ensino_unidade",
            "codigo_natureza_organizacao_unidade",
            "codigo_nivel_hierarquia_unidade",
            "codigo_esfera_administrativa_unidade",
        )
        return JsonResponse({"estabelecimentos": list(estabelecimentos)}, safe=False)

    def build_filters(self, request):
        """Constrói filtros de consulta a partir dos parâmetros da requisição"""
        filter_params = [
            "codigo_cnes",
            "nome_fantasia",
            "endereco_estabelecimento",
            "numero_estabelecimento",
            "bairro_estabelecimento",
            "codigo_cep_estabelecimento",
            "latitude_estabelecimento_decimo_grau",
            "longitude_estabelecimento_decimo_grau",
            "numero_telefone_estabelecimento",
            "descricao_turno_atendimento",
            "estabelecimento_faz_atendimento_ambulatorial_sus",
            "estabelecimento_possui_centro_cirurgico",
            "estabelecimento_possui_servico_apoio",
            "estabelecimento_possui_atendimento_ambulatorial",
            "codigo_municipio",
            "codigo_tipo_unidade",  
        ]
        filters = {
            param: request.GET.get(param)
            for param in filter_params
            if request.GET.get(param)
        }
        return filters


class TipoUnidadeListView(APIView):
    def get(self, request):
        tipos_unidade = TipoUnidade.objects.all().values(
            "codigo_tipo_unidade", "descricao_tipo_unidade"
        )
        return JsonResponse({"tipos_unidade": list(tipos_unidade)}, safe=False)


class CidadeListView(APIView):
    def get(self, request):
        cidades = Cidade.objects.all().values(
            'codigo_ibge', 'nome', 'latitude', 'longitude', 'regiao_saude__nome'
        )
        cidades = [
            {
                'codigo_ibge': cidade['codigo_ibge'][:-1],  # Remove o último dígito
                'nome': cidade['nome'],
                'latitude': cidade['latitude'],
                'longitude': cidade['longitude'],
                'regiao_saude__nome': cidade['regiao_saude__nome']
            }
            for cidade in cidades
        ]
        return JsonResponse({'cidades': cidades}, safe=False)
