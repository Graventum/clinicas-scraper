import scrapy

from clinicas_scraper.items import ClinicaItem


class RedeClinicasSpider(scrapy.Spider):
    name = 'rede_clinicas'

    custom_settings = {
        'DOWNLOAD_DELAY': 1,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
    }

    def __init__(self, start_url=None, output_dir='/root/Comercial Estructure/Base de Clinicas Odonto', **kwargs):
        super().__init__(**kwargs)
        self.start_urls = [start_url] if start_url else []
        self.output_dir = output_dir
        if not self.start_urls or not self.start_urls[0]:
            raise ValueError("Use: -a start_url=\"URL_DA_PAGINA_DE_UNIDADES\"")

    def parse(self, response):
        self.logger.info(f"Analisando rede: {response.url}")
        for unidade in response.css('div.unidade, .filial, .unit-card, .location-item, .branch'):
            item = ClinicaItem()
            item['nome'] = self._extract(unidade, 'h3::text, h4::text, .unit-name::text, .nome::text')
            rua = self._extract(unidade, '.rua::text, .street::text, .address-line::text')
            bairro = self._extract(unidade, '.bairro::text, .neighborhood::text')
            numero = self._extract(unidade, '.numero::text, .number::text')
            endereco = f"{rua}, {numero}".strip(', ') if rua else bairro
            item['endereco'] = endereco
            item['bairro'] = bairro
            item['telefone'] = self._extract(unidade, '.telefone::text, .phone::text, [href^="tel:"]::text')
            item['site'] = response.url
            item['cidade'] = 'Curitiba'
            item['estado'] = 'PR'
            item['categoria'] = 'Clinica Odontologica - Rede'
            item['fonte'] = response.url
            yield item

        for link in response.css('a[href*="unidade"], a[href*="filial"], a[href*="local"]::attr(href)').getall():
            yield response.follow(link, callback=self.parse_unidade)

    def parse_unidade(self, response):
        self.logger.info(f"Detalhe da unidade: {response.url}")
        item = ClinicaItem()
        item['nome'] = response.css('h1::text, h2::text, .unit-title::text').get('').strip()
        item['endereco'] = response.css('.endereco::text, .address::text, address::text').get('').strip()
        item['telefone'] = response.css('.telefone::text, .phone::text, [href^="tel:"]::text').get('').strip()
        item['email'] = response.css('.email::text, [href^="mailto:"]::text').get('').strip()
        item['site'] = response.url
        item['cidade'] = response.css('.cidade::text, .city::text').get('Curitiba').strip()
        item['estado'] = response.css('.estado::text, .state::text').get('PR').strip()
        item['categoria'] = 'Clinica Odontologica - Rede'
        item['fonte'] = response.url
        yield item

    def _extract(self, selector, css_path):
        for text in selector.css(css_path).getall():
            if text and text.strip():
                return text.strip()
        return ''
