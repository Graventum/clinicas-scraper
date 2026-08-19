# Clinicas Scraper - Graventum

## Instalacao
pip install -r requirements.txt
playwright install chromium

## 3 Spiders prontos

### 1. Diretorio Generico (HTML puro)
scrapy crawl diretorio_clinicas -a start_url="URL_AQUI"

### 2. Rede/Franquia
scrapy crawl rede_clinicas -a start_url="URL_AQUI"

### 3. Google Maps (Playwright)
scrapy crawl gmaps_clinicas -a cidade="Curitiba" -a estado="PR" -a termo="clinica odontologica" -a max_resultados=30

## Onde a planilha cai
Por padrao: `/root/Comercial Estructure/Base de Clinicas Odonto/`
Nome: `{spider_name}_{timestamp}.csv`

## Aviso
Respeite robots.txt. Use delays. Nao faca scraping em massa sem autorizacao.
