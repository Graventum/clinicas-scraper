import scrapy


class ClinicaItem(scrapy.Item):
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
