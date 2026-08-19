import csv
import os
import re
from datetime import datetime

from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem


class ValidacaoPipeline:
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        nome = adapter.get('nome', '').strip()
        telefone = adapter.get('telefone', '').strip()
        site = adapter.get('site', '').strip()
        if not nome or (not telefone and not site):
            spider.logger.warning(f"Item descartado: {dict(adapter)}")
            raise DropItem(f"nome/telefone/site insuficientes: {dict(adapter)}")
        return item


class NormalizacaoPipeline:
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        telefone = adapter.get('telefone', '')
        if telefone:
            adapter['telefone'] = re.sub(r'\D', '', telefone)
        nome = adapter.get('nome', '')
        if nome:
            adapter['nome'] = nome.strip().title()
        if not adapter.get('categoria'):
            adapter['categoria'] = 'Clinica Odontologica'
        return item


class CsvExportPipeline:
    def __init__(self):
        self.file = None
        self.writer = None
        self.output_path = None

    def open_spider(self, spider):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{spider.name}_{timestamp}.csv"
        output_dir = getattr(spider, 'output_dir', '/root/Comercial Estructure/Base de Clinicas Odonto')
        os.makedirs(output_dir, exist_ok=True)
        self.output_path = os.path.join(output_dir, filename)
        spider.logger.info(f"CSV: {self.output_path}")
        self.file = open(self.output_path, 'w', newline='', encoding='utf-8-sig')
        self.writer = None

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        row = dict(adapter)
        if self.writer is None:
            self.writer = csv.DictWriter(self.file, fieldnames=row.keys())
            self.writer.writeheader()
        self.writer.writerow(row)
        return item

    def close_spider(self, spider):
        if self.file:
            self.file.close()
            spider.logger.info(f"Planilha salva: {self.output_path}")
