#!/usr/bin/env bash
# Levantar todo el proyecto 2PC
# Uso: ./start.sh [--fallo]

cd "$(dirname "$0")"

MODO_FALLO=0
if [[ "$1" == "--fallo" ]]; then
  MODO_FALLO=1
fi

echo ""
echo "══════════════════════════════════════════════════"
echo "  Práctica 2PC — Transacciones Distribuidas"
echo "══════════════════════════════════════════════════"
echo ""
echo "  Levantando contenedores Docker..."
MODO_FALLO=$MODO_FALLO docker compose up --build -d

echo ""
echo "  Esperando que los servicios estén listos..."
sleep 5

echo ""
echo "  Abriendo interfaz gráfica..."
python interfaz/interfaz_2pc.py
