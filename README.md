# Clinicas Scraper - Graventum

## Instalacao
pip install -r requirements.txt
playwright install chromium

## 4 Spiders prontos

### 1. Diretorio Generico (HTML puro)
scrapy crawl diretorio_clinicas -a start_url="URL_AQUI"

### 2. Rede/Franquia
scrapy crawl rede_clinicas -a start_url="URL_AQUI"

### 3. Google Maps (Playwright) — enriquecido com ICP Odonto
scrapy crawl gmaps_clinicas -a cidade="Curitiba" -a estado="PR" -a termo="clinica odontologica" -a max_resultados=30

Campos ICP coletados:
- `qtd_reviews`, `estrelas` — reputacao e volume
- `qtd_fotos`, `urls_fotos` — infraestrutura
- `horario_funcionamento` — porte/organizacao
- `especialidades`, `servicos` — alto ticket (implante, ortodontia, invisalign, facetas, etc)

### 4. Instagram — maturidade digital (Pilar 4 do ICP)
scrapy crawl instagram_clinicas -a input_csv="/root/Comercial Estructure/Base de Clinicas Odonto/clinicas_curitiba_pr_20260820.csv" -a max_itens=10

Campos coletados:
- `instagram` — handle
- `instagram_seguidores` — numero de seguidores
- `instagram_posts` — quantidade de publicacoes
- `instagram_ultima_postagem` — tempo da ultima postagem
- `instagram_bio` — descricao do perfil

## Onde a planilha cai
Por padrao: `/root/Comercial Estructure/Base de Clinicas Odonto/`
Nome: `{spider_name}_{timestamp}.csv`

## Cron diario (OmniRoute + Scrapy)

O job roda todo dia as 06h00 UTC (03h00 BRT) via `cron-monitor.sh`.

```bash
0 6 * * * cd "/root/Comercial Estructure/clinicas_scraper" && /root/scripts/cron-monitor.sh "clinicas-odonto-daily" bash scripts/run_daily.sh >> /var/log/clinicas-odonto-daily.log 2>&1
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
