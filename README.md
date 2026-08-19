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

## Cron diario (OmniRoute + Scrapy)

O job roda todo dia as 06h00 UTC (03h00 BRT) via `cron-monitor.sh`.

```bash
0 6 * * * /root/scripts/cron-monitor.sh "clinicas-odonto-daily" bash "/root/Comercial Estructure/clinicas_scraper/scripts/run_daily.sh" >> /var/log/clinicas-odonto-daily.log 2>&1
```

Script: `scripts/run_daily.sh`
- Checa saude do OmniRoute (`GET http://localhost:20128/v1/models`)
- Ativa o venv do projeto
- Roda `scrapy crawl gmaps_clinicas` para Curitiba/PR
- Copia o CSV mais recente para `clinicas_curitiba_pr_YYYYMMDD.csv`

Para rodar manualmente:
```bash
bash "/root/Comercial Estructure/clinicas_scraper/scripts/run_daily.sh"
```

## Aviso
Respeite robots.txt. Use delays. Nao faca scraping em massa sem autorizacao.
