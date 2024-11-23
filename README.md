SASI
## Instruções Básicas de Uso

### Configuração do Ambiente
1. Clone o repositório:
    ```bash
    git clone https://github.com/sasi-team/sasi.git
    cd sasi
    ```
2. Crie e ative um ambiente virtual:
    ```bash
    python -m venv venv
    source venv/bin/activate  # No Windows use `venv\Scripts\activate`
    ```
3. Instale as dependências:
    ```bash
    pip install -r requirements.txt
    ```
4. Rode as migrações do banco de dados:
    ```bash
    python3 src/backend/manage.py migrate
    ```

### Processos de ETL

#### ETL do CSV
1. Execute o comando para importar dados do CSV de indicadores de sude do ibge:
    ```bash
    python3 src/backend/manage.py import_data
    ```

#### ETL da API
1. Execute o comando para importar dados da API de dados abertos do governo:
    ```bash
    python3 src/backend/manage.py import_estabelecimentos
    ```

### Pastas de Notebooks e Assets
- **notebooks**: Contém notebooks Jupyter para análise e visualização de dados.
- **assets**: Contém arquivos GeoJSON e dados georreferenciados de saúde.

### Executando o Projeto
1. Inicie o servidor:
    ```bash
    python3 src/backend/manage.py runserver
    ```
2. Acesse o projeto no navegador em `http://127.0.0.1:8000`.

Pronto! Agora você está preparado para utilizar o projeto SASI.