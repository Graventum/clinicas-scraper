import asyncio
import re

import scrapy
from playwright.async_api import async_playwright

from clinicas_scraper.items import ClinicaItem


class GoogleMapsClinicasSpider(scrapy.Spider):
    name = 'gmaps_clinicas'

    custom_settings = {
        'DOWNLOAD_DELAY': 3,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'ROBOTSTXT_OBEY': False,
    }

    def __init__(self, cidade='Curitiba', estado='PR', termo='clinica odontologica',
                 max_resultados=50, output_dir='/root/Comercial Estructure/Base de Clinicas Odonto', **kwargs):
        super().__init__(**kwargs)
        self.cidade = cidade
        self.estado = estado
        self.termo = termo
        self.max_resultados = int(max_resultados)
        self.output_dir = output_dir

    async def start(self):
        query = f"{self.termo} {self.cidade} {self.estado}"
        url = f"https://www.google.com.br/maps/search/{query.replace(' ', '+')}?hl=pt-BR&gl=BR"
        self.logger.info(f"Playwright: {url}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
                locale='pt-BR',
                timezone_id='America/Sao_Paulo',
            )
            page = await context.new_page()

            try:
                await page.goto(url, wait_until='networkidle', timeout=90000)
                await asyncio.sleep(4)

                try:
                    await page.click('button:has-text("Recusar tudo")', timeout=5000)
                    await asyncio.sleep(4)
                except Exception:
                    pass

                resultados = []
                vistos = set()
                hrefs_vistos = set()
                scroll_count = 0
                max_scrolls = 8
                sem_progresso = 0

                while len(resultados) < self.max_resultados and scroll_count < max_scrolls and sem_progresso < 3:
                    cards = await page.query_selector_all('div[role="main"] a[href*="/place/"]')
                    antes = len(resultados)
                    for card in cards:
                        if len(resultados) >= self.max_resultados:
                            break
                        href = await card.get_attribute('href') or ''
                        if href in hrefs_vistos:
                            continue
                        hrefs_vistos.add(href)
                        try:
                            item = await asyncio.wait_for(self._process_card(page, card, vistos), timeout=10)
                            if item:
                                resultados.append(item)
                                yield item
                                self.logger.info(f"Extraido: {item['nome']}")
                        except asyncio.TimeoutError:
                            self.logger.warning('Timeout processando card')
                            continue
                        except Exception as e:
                            self.logger.warning(f'Erro card: {e}')
                            continue

                    if len(resultados) == antes:
                        sem_progresso += 1
                    else:
                        sem_progresso = 0

                    await page.evaluate('''() => {
                        const main = document.querySelector('div[role="main"]');
                        if (main) {
                            const list = main.querySelector('div[role="feed"]') || main.firstElementChild;
                            if (list) list.scrollBy(0, 800);
                        }
                    }''')
                    await asyncio.sleep(2)
                    scroll_count += 1

                self.logger.info(f"Total: {len(resultados)}")

            except Exception as e:
                self.logger.error(f"Erro Playwright: {e}")
            finally:
                await browser.close()

    async def _process_card(self, page, card, vistos):
        await card.click()
        await asyncio.sleep(3)
        item = await self._extract_from_panel(page)
        if item and item['nome']:
            chave = item['nome'] + item['endereco']
            if chave not in vistos:
                vistos.add(chave)
                return item
        return None

    async def _extract_from_panel(self, page):
        item = ClinicaItem()
        try:
            title = await page.title()
            item['nome'] = title.replace(' - Google Maps', '').strip()

            addr = await page.query_selector('button[data-item-id="address"]')
            if addr:
                aria = await addr.get_attribute('aria-label') or ''
                item['endereco'] = aria.replace('Endereço:', '').strip()
            else:
                item['endereco'] = ''

            # telefone do botao especifico
            phone = await page.query_selector('button[data-item-id="phone"]')
            if phone:
                aria = await phone.get_attribute('aria-label') or ''
                item['telefone'] = aria.replace('Telefone:', '').strip()
            else:
                item['telefone'] = ''

            # fallback: procura telefone no painel ao lado do nome
            if not item['telefone']:
                item['telefone'] = await self._find_phone_for_place(page, item['nome'])

            web = await page.query_selector('a[data-item-id="authority"]')
            if web:
                item['site'] = await web.get_attribute('href') or ''
            else:
                item['site'] = ''

            endereco = item['endereco']
            if endereco:
                partes = [p.strip() for p in endereco.split(',')]
                cidade_raw = partes[-2] if len(partes) > 2 else self.cidade
                cidade_match = re.search(r'^([^-]+)', cidade_raw)
                item['cidade'] = cidade_match.group(1).strip() if cidade_match else cidade_raw
                estado_match = re.search(r'-([A-Za-z]{2})', endereco)
                item['estado'] = estado_match.group(1).upper() if estado_match else self.estado
            else:
                item['cidade'] = self.cidade
                item['estado'] = self.estado

            item['categoria'] = 'Clinica Odontologica'
            item['fonte'] = page.url
            return item
        except Exception as e:
            self.logger.warning(f"Erro painel: {e}")
            return None

    async def _find_phone_for_place(self, page, nome):
        try:
            # botao de telefone direto
            phone = await page.query_selector('button[data-item-id="phone"]')
            if phone:
                aria = await phone.get_attribute('aria-label') or ''
                match = re.search(r'\(\d{2}\)\s*\d[\d\-\s]{7,}\d', aria)
                if match:
                    return match.group(0).strip()
            # painel lateral: bloco do lugar selecionado
            textos = await page.evaluate(r'''() => {
                const nodes = document.querySelectorAll('div, span');
                return Array.from(nodes).map(n => n.innerText || '')
                    .filter(t => t.includes('Compartilhar') && /\(\d{2}\)/.test(t));
            }''')

            for t in textos:
                if nome not in t:
                    continue
                linhas = [l.strip() for l in t.split('\n') if l.strip()]
                try:
                    idx = next(i for i, l in enumerate(linhas) if nome in l)
                except StopIteration:
                    continue
                for linha in linhas[idx:idx+12]:
                    match = re.search(r'\(\d{2}\)\s*\d[\d\-\s]{7,}\d', linha)
                    if match:
                        return match.group(0).strip()
        except Exception:
            pass
        return ''
