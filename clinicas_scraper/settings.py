BOT_NAME = 'clinicas_scraper'
SPIDER_MODULES = ['clinicas_scraper.spiders']
NEWSPIDER_MODULE = 'clinicas_scraper.spiders'

ROBOTSTXT_OBEY = True
DOWNLOAD_DELAY = 2
RANDOMIZE_DOWNLOAD_DELAY = True
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

ITEM_PIPELINES = {
    'clinicas_scraper.pipelines.ValidacaoPipeline': 100,
    'clinicas_scraper.pipelines.NormalizacaoPipeline': 200,
    'clinicas_scraper.pipelines.CsvExportPipeline': 300,
}

FEED_EXPORT_ENCODING = 'utf-8-sig'
LOG_LEVEL = 'INFO'

# Playwright handler
DOWNLOAD_HANDLERS = {
    'http': 'scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler',
    'https': 'scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler',
}

TWISTED_REACTOR = 'twisted.internet.asyncioreactor.AsyncioSelectorReactor'

PLAYWRIGHT_LAUNCH_OPTIONS = {
    'headless': True,
}
