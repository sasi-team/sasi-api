import requests
import logging
from django.db import transaction
from api.models import Estabelecimento, TipoUnidade
from tqdm import tqdm

class EstabelecimentosETL:
    def __init__(self):
        self.base_url = 'https://apidadosabertos.saude.gov.br/cnes/estabelecimentos'
        self.tipo_unidade_url = 'https://apidadosabertos.saude.gov.br/cnes/tipounidades'
        self.uf_code = 29
        self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('etl_estabelecimentos.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def fetch_data(self, url, params=None):
        self.logger.info(f"Fetching data from {url} with params {params}")
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def fetch_all_estabelecimentos(self):
        estabelecimentos = []
        offset = 0
        limit = 20

        while True:
            params = {
                'codigo_uf': self.uf_code,
                'limit': limit,
                'offset': offset
            }
            data = self.fetch_data(self.base_url, params)
            estabelecimentos.extend(data['estabelecimentos'])

            if len(data['estabelecimentos']) < limit:
                break

            offset += limit
            self.logger.info(f"Fetched {len(estabelecimentos)} estabelecimentos so far")

        return estabelecimentos

    def fetch_tipos_unidade(self):
        return self.fetch_data(self.tipo_unidade_url)['tipos_unidade']

    @transaction.atomic
    def import_estabelecimentos(self):
        estabelecimentos = self.fetch_all_estabelecimentos()
        batch_size = 100
        for i in tqdm(range(0, len(estabelecimentos), batch_size), desc="Importando estabelecimentos"):
            batch = estabelecimentos[i:i + batch_size]
            Estabelecimento.objects.bulk_create(
                [Estabelecimento(
                    codigo_cnes=est['codigo_cnes'],
                    nome_fantasia=est['nome_fantasia'],
                    endereco_estabelecimento=est['endereco_estabelecimento'],
                    numero_estabelecimento=est['numero_estabelecimento'],
                    bairro_estabelecimento=est['bairro_estabelecimento'],
                    codigo_cep_estabelecimento=est['codigo_cep_estabelecimento'],
                    latitude_estabelecimento_decimo_grau=est['latitude_estabelecimento_decimo_grau'],
                    longitude_estabelecimento_decimo_grau=est['longitude_estabelecimento_decimo_grau'],
                    numero_telefone_estabelecimento=est['numero_telefone_estabelecimento'],
                    descricao_turno_atendimento=est['descricao_turno_atendimento'],
                    estabelecimento_faz_atendimento_ambulatorial_sus=est['estabelecimento_faz_atendimento_ambulatorial_sus'],
                    estabelecimento_possui_centro_cirurgico=est['estabelecimento_possui_centro_cirurgico'],
                    estabelecimento_possui_servico_apoio=est['estabelecimento_possui_servico_apoio'],
                    estabelecimento_possui_atendimento_ambulatorial=est['estabelecimento_possui_atendimento_ambulatorial']
                ) for est in batch],
                ignore_conflicts=True
            )
            self.logger.info(f"Imported batch {i // batch_size + 1}")

    @transaction.atomic
    def import_tipos_unidade(self):
        tipos_unidade = self.fetch_tipos_unidade()
        for tipo in tqdm(tipos_unidade, desc="Importando tipos de unidade"):
            TipoUnidade.objects.update_or_create(
                codigo_tipo_unidade=tipo['codigo_tipo_unidade'],
                defaults={'descricao_tipo_unidade': tipo['descricao_tipo_unidade']}
            )
        self.logger.info("Tipos de unidade importados com sucesso")

    def run(self):
        self.import_tipos_unidade()
        self.import_estabelecimentos()

if __name__ == "__main__":
    etl = EstabelecimentosETL()
    etl.run()