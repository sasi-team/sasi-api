from django.db import models

class MacroRegiao(models.Model):
    nome = models.CharField(max_length=100)

    class Meta:
        app_label = 'api'

    def __str__(self):
        return self.nome

class RegiaoSaude(models.Model):
    nome = models.CharField(max_length=100)
    macro_regiao = models.ForeignKey(MacroRegiao, on_delete=models.CASCADE)

    class Meta:
        app_label = 'api'

    def __str__(self):
        return self.nome

class Cidade(models.Model):
    codigo_ibge = models.CharField(max_length=7, unique=True)
    nome = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()
    regiao_saude = models.ForeignKey(RegiaoSaude, on_delete=models.CASCADE, null=True)

    class Meta:
        app_label = 'api'

    def __str__(self):
        return f"{self.nome} ({self.codigo_ibge})"

class Indicador(models.Model):
    nome_arquivo = models.CharField(max_length=100, unique=True)
    titulo = models.TextField()
    subtitulo = models.TextField(null=True, blank=True)
    fonte = models.TextField()

    class Meta:
        app_label = 'api'

    def __str__(self):
        return self.titulo

class ValorIndicador(models.Model):
    cidade = models.ForeignKey(Cidade, on_delete=models.CASCADE)
    indicador = models.ForeignKey(Indicador, on_delete=models.CASCADE)
    ano = models.IntegerField()
    valor = models.FloatField(null=True)

    class Meta:
        app_label = 'api'
        unique_together = ['cidade', 'indicador', 'ano']

    def __str__(self):
        return f"{self.cidade} - {self.indicador} ({self.ano}): {self.valor}"

class TipoUnidade(models.Model):
    codigo_tipo_unidade = models.IntegerField(primary_key=True)
    descricao_tipo_unidade = models.CharField(max_length=255)

class Estabelecimento(models.Model):
    codigo_cnes = models.IntegerField(primary_key=True)
    nome_fantasia = models.CharField(max_length=255)
    endereco_estabelecimento = models.CharField(max_length=255)
    numero_estabelecimento = models.CharField(max_length=10)
    bairro_estabelecimento = models.CharField(max_length=255)
    codigo_cep_estabelecimento = models.CharField(max_length=10)
    latitude_estabelecimento_decimo_grau = models.FloatField()
    longitude_estabelecimento_decimo_grau = models.FloatField()
    numero_telefone_estabelecimento = models.CharField(max_length=20, null=True)
    descricao_turno_atendimento = models.CharField(max_length=255)
    estabelecimento_faz_atendimento_ambulatorial_sus = models.CharField(max_length=3)
    estabelecimento_possui_centro_cirurgico = models.IntegerField()
    estabelecimento_possui_servico_apoio = models.IntegerField()
    estabelecimento_possui_atendimento_ambulatorial = models.IntegerField()