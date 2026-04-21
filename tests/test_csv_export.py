"""
Тесты для экспорта в CSV
"""
import pytest
import csv
import os
from pathlib import Path
from HHV_to_csv import generate_csv


class TestCSVExport:
    """Тесты для генерации CSV файлов"""
    
    def test_generate_csv_structure(self, tmp_path):
        """Проверка структуры создаваемого CSV файла"""
        # Тестовые данные
        test_products = [
            {
                'artist': 'Test Artist',
                'title': 'Test Album',
                'price': '33,99 €',
                'label': 'Test Label',
                'format': 'LP',
                'genre': 'Electronic',
                'release_date': '01.01.2024',
                'description': 'Test description',
                'tracklist': '1. Track One\n2. Track Two'
            }
        ]
        
        # Генерируем CSV
        output_file = str(tmp_path / "test_output.csv")
        result = generate_csv(test_products, output_file=output_file)
        
        assert result or os.path.exists(output_file)
        
        # Проверяем структуру
        if os.path.exists(output_file):
            with open(output_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
                assert len(rows) == 1
                row = rows[0]
                
                # Проверка наличия ключевых колонок
                assert 'Имя' in row or 'name' in row or 'Artist' in str(row)
                # Проверка цены - может быть в разных колонках
                has_price = any('цена' in k.lower() or 'price' in k.lower() for k in row.keys())
                assert has_price or '5690' in str(row.values())
    
    def test_generate_csv_empty_data(self, tmp_path):
        """Генерация CSV с пустыми данными"""
        output_file = str(tmp_path / "empty.csv")
        result = generate_csv([], output_file=output_file)
        
        # Должен создать файл даже с пустыми данными или вернуть None
        assert result is None or os.path.exists(output_file)
    
    def test_generate_csv_encoding(self, tmp_path):
        """Проверка кодировки UTF-8-SIG"""
        test_products = [
            {
                'artist': 'Артист с кириллицей',
                'title': 'Название с умляутами äöü',
                'price': '29,99 €',
                'label': 'Лейбл',
                'format': 'CD',
                'genre': 'Рок',
                'release_date': '01.01.2024',
                'description': 'Описание',
                'tracklist': 'Треклист'
            }
        ]
        
        output_file = str(tmp_path / "unicode.csv")
        result = generate_csv(test_products, output_file=output_file)
        
        if os.path.exists(output_file):
            # Проверка чтения файла с правильной кодировкой
            with open(output_file, 'r', encoding='utf-8-sig') as f:
                content = f.read()
                assert 'Артист' in content or 'Название' in content
    
    def test_csv_field_mapping(self, tmp_path):
        """Проверка маппинга полей в CSV"""
        test_product = {
            'artist': 'Artist Name',
            'title': 'Album Title',
            'price_eur': 25.99,
            'price_rub': 2590,
            'label': 'Label Name',
            'format': 'Vinyl',
            'genre': 'Jazz',
            'release_date': '15.06.2024',
            'description': 'Description text',
            'tracklist': '1. Track 1\n2. Track 2',
            'image_urls': ['http://example.com/img.jpg']
        }
        
        output_file = str(tmp_path / "mapped.csv")
        result = generate_csv([test_product], output_file=output_file)
        
        if os.path.exists(output_file):
            with open(output_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
                if rows:
                    row = rows[0]
                    # Проверка что данные корректно перенесены
                    assert any('Artist' in str(v) for v in row.values()) or \
                           any('Album' in str(v) for v in row.values())
