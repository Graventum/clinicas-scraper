import scrapy


class ClinicaItem(scrapy.Item):
    # identificacao
    nome = scrapy.Field()
    endereco = scrapy.Field()
    telefone = scrapy.Field()
    email = scrapy.Field()
    site = scrapy.Field()
    cidade = scrapy.Field()
    estado = scrapy.Field()
    bairro = scrapy.Field()
    categoria = scrapy.Field()
    fonte = scrapy.Field()
    cnpj = scrapy.Field()

    # pilar 1: reputacao e volume
    qtd_reviews = scrapy.Field()
    estrelas = scrapy.Field()

    # pilar 2: infraestrutura
    qtd_fotos = scrapy.Field()
    urls_fotos = scrapy.Field()

    # pilar 3: porte/organizacao
    horario_funcionamento = scrapy.Field()

    # pilar 5: alto ticket
    especialidades = scrapy.Field()
    servicos = scrapy.Field()

    # pilar 4: maturidade digital
    instagram = scrapy.Field()
    instagram_seguidores = scrapy.Field()
    instagram_posts = scrapy.Field()
    instagram_ultima_postagem = scrapy.Field()
    instagram_bio = scrapy.Field()
