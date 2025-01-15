import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import logging
from django.db import transaction
from django.db.utils import DataError
from api.models import Estoque
from tqdm import tqdm
from typing import List, Dict, Any
from datetime import datetime
import backoff

class EstoqueETL:
    def __init__(self, uf_code: int = 29, batch_size: int = 100):
        self.base_url = 'https://apidadosabertos.saude.gov.br/daf/estoque-medicamentos-bnafar-horus'
        self.uf_code = uf_code
        self.batch_size = batch_size
        self.session = self._setup_session()
        self.setup_logging()

    def _setup_session(self) -> requests.Session:
        """Configure session with retry logic"""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def setup_logging(self) -> None:
        """Configure logging with rotation and structured format"""
        log_filename = f'etl_estoque_{datetime.now().strftime("%Y%m%d")}.log'
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
            handlers=[
                logging.handlers.RotatingFileHandler(
                    log_filename,
                    maxBytes=10485760,  # 10MB
                    backupCount=5
                ),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=3)
    def fetch_data(self, url: str, params: Dict = None) -> Dict:
        """Fetch data with exponential backoff retry"""
        self.logger.info(f"Fetching data from {url} with params {params}")
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching data: {str(e)}")
            raise

    def fetch_all_estoque(self) -> List[Dict[str, Any]]:
        """Fetch all establishments with pagination"""
        estoque = []
        offset = 0
        limit = 20
        
        try:
            with tqdm(desc="Fetching estoque") as pbar:
                while True:
                    params = {
                        'codigo_uf': self.uf_code,
                        'limit': limit,
                        'offset': offset
                    }
                    data = self.fetch_data(self.base_url, params)
                    current_batch = data['estoque']
                    estoque.extend(current_batch)
                    
                    pbar.update(len(current_batch))
                    
                    if len(current_batch) < limit:
                        break
                        
                    offset += limit
                    
            self.logger.info(f"Successfully fetched {len(estoque)} estoque")
            return estoque
            
        except Exception as e:
            self.logger.error(f"Error in fetch_all_estoque: {str(e)}")
            raise
    
    def _create_estoque_object(self, est: Dict) -> Estoque:
        """Create Estoque object with data validation"""
        try:
            return Estoque(
                codigo_uf=est['codigo_uf'],
                uf=est['uf'][:2] if est['uf'] else None,
                endereco_estabelecimento=est['endereco_estabelecimento'][:255] if est['endereco_estabelecimento'] else None,
                numero_estabelecimento=est['numero_estabelecimento'],
                bairro_estabelecimento=est['bairro_estabelecimento'][:100] if est['bairro_estabelecimento'] else None,
                codigo_cep_estabelecimento=est['codigo_cep_estabelecimento'],
                latitude_estabelecimento_decimo_grau=est['latitude_estabelecimento_decimo_grau'],
                longitude_estabelecimento_decimo_grau=est['longitude_estabelecimento_decimo_grau'],
                numero_telefone_estabelecimento=est['numero_telefone_estabelecimento'],
                descricao_turno_atendimento=est['descricao_turno_atendimento'],
                estabelecimento_faz_atendimento_ambulatorial_sus=est['estabelecimento_faz_atendimento_ambulatorial_sus'],
                estabelecimento_possui_centro_cirurgico=est['estabelecimento_possui_centro_cirurgico'],
                estabelecimento_possui_servico_apoio=est['estabelecimento_possui_servico_apoio'],
                estabelecimento_possui_atendimento_ambulatorial=est['estabelecimento_possui_atendimento_ambulatorial'],
                codigo_municipio=est['codigo_municipio'],
                **{k: est.get(k) for k in [
                    'numero_cnpj_entidade', 'nome_razao_social', 'natureza_organizacao_entidade',
                    'tipo_gestao', 'descricao_nivel_hierarquia', 'descricao_esfera_administrativa',
                    'codigo_tipo_unidade', 'endereco_email_estabelecimento', 'numero_cnpj',
                    'codigo_identificador_turno_atendimento', 'codigo_estabelecimento_saude',
                    'codigo_uf', 'descricao_natureza_juridica_estabelecimento',
                    'codigo_motivo_desabilitacao_estabelecimento', 'estabelecimento_possui_centro_obstetrico',
                    'estabelecimento_possui_centro_neonatal', 'estabelecimento_possui_atendimento_hospitalar',
                    'codigo_atividade_ensino_unidade', 'codigo_natureza_organizacao_unidade',
                    'codigo_nivel_hierarquia_unidade', 'codigo_esfera_administrativa_unidade'
                ]}
            )
        except Exception as e:
            self.logger.error(f"Error creating estabelecimento object: {str(e)}")
            raise

    @transaction.atomic
    def import_estoque(self) -> None:
        """Import establishments with error handling and progress tracking"""
        try:
            estoque = self.fetch_all_estoque()
            failed_records = []
            
            for i in tqdm(range(0, len(estoque), self.batch_size), desc="Importando estoque"):
                batch = estoque[i:i + self.batch_size]
                try:
                    objects_to_create = [
                        self._create_estoque_object(est) for est in batch
                    ]
                    Estoque.objects.bulk_create(
                        objects_to_create,
                        ignore_conflicts=True,
                        batch_size=self.batch_size
                    )
                except DataError as e:
                    self.logger.error(f"Data error in batch {i // self.batch_size + 1}: {str(e)}")
                    failed_records.extend(batch)
                except Exception as e:
                    self.logger.error(f"Error processing batch {i // self.batch_size + 1}: {str(e)}")
                    failed_records.extend(batch)
                # else:
                #     self.logger.info(f"Successfully imported batch {i // self.batch_size + 1}")
            
            if failed_records:
                self.logger.warning(f"Failed to import {len(failed_records)} records")
                # Save failed records for later analysis
                with open(f'failed_records_{datetime.now().strftime("%Y%m%d")}.log', 'w') as f:
                    for record in failed_records:
                        f.write(f"{record}\n")
                        
        except Exception as e:
            self.logger.error(f"Error in import_estoque: {str(e)}")
            raise

    @transaction.atomic
    def run(self) -> None:
        """Run the ETL process with timing information"""
        start_time = datetime.now()
        self.logger.info(f"Starting ETL process at {start_time}")
        
        try:
            self.import_tipos_unidade()
            self.import_estoque()
            
            end_time = datetime.now()
            duration = end_time - start_time
            self.logger.info(f"ETL process completed successfully at {end_time}. Duration: {duration}")
        except Exception as e:
            self.logger.error(f"ETL process failed: {str(e)}")
            raise

if __name__ == "__main__":
    etl = EstoqueETL()
    etl.run()