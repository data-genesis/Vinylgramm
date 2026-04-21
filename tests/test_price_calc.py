"""
Тесты для расчёта цены и парсинга цен
"""
import pytest
import sys
sys.path.append('/workspace')

# Функции находятся в HHV_to_csv.py, а не в HHVParser
from HHV_to_csv import parse_price_eur, calculate_price
from parsers.hhv import HHVParser


class TestPriceCalculation:
    """Тесты для функций расчёта цены"""
    
    def test_parse_price_eur_valid(self):
        """Парсинг корректной цены в евро"""
        # Тест различных форматов цен
        assert parse_price_eur('33,99 €') == 33.99
        assert parse_price_eur('19,99€') == 19.99
        assert parse_price_eur('€ 25,50') == 25.50
        assert parse_price_eur('9,90 EUR') == 9.90
    
    def test_parse_price_eur_invalid(self):
        """Парсинг некорректных значений"""
        assert parse_price_eur(None) is None
        assert parse_price_eur('') is None
        assert parse_price_eur('N/A') is None
        assert parse_price_eur('Sold Out') is None
    
    def test_calculate_price_basic(self):
        """Базовый расчёт финальной цены"""
        # Цена 33.99 EUR с наценкой
        result = calculate_price(33.99)
        assert isinstance(result, float)
        assert result > 33.99  # Цена должна быть выше из-за наценки
    
    def test_calculate_price_edge_cases(self):
        """Граничные значения расчёта цены"""
        # None цена
        assert calculate_price(None) is None
        
        # Нулевая цена
        result_zero = calculate_price(0)
        assert result_zero is None or result_zero == 0
        
        # Отрицательная цена (должна возвращать None)
        assert calculate_price(-10) is None
    
    def test_calculate_price_rounding(self):
        """Проверка округления до 90"""
        # Цены должны округляться до ...90
        test_prices = [10.5, 25.3, 100.1]
        for price in test_prices:
            result = calculate_price(price)
            if result:
                # Последняя цифра перед десятичной точкой должна быть 9
                last_digit = int(result % 10)
                assert last_digit == 9 or result == round(result, -1)


class TestGenreMapping:
    """Тесты для маппинга жанров"""
    
    def test_load_genre_mapping(self):
        """Загрузка файла маппинга жанров"""
        parser = HHVParser()
        
        mapping = parser.load_genre_mapping()
        assert isinstance(mapping, dict)
        assert len(mapping) > 0
    
    def test_find_genre_match(self):
        """Поиск соответствия жанра"""
        parser = HHVParser()
        
        # Точное совпадение
        result = parser.find_genre_match('Techno', {'techno': ['Electronic']})
        assert result == ['Electronic']
        
        # Совпадение без учёта регистра
        result = parser.find_genre_match('TECHNO', {'techno': ['Electronic']})
        assert result == ['Electronic']
        
        # Отсутствие совпадения
        result = parser.find_genre_match('Unknown', {'techno': ['Electronic']})
        assert result is None
    
    def test_process_genres(self):
        """Обработка строки жанров"""
        parser = HHVParser()
        
        # Простая обработка
        result = parser.process_genres('Techno, House')
        assert isinstance(result, str)
        
        # Пустая строка
        result = parser.process_genres('')
        assert result == '' or result is None
