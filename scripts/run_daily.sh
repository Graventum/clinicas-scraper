#!/bin/bash
# run_daily.sh — executa o scraper de clínicas odontológicas diariamente.
# Rota: ativa venv, checa OmniRoute, roda spider gmaps, salva CSV em /root/Comercial Estructure/Base de Clinicas Odonto/

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="/root/Comercial Estructure/Base de Clinicas Odonto"
VENV_DIR="$PROJECT_DIR/venv"
OMNIROUTE_URL="http://localhost:20128/v1/models"
CIDADE="${CIDADE:-Curitiba}"
ESTADO="${ESTADO:-PR}"
TERMO="${TERMO:-clinica odontologica}"
MAX_RESULTADOS="${MAX_RESULTADOS:-50}"

mkdir -p "$OUTPUT_DIR"

log() {
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"
}

# Health check no OmniRoute antes de rodar
log "Checando OmniRoute em $OMNIROUTE_URL ..."
if curl -sf "$OMNIROUTE_URL" >/dev/null 2>&1; then
  log "OmniRoute OK"
else
  log "WARNING: OmniRoute nao respondeu. Continuando sem roteamento LLM."
fi

# Ativa venv
if [ ! -d "$VENV_DIR" ]; then
  log "ERROR: venv nao encontrado em $VENV_DIR"
  exit 1
fi
source "$VENV_DIR/bin/activate"

cd "$PROJECT_DIR"

log "Iniciando scraping: cidade=$CIDADE estado=$ESTADO termo='$TERMO' max=$MAX_RESULTADOS"

scrapy crawl gmaps_clinicas \
  -a cidade="$CIDADE" \
  -a estado="$ESTADO" \
  -a termo="$TERMO" \
  -a max_resultados="$MAX_RESULTADOS" \
  -a output_dir="$OUTPUT_DIR"

# Renomeia o CSV mais recente do spider para o nome padrao diario
LATEST=$(ls -t "$OUTPUT_DIR"/gmaps_clinicas_*.csv 2>/dev/null | head -n 1)
if [ -n "$LATEST" ]; then
  TODAY=$(date +%Y%m%d)
  DEST="$OUTPUT_DIR/clinicas_${CIDADE,,}_${ESTADO,,}_${TODAY}.csv"
  cp "$LATEST" "$DEST"
  log "Planilha do dia salva: $DEST"
else
  log "WARNING: nenhum CSV gerado pelo spider"
fi

log "Scraping finalizado."
