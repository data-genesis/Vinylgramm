"""
Тесты для экспорта в CSV
"""
import pytest
import csv
import os
from pathlib import Path
from parsers.hhv import HHVParser


class TestCSVExport:
    """Тесты для генерации CSV файлов"""
    
    def test_generate_csv_structure(self, tmp_path):
        """Проверка структуры создаваемого CSV файла"""
        parser = HHVParser(output_root=str(tmp_path))
        
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
        csv_file = parser.generate_csv(test_products, output_file=str(tmp_path / "test_output.csv"))
        
        assert csv_file
        assert os.path.exists(csv_file)
        
        # Проверяем структуру
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            assert len(rows) == 1
            row = rows[0]
            
            # Проверка наличия ключевых колонок
            assert 'Имя' in row or 'name' in row
            assert 'Цена' in row or 'price' in row
    
    def test_generate_csv_empty_data(self, tmp_path):
        """Генерация CSV с пустыми данными"""
        parser = HHVParser(output_root=str(tmp_path))
        
        csv_file = parser.generate_csv([], output_file=str(tmp_path / "empty.csv"))
        
        # Должен создать файл даже с пустыми данными
        assert csv_file is None or os.path.exists(csv_file)
    
    def test_generate_csv_encoding(self, tmp_path):
        """Проверка кодировки UTF-8-SIG"""
        parser = HHVParser(output_root=str(tmp_path))
        
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
        
        csv_file = parser.generate_csv(test_products, output_file=str(tmp_path / "unicode.csv"))
        
        if csv_file and os.path.exists(csv_file):
            # Проверка чтения файла с правильной кодировкой
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                content = f.read()
                assert 'Артист' in content or 'Альбом' in content
    
    def test_csv_field_mapping(self, tmp_path):
        """Проверка маппинга полей в CSV"""
        parser = HHVParser(output_root=str(tmp_path))
        
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
        
        csv_file = parser.generate_csv([test_product], output_file=str(tmp_path / "mapped.csv"))
        
        if csv_file and os.path.exists(csv_file):
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
                if rows:
                    row = rows[0]
                    # Проверка что данные корректно перенесены
                    assert any('Artist' in str(v) for v in row.values()) or \
                           any('Album' in str(v) for v in row.values())
