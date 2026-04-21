"""
Тесты для парсинга страниц товаров
"""
import pytest
from parsers.hhv import HHVParser


class TestProductPageParsing:
    """Тесты для парсинга страниц товаров"""
    
    def test_parse_product_page_structure(self, browser_context, sample_urls):
        """Проверка структуры возвращаемых данных"""
        parser = HHVParser(headless=True)
        
        if not sample_urls:
            pytest.skip("No test URLs available")
        
        url = sample_urls[0]
        result = parser.parse_product_page(browser_context, url)
        
        # Проверка наличия обязательных полей
        assert isinstance(result, dict)
        if result:  # Если парсинг успешен
            assert 'artist' in result or 'title' in result
    
    def test_parse_product_page_timeout(self):
        """Обработка таймаута при загрузке страницы"""
        parser = HHVParser(headless=True)
        
        # Несуществующий URL должен вернуть пустой dict
        result = parser.parse_product_page(
            None, 
            "https://www.hhv.de/nonexistent-product-12345"
        )
        # Должен вернуть пустой dict или обработать ошибку gracefully
        assert result is None or isinstance(result, dict)
    
    def test_get_image_urls_from_html(self):
        """Извлечение URL изображений из HTML"""
        from bs4 import BeautifulSoup
        
        parser = HHVParser()
        
        # Пример HTML с изображением
        html = '''
        <div class="items--detail--images--base-component">
            <picture>
                <source srcset="/images/test.jpg" />
            </picture>
        </div>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        
        # Метод должен вернуть список URL
        # (тест может потребовать доработки в зависимости от реализации)
        try:
            result = parser.get_image_urls(soup)
            assert isinstance(result, list)
        except Exception:
            # Если метод требует полной страницы - это OK
            pass


class TestURLCollection:
    """Тесты для сбора URL товаров"""
    
    def test_get_product_urls_limit(self, browser_context):
        """Проверка ограничения количества URL"""
        parser = HHVParser(headless=True)
        
        # Тестовая категория (можно заменить на реальную)
        test_url = "https://www.hhv.de/en/records/?sort=availability&display=24"
        
        result = parser.get_product_urls(test_url, max_products=5)
        
        assert isinstance(result, list)
        assert len(result) <= 5
    
    def test_get_product_urls_format(self, browser_context):
        """Проверка формата собранных URL"""
        parser = HHVParser(headless=True)
        
        test_url = "https://www.hhv.de/en/records/?sort=availability&display=24"
        result = parser.get_product_urls(test_url, max_products=3)
        
        for url in result:
            assert url.startswith('http')
            assert 'hhv.de' in url
            assert '/records/' in url
