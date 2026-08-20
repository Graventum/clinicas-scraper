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

            # pilar 1: reputacao e volume
            reviews = await self._extract_reviews(page)
            item['qtd_reviews'] = reviews['qtd']
            item['estrelas'] = reviews['estrelas']

            # pilar 2: infraestrutura
            fotos = await self._extract_photos(page)
            item['qtd_fotos'] = fotos['qtd']
            item['urls_fotos'] = fotos['urls']

            # pilar 3: porte/organizacao
            item['horario_funcionamento'] = await self._extract_hours(page)

            # pilar 5: alto ticket
            servicos = await self._extract_services(page)
            item['especialidades'] = servicos['especialidades']
            item['servicos'] = servicos['servicos']

            return item
        except Exception as e:
            self.logger.warning(f"Erro painel: {e}")
            return None

    async def _extract_reviews(self, page):
        resultado = {'qtd': '', 'estrelas': ''}
        try:
            # estrategia 1: aria-label da estrela
            estrela = await page.query_selector('span[role="img"][aria-label*="estrela"], span[role="img"][aria-label*="stars"], img[alt*="estrela"]')
            if estrela:
                aria = await estrela.get_attribute('aria-label') or ''
                match = re.search(r'([\d,]+)', aria.replace('.', ','))
                if match:
                    resultado['estrelas'] = match.group(1).replace(',', '.')

            # estrategia 2: texto visivel no painel lateral
            texto = await page.evaluate(r'''() => {
                const painel = document.querySelector('div[role="main"]') || document.body;
                return painel.innerText || '';
            }''')

            if not resultado['estrelas']:
                # procura "4,5" seguido proximo de avaliacoes
                m = re.search(r'([\d,]+)\s*\(\s*(\d+)\s*(avaliações|avaliação|reviews|review)', texto, re.IGNORECASE)
                if m:
                    resultado['estrelas'] = m.group(1).replace(',', '.')
                    resultado['qtd'] = m.group(2)
                else:
                    # so quantidade de avaliacoes
                    m2 = re.search(r'(\d+)\s*(avaliações|avaliação|reviews|review)', texto, re.IGNORECASE)
                    if m2:
                        resultado['qtd'] = m2.group(1)

            # se estrelas encontrada mas nao qtd
            if resultado['estrelas'] and not resultado['qtd']:
                m3 = re.search(r'\(\s*(\d+)\s*(avaliações|avaliação|reviews|review)', texto, re.IGNORECASE)
                if m3:
                    resultado['qtd'] = m3.group(1)

            # ultimo fallback: numero logo antes da palavra avaliacoes
            if not resultado['qtd']:
                m4 = re.search(r'(\d{1,6})\s*(?:avaliações|avaliação|reviews|review)', texto, re.IGNORECASE)
                if m4:
                    resultado['qtd'] = m4.group(1)

        except Exception as e:
            self.logger.warning(f"Erro reviews: {e}")
        return resultado

    async def _extract_photos(self, page):
        resultado = {'qtd': '', 'urls': ''}
        try:
            # conta thumbnails visiveis no painel
            fotos = await page.query_selector_all('div[role="main"] button img, div[role="main"] img')
            urls = []
            for f in fotos[:10]:
                src = await f.get_attribute('src') or ''
                if src and 'googleusercontent' in src and src not in urls:
                    urls.append(src)
            resultado['urls'] = ' | '.join(urls[:5])

            # tenta extrair contagem textual "X fotos"
            texto = await page.evaluate(r'''() => {
                const painel = document.querySelector('div[role="main"]') || document.body;
                return painel.innerText || '';
            }''')
            m = re.search(r'(\d+)\s*(fotos|foto)', texto, re.IGNORECASE)
            if m:
                resultado['qtd'] = m.group(1)
            else:
                resultado['qtd'] = str(len(urls))
        except Exception as e:
            self.logger.warning(f"Erro fotos: {e}")
        return resultado

    async def _extract_hours(self, page):
        try:
            # botao de horario
            btn = await page.query_selector('button[data-item-id="oh"], button[aria-label*="horário"], button[aria-label*="Horário"]')
            if btn:
                label = await btn.get_attribute('aria-label') or ''
                return label.replace('Horário:', '').strip()

            # texto visivel com horarios
            texto = await page.evaluate(r'''() => {
                const painel = document.querySelector('div[role="main"]') || document.body;
                return painel.innerText || '';
            }''')

            # procura padrao "segunda-feira", "aberto 24 horas", etc
            linhas = texto.split('\n')
            horarios = []
            for i, linha in enumerate(linhas):
                if re.search(r'(segunda|terça|quarta|quinta|sexta|sábado|domingo|aberto|fechado)', linha, re.IGNORECASE):
                    horarios.append(linha.strip())
                    if i + 1 < len(linhas) and re.search(r'\d{1,2}:\d{2}', linhas[i + 1]):
                        horarios.append(linhas[i + 1].strip())
            return ' | '.join(horarios[:14])
        except Exception as e:
            self.logger.warning(f"Erro horario: {e}")
            return ''

    async def _extract_services(self, page):
        resultado = {'especialidades': '', 'servicos': ''}
        try:
            texto = await page.evaluate(r'''() => {
                const painel = document.querySelector('div[role="main"]') || document.body;
                return painel.innerText || '';
            }''')

            # termos de alto ticket em odonto
            termos_alto_ticket = [
                'implante', 'implantes', 'ortodontia', 'invisalign', 'aparelho invisivel',
                'lente de contato dental', 'faceta', 'facetas', 'coroa', 'protese',
                'prótese', 'reabilitacao oral', 'cirurgia', 'periodontia', 'endodontia',
                'canal', 'clareamento', 'botox', 'preenchimento', 'harmonizacao'
            ]
            encontrados = []
            for termo in termos_alto_ticket:
                if re.search(rf'\b{re.escape(termo)}\b', texto, re.IGNORECASE):
                    encontrados.append(termo)
            resultado['especialidades'] = ' | '.join(encontrados)

            # se houver secao "Sobre" ou "Servicos", tenta pegar lista
            servicos = []
            if 'Sobre' in texto:
                idx = texto.find('Sobre')
                bloco = texto[idx:idx + 2000]
                linhas = [l.strip() for l in bloco.split('\n') if l.strip() and len(l.strip()) > 2]
                servicos = linhas[1:20]
            resultado['servicos'] = ' | '.join(servicos[:15])
        except Exception as e:
            self.logger.warning(f"Erro servicos: {e}")
        return resultado

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
