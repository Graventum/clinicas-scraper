#!/bin/bash
# run_enriched.sh — roda gmaps + instagram e gera uma unica planilha consolidada.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="/root/Comercial Estructure/Base de Clinicas Odonto"
PROCESSED_DIR="$OUTPUT_DIR/processadas"
VENV_DIR="$PROJECT_DIR/venv"
OMNIROUTE_URL="http://localhost:20128/v1/models"
CIDADE="${CIDADE:-Curitiba}"
ESTADO="${ESTADO:-PR}"
TERMO="${TERMO:-clinica odontologica}"
MAX_RESULTADOS="${MAX_RESULTADOS:-50}"

mkdir -p "$OUTPUT_DIR" "$PROCESSED_DIR"

log() {
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"
}

# Health check no OmniRoute
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

TODAY=$(date +%Y%m%d)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 1. GMaps
log "=== 1/3 Google Maps ==="
scrapy crawl gmaps_clinicas \
  -a cidade="$CIDADE" \
  -a estado="$ESTADO" \
  -a termo="$TERMO" \
  -a max_resultados="$MAX_RESULTADOS" \
  -a output_dir="$OUTPUT_DIR"

GMAPS_CSV=$(ls -t "$OUTPUT_DIR"/gmaps_clinicas_*.csv 2>/dev/null | head -n 1)
if [ -z "$GMAPS_CSV" ]; then
  log "ERROR: nenhum CSV do Google Maps gerado"
  exit 1
fi
log "GMaps CSV: $GMAPS_CSV"

# 2. Instagram
log "=== 2/3 Instagram ==="
scrapy crawl instagram_clinicas \
  -a input_csv="$GMAPS_CSV" \
  -a output_dir="$OUTPUT_DIR"

INSTA_CSV=$(ls -t "$OUTPUT_DIR"/instagram_clinicas_*.csv 2>/dev/null | head -n 1)
if [ -z "$INSTA_CSV" ]; then
  log "WARNING: nenhum CSV do Instagram gerado; consolidado sem Instagram"
  INSTA_CSV=""
else
  log "Instagram CSV: $INSTA_CSV"
fi

# 3. Consolida
log "=== 3/3 Consolidacao ==="
CONSOLIDADO="$PROCESSED_DIR/clinicas_consolidado_${CIDADE,,}_${ESTADO,,}_${TIMESTAMP}.csv"
python3 "$SCRIPT_DIR/consolidar_clinicas.py" \
  --gmaps="$GMAPS_CSV" \
  --instagram="${INSTA_CSV:-$GMAPS_CSV}" \
  --output="$CONSOLIDADO"

# Copia tambem um arquivo fixo com data do dia
DAILY="$OUTPUT_DIR/clinicas_${CIDADE,,}_${ESTADO,,}_${TODAY}.csv"
cp "$CONSOLIDADO" "$DAILY"
log "Planilha diaria: $DAILY"

log "Finalizado."
