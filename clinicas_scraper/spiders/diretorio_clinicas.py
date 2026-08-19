import scrapy

from clinicas_scraper.items import ClinicaItem


class DiretorioClinicasSpider(scrapy.Spider):
    name = 'diretorio_clinicas'

    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
    }

    def __init__(self, start_url=None, output_dir='/root/Comercial Estructure/Base de Clinicas Odonto', **kwargs):
        super().__init__(**kwargs)
        self.start_urls = [start_url] if start_url else []
        self.output_dir = output_dir
        if not self.start_urls or not self.start_urls[0]:
            raise ValueError("Use: -a start_url=\"URL_DO_DIRETORIO\"")

    def parse(self, response):
        self.logger.info(f"Analisando: {response.url}")
        for card in response.css('div.result-item, .listing-card, .empresa-item, .item-lista'):
            item = ClinicaItem()
            item['nome'] = self._extract(card, 'h2::text, h3::text, .nome::text, .title::text, .company-name::text')
            item['endereco'] = self._extract(card, '.endereco::text, .address::text, address::text, .localizacao::text')
            item['telefone'] = self._extract(card, '.telefone::text, .phone::text, [href^="tel:"]::text, .tel::text')
            item['email'] = self._extract(card, '.email::text, [href^="mailto:"]::text')
            item['site'] = self._extract_attr(card, '.site::attr(href), .website::attr(href), a[href*="http"]::attr(href)')
            item['cidade'] = self._extract(card, '.cidade::text, .city::text')
            item['estado'] = self._extract(card, '.estado::text, .state::text, .uf::text')
            item['bairro'] = self._extract(card, '.bairro::text, .neighborhood::text')
            item['categoria'] = 'Clinica Odontologica'
            item['fonte'] = response.url
            yield item

        next_page = response.css('a.next::attr(href), .pagination .next a::attr(href), a[rel="next"]::attr(href), .proxima::attr(href)').get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def _extract(self, selector, css_path):
        for text in selector.css(css_path).getall():
            if text and text.strip():
                return text.strip()
        return ''

    def _extract_attr(self, selector, css_path):
        for val in selector.css(css_path).getall():
            if val and val.strip():
                return val.strip()
        return ''
