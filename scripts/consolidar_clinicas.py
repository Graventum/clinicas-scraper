#!/usr/bin/env python3
"""
Consolida CSV do Google Maps com CSV do Instagram em uma unica planilha.
Chave de join: nome da clinica (case-insensitive, strip).
"""

import argparse
import csv
import os
from datetime import datetime


def normalizar(texto):
    if not texto:
        return ''
    return texto.strip().lower().replace('  ', ' ')


def carregar_csv(path):
    with open(path, 'r', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def salvar_csv(path, linhas, fieldnames):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for linha in linhas:
            writer.writerow({k: linha.get(k, '') for k in fieldnames})


def merge(gmaps_path, instagram_path, output_path):
    gmaps = carregar_csv(gmaps_path)
    instagram = carregar_csv(instagram_path)

    # indexa instagram por nome
    insta_por_nome = {}
    for row in instagram:
        nome = normalizar(row.get('nome', ''))
        if nome:
            insta_por_nome[nome] = row

    campos_instagram = [
        'instagram', 'instagram_seguidores', 'instagram_posts',
        'instagram_ultima_postagem', 'instagram_bio'
    ]

    consolidado = []
    for row in gmaps:
        nome_norm = normalizar(row.get('nome', ''))
        insta = insta_por_nome.get(nome_norm, {})
        for campo in campos_instagram:
            row[campo] = insta.get(campo, '')
        consolidado.append(row)

    # garante ordem dos campos
    fieldnames = []
    if gmaps:
        fieldnames = list(gmaps[0].keys())
        for campo in campos_instagram:
            if campo not in fieldnames:
                fieldnames.append(campo)

    salvar_csv(output_path, consolidado, fieldnames)
    print(f'Consolidado salvo: {output_path} ({len(consolidado)} clinicas)')


def main():
    parser = argparse.ArgumentParser(description='Consolida CSVs de GMaps e Instagram')
    parser.add_argument('--gmaps', required=True, help='CSV do Google Maps')
    parser.add_argument('--instagram', required=True, help='CSV do Instagram')
    parser.add_argument('--output', required=True, help='CSV consolidado de saida')
    args = parser.parse_args()
    merge(args.gmaps, args.instagram, args.output)


if __name__ == '__main__':
    main()
