import asyncio
import csv
import re

import scrapy
from playwright.async_api import async_playwright

from clinicas_scraper.items import ClinicaItem


class InstagramClinicasSpider(scrapy.Spider):
    name = 'instagram_clinicas'

    custom_settings = {
        'DOWNLOAD_DELAY': 5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'ROBOTSTXT_OBEY': False,
    }

    def __init__(self, input_csv=None, output_dir='/root/Comercial Estructure/Base de Clinicas Odonto',
                 max_itens=0, **kwargs):
        super().__init__(**kwargs)
        self.input_csv = input_csv
        self.output_dir = output_dir
        self.max_itens = int(max_itens) if max_itens else 0

    async def start(self):
        if not self.input_csv:
            self.logger.error('Use: -a input_csv="/caminho/clinicas.csv"')
            return

        linhas = self._load_csv(self.input_csv)
        if not linhas:
            self.logger.error(f'CSV vazio ou nao encontrado: {self.input_csv}')
            return

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                locale='pt-BR',
                timezone_id='America/Sao_Paulo',
            )
            page = await context.new_page()

            try:
                for idx, row in enumerate(linhas):
                    if self.max_itens and idx >= self.max_itens:
                        break
                    item = await self._process_row(page, row)
                    if item:
                        yield item
                        self.logger.info(f'Instagram extraido: {item["nome"]} -> @{item["instagram"]}')
                    await asyncio.sleep(3)
            finally:
                await browser.close()

    def _load_csv(self, path):
        linhas = []
        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    linhas.append(row)
        except Exception as e:
            self.logger.error(f'Erro lendo CSV: {e}')
        return linhas

    async def _process_row(self, page, row):
        nome = row.get('nome', '').strip()
        site = row.get('site', '').strip()
        instagram_raw = row.get('instagram', '').strip()

        handle = self._extract_handle(instagram_raw, site)
        if not handle:
            self.logger.warning(f'Instagram nao encontrado para: {nome}')
            return None

        url = f'https://www.instagram.com/{handle}/embed/'
        try:
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(4)

            item = ClinicaItem()
            item['nome'] = nome
            item['site'] = site
            item['instagram'] = handle
            item['cidade'] = row.get('cidade', '')
            item['estado'] = row.get('estado', '')
            item['categoria'] = 'Clinica Odontologica - Instagram'
            item['fonte'] = url

            texto = await page.evaluate(r'''() => document.body.innerText || '' ''')
            linhas = [l.strip() for l in texto.split('\n') if l.strip()]

            # bio: linha apos o handle
            if len(linhas) >= 2 and handle.lower() in linhas[0].lower():
                item['instagram_bio'] = linhas[1]
            else:
                item['instagram_bio'] = ' | '.join(linhas[:3])

            # seguidores e posts do texto do embed
            seguidores = self._parse_count(texto, [
                r'(\d[\d.,]*\s*[KMB]?)\s*seguidores',
                r'(\d[\d.,]*\s*[KMB]?)\s*followers',
            ])
            posts = self._parse_count(texto, [
                r'(\d[\d.,]*\s*[KMB]?)\s*posts',
                r'(\d[\d.,]*\s*[KMB]?)\s*publica[çc][õo]es',
            ])

            item['instagram_seguidores'] = seguidores
            item['instagram_posts'] = posts
            item['instagram_ultima_postagem'] = self._extract_last_post(texto)

            return item

        except Exception as e:
            self.logger.warning(f'Erro Instagram {handle}: {e}')
            return None

    def _extract_handle(self, instagram_raw, site):
        invalid_handles = {'explore', 'p', 'accounts', 'direct', 'stories', 'reels', 'about', 'blog', 'rsrc.php', 'whatsapp', 'reel'}

        if instagram_raw:
            m = re.search(r'(?:instagram\.com/|@)([A-Za-z0-9_.]+)', instagram_raw)
            if m:
                h = m.group(1).strip('.').lower()
                if h not in invalid_handles:
                    return h
            if re.match(r'^[A-Za-z0-9_.]+$', instagram_raw):
                h = instagram_raw.lower()
                if h not in invalid_handles:
                    return h

        if site:
            # tenta achar link do instagram no site
            try:
                import urllib.request
                req = urllib.request.Request(site, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    html = resp.read().decode('utf-8', errors='ignore')
                    for m in re.finditer(r'instagram\.com/([A-Za-z0-9_.]+)', html):
                        h = m.group(1).strip('/').lower()
                        if h and h not in invalid_handles:
                            return h
            except Exception:
                pass
        return ''

    def _parse_count(self, texto, patterns):
        for pat in patterns:
            m = re.search(pat, texto, re.IGNORECASE)
            if m:
                return self._normalize_count(m.group(1))
        return ''

    def _normalize_count(self, valor):
        valor = valor.strip().replace('.', '').replace(',', '.')
        try:
            if 'K' in valor.upper():
                return str(int(float(valor.upper().replace('K', '')) * 1000))
            if 'M' in valor.upper():
                return str(int(float(valor.upper().replace('M', '')) * 1000000))
            if 'B' in valor.upper():
                return str(int(float(valor.upper().replace('B', '')) * 1000000000))
            return str(int(float(valor)))
        except Exception:
            return valor

    def _extract_last_post(self, texto):
        # procura padroes tipo "2 dias atras", "5 horas atras", etc
        m = re.search(r'(\d+)\s*(horas?|dias?|semanas?|meses?|minutos?)\s*atr[áa]s', texto, re.IGNORECASE)
        if m:
            return m.group(0)
        return ''
