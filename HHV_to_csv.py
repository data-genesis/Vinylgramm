import os
import csv
import json
import re
from pathlib import Path
import math
import logging

# Настройка логгера для HHV_to_csv.py
logger = logging.getLogger("HHV_to_csv")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

CONFIG_FILE = "config_price.json"
PARSED_FOLDER = "parsed"
OUTPUT_CSV = "HHV_test2.csv"
IMAGE_BASE_URL = "https://xn--b1albagkmm2ah6h.xn--p1ai/wp-content/uploads/2026/03/"
GENRE_MAPPING_FILE = "genre.md"

# --- Загрузка конфигурации цены ---
with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config = json.load(f)

CURRENCY = config.get("currency", "RUB")
EUR_TO_RUB = config.get("usd_to_rub", 90.0)  # используем как EUR_TO_RUB
ADD_EUR = config.get("add_usd", [2, 10])
PERCENT_MARKUP = config.get("percent_markup", 50)
ADD_RUB = config.get("add_rub", 150)
ROUND_TO_LAST = config.get("round_to_last_digits", 90)

def parse_price_eur(price_str: str):
    """
    Парсинг цены в евро: '33,99 €' → 33.99
    """
    if not price_str or price_str == "N/A":
        return None
    
    # Убираем символы валюты и пробелы
    clean = re.sub(r'[^\d,.]', '', price_str)
    # Заменяем запятую на точку
    clean = clean.replace(',', '.')
    
    try:
        return float(clean)
    except:
        return None


def calculate_price(price_eur: float):
    """
    Формула расчета цены:
    1. base_eur + random(add_eur)
    2. * EUR_TO_RUB
    3. * (1 + markup%)
    4. + add_rub
    5. Округление до round_to_last
    """
    if price_eur is None:
        return None
    
    # Логирование нулевой или отрицательной цены
    if price_eur <= 0:
        logger.warning(f"У товара нет цены (price_eur={price_eur})")
        return None
    
    import random
    add_eur_value = random.uniform(ADD_EUR[0], ADD_EUR[1])
    
    # Шаг 1: добавляем к цене
    step1 = price_eur + add_eur_value
    
    # Шаг 2: конвертируем в рубли
    step2 = step1 * EUR_TO_RUB
    
    # Шаг 3: наценка в процентах
    step3 = step2 * (1 + PERCENT_MARKUP / 100)
    
    # Шаг 4: добавляем рубли
    step4 = step3 + ADD_RUB
    
    # Шаг 5: округление
    rounded = math.ceil(step4 / 100) * 100
    final_price = rounded - (100 - ROUND_TO_LAST)
    
    return int(final_price)


def parse_info_txt(info_path: Path):
    """Парсинг info.txt"""
    data = {}
    current_key = None
    current_value = []
    
    with open(info_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            
            # Проверяем ключ: строка
            if ':' in line and not line.startswith(' '):
                # Сохраняем предыдущий ключ
                if current_key:
                    data[current_key] = '\n'.join(current_value).strip()
                
                key, value = line.split(':', 1)
                current_key = key.strip().lower()
                current_value = [value.strip()] if value.strip() else []
            else:
                # Продолжение значения
                if line.strip():
                    current_value.append(line.strip())
        
        # Сохраняем последний ключ
        if current_key:
            data[current_key] = '\n'.join(current_value).strip()
    
    return data


def load_genre_mapping(genre_file: str):
    """
    Загрузка маппинга жанров из genre.md
    Возвращает словарь: {категория: [список стилей]}
    """
    genre_map = {}
    current_category = None
    
    with open(genre_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            
            # Пропускаем пустые строки
            if not line:
                continue
            
            # Главная категория (заголовок)
            if line.startswith('# '):
                current_category = line[2:].strip()
                genre_map[current_category] = []
            
            # Стиль (элемент списка)
            elif line.startswith('- ') and current_category:
                style = line[2:].strip()
                genre_map[current_category].append(style)
    
    return genre_map


def find_genre_match(genre_str: str, genre_map: dict):
    """
    Поиск соответствия жанра в маппинге по ключевым словам
    Возвращает: (категория, стиль) или (категория, None) или (None, None)
    """
    genre_lower = genre_str.lower().strip()
    
    # Сначала ищем в категориях
    for category in genre_map.keys():
        category_keywords = category.lower().split()
        
        # Проверяем все ключевые слова категории
        if any(keyword in genre_lower for keyword in category_keywords):
            # Теперь ищем стиль
            for style in genre_map[category]:
                style_keywords = style.lower().split()
                
                # Проверяем совпадение стиля
                if any(keyword in genre_lower for keyword in style_keywords):
                    return (category, style)
            
            # Категория найдена, но стиль нет
            return (category, None)
    
    return (None, None)


def process_genres(genre_str: str, genre_map: dict):
    """
    Обработка строки жанров из info.txt
    Возвращает строку для поля "Категории" или "Без категории"
    """
    if not genre_str or genre_str == "N/A":
        return "Без категории"
    
    # Разбиваем по запятой
    genres = [g.strip() for g in genre_str.split(',')]
    
    # Словарь для группировки: {категория: стиль или None}
    category_style_map = {}
    
    for genre in genres:
        category, style = find_genre_match(genre, genre_map)
        
        if category:
            # Берем только первый стиль для каждой категории
            if category not in category_style_map:
                category_style_map[category] = style
    
    # Если ничего не нашли
    if not category_style_map:
        return "Без категории"
    
    # Формируем строку результата
    result_parts = []
    for category, style in category_style_map.items():
        if style:
            # Формат: "Категория > Стиль, Категория"
            result_parts.append(f"{category} > {style}, {category}")
        else:
            # Только категория
            result_parts.append(category)
    
    return ", ".join(result_parts)


def generate_csv(products=None, output_file=None):
    """Генерация CSV файла
    
    Args:
        products: Список словарей с данными товаров (опционально)
        output_file: Путь к выходному файлу (опционально)
    
    Если продукты не переданы, читает из папки parsed/
    """
    # Если продукты переданы напрямую - используем их
    if products is not None:
        return _generate_csv_from_products(products, output_file or OUTPUT_CSV)
    
    # Загрузка маппинга жанров
    try:
        genre_map = load_genre_mapping(GENRE_MAPPING_FILE)
        print(f"✅ Загружен маппинг жанров: {len(genre_map)} категорий")
    except Exception as e:
        print(f"⚠️ Ошибка загрузки {GENRE_MAPPING_FILE}: {e}")
        genre_map = {}
    
    parsed_path = Path(PARSED_FOLDER)
    
    if not parsed_path.exists():
        print(f"❌ Папка {PARSED_FOLDER} не найдена")
        return
    
    product_folders = [f for f in parsed_path.iterdir() if f.is_dir()]
    
    if not product_folders:
        print(f"❌ Нет товаров в {PARSED_FOLDER}")
        return
    
    print(f"📦 Найдено товаров: {len(product_folders)}")
    
    # Заголовки CSV (скопированы из example-2.csv)
    headers = [
    "ID", "Тип", "Артикул", "GTIN, UPC, EAN или ISBN", "Имя", "Опубликован",
    "Рекомендуемый?", "Видимость в каталоге", "Краткое описание", "Описание",
    "Дата начала действия скидки", "Дата окончания действия скидки",
    "Статус налога", "Налоговый класс", "Наличие", "Запасы", "Величина малых запасов",
    "Возможен ли предзаказ?", "Продано индивидуально?", "Вес (г)", "Длина (см)",
    "Ширина (см)", "Высота (см)", "Разрешить отзывы от клиентов?",
    "Примечание к покупке", "Акционная цена", "Базовая цена", "Категории",
    "Метки", "Класс доставки", "Изображения", "Лимит скачивания",
    "Дней срока скачивания", "Родительский", "Сгруппированные товары",
    "Апсэлы", "Кросселы", "Внешний URL", "Текст кнопки", "Позиция", "Бренды",
    "Название атрибута 1", "Значения атрибутов 1", "Видимость атрибута 1",
    "Глобальный атрибут 1", "Название атрибута 2", "Значения атрибутов 2",
    "Видимость атрибута 2", "Глобальный атрибут 2", "Название атрибута 3",
    "Значения атрибутов 3", "Видимость атрибута 3", "Глобальный атрибут 3",
    "Название атрибута 4", "Значения атрибутов 4", "Видимость атрибута 4",
    "Глобальный атрибут 4", "Название атрибута 5", "Значения атрибутов 5",
    "Видимость атрибута 5", "Глобальный атрибут 5", "Название атрибута 6",
    "Значения атрибутов 6", "Видимость атрибута 6", "Глобальный атрибут 6",
    "Название атрибута 7", "Значения атрибутов 7", "Видимость атрибута 7",  # ← ДОБАВЬТЕ
    "Глобальный атрибут 7", "Название атрибута 8", "Значения атрибутов 8",
    "Видимость атрибута 8", "Глобальный атрибут 8"
]

    
    rows = []
    
    for folder in product_folders:
        info_file = folder / "info.txt"
        
        if not info_file.exists():
            print(f"⚠️ Нет info.txt в {folder.name}")
            continue
        
        data = parse_info_txt(info_file)
        
        # Извлекаем данные
        artist = data.get('artist', 'Unknown')
        title = data.get('title', 'Untitled')
        price_str = data.get('price', '')
        label = data.get('label', '')
        format_info = data.get('format', '')
        release_date = data.get('release_date', 'Уже в продаже')
        source_url = data.get('source url', '')
        genre = data.get('genre', '')
        
        # Имя товара
        product_name = f"{artist} - {title}"
        
        # Расчет цены
        price_eur = parse_price_eur(price_str)
        final_price = calculate_price(price_eur) if price_eur else ""
        
        # Обработка категорий
        categories = process_genres(genre, genre_map)
        
        # Изображения
        downloaded_images_str = data.get('downloaded_images', '')
        image_files = [line.strip() for line in downloaded_images_str.split('\n') if line.strip()]
        image_urls = [IMAGE_BASE_URL + img for img in image_files]
        images_csv = ", ".join(image_urls)
        
        # Формируем строку
        row = {
            "ID": "",
            "Тип": "simple",
            "Артикул": "",
            "GTIN, UPC, EAN или ISBN": "",
            "Имя": product_name,
            "Опубликован": "1",
            "Рекомендуемый?": "0",
            "Видимость в каталоге": "visible",
            "Краткое описание": "",
            "Описание": "",
            "Дата начала действия скидки": "",
            "Дата окончания действия скидки": "",
            "Статус налога": "taxable",
            "Налоговый класс": "",
            "Наличие": "backorder",
            "Запасы": "",
            "Величина малых запасов": "",
            "Возможен ли предзаказ?": "0",
            "Продано индивидуально?": "0",
            "Вес (г)": "",
            "Длина (см)": "",
            "Ширина (см)": "",
            "Высота (см)": "",
            "Разрешить отзывы от клиентов?": "0",
            "Примечание к покупке": "",
            "Акционная цена": "",
            "Базовая цена": final_price,
            "Категории": categories,
            "Метки": "",
            "Класс доставки": "",
            "Изображения": images_csv,
            "Лимит скачивания": "",
            "Дней срока скачивания": "",
            "Родительский": "",
            "Сгруппированные товары": "",
            "Апсэлы": "",
            "Кросселы": "",
            "Внешний URL": "",
            "Текст кнопки": "",
            "Позиция": "0",
            "Бренды": "",
            "Название атрибута 1": "Лейбл",
            "Значения атрибутов 1": label,
            "Видимость атрибута 1": "1",
            "Глобальный атрибут 1": "1",
            "Название атрибута 2": "Состояние",
            "Значения атрибутов 2": "Новый",
            "Видимость атрибута 2": "1",
            "Глобальный атрибут 2": "1",
            "Название атрибута 3": "Формат",
            "Значения атрибутов 3": format_info,
            "Видимость атрибута 3": "1",
            "Глобальный атрибут 3": "0",
            "Название атрибута 4": "Исполнитель",
            "Значения атрибутов 4": artist,
            "Видимость атрибута 4": "1",
            "Глобальный атрибут 4": "1",
            "Название атрибута 5": "Дата старта продаж",
            "Значения атрибутов 5": release_date,
            "Видимость атрибута 5": "1",
            "Глобальный атрибут 5": "0",
            "Название атрибута 6": "Треклист",
            "Значения атрибутов 6": data.get('tracklist', 'Нет треклиста').replace('\n', '<br>'),
            "Видимость атрибута 6": "0",
            "Глобальный атрибут 6": "0",
            "Название атрибута 7": "Ссылка на товар",
            "Значения атрибутов 7": source_url,
            "Видимость атрибута 7": "0",
            "Глобальный атрибут 7": "0",
            "Название атрибута 8": "Цена на сайте",
            "Значения атрибутов 8": price_str,
            "Видимость атрибута 8": "0",
            "Глобальный атрибут 8": "0",

        }
        
        rows.append(row)
        print(f"✅ {product_name} → {final_price} RUB")
    
    # Запись в CSV
    output_path = output_file or OUTPUT_CSV
    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"\n🎉 CSV создан: {output_path}")
    print(f"📊 Товаров: {len(rows)}")
    return output_path


def _generate_csv_from_products(products, output_file):
    """Внутренняя функция для генерации CSV из списка продуктов"""
    if not products:
        logger.warning("Пустой список продуктов для CSV")
        return None
    
    # Загрузка маппинга жанров
    try:
        genre_map = load_genre_mapping(GENRE_MAPPING_FILE)
    except Exception as e:
        logger.warning(f"Ошибка загрузки {GENRE_MAPPING_FILE}: {e}")
        genre_map = {}
    
    # Заголовки CSV
    headers = [
    "ID", "Тип", "Артикул", "GTIN, UPC, EAN или ISBN", "Имя", "Опубликован",
    "Рекомендуемый?", "Видимость в каталоге", "Краткое описание", "Описание",
    "Дата начала действия скидки", "Дата окончания действия скидки",
    "Статус налога", "Налоговый класс", "Наличие", "Запасы", "Величина малых запасов",
    "Возможен ли предзаказ?", "Продано индивидуально?", "Вес (г)", "Длина (см)",
    "Ширина (см)", "Высота (см)", "Разрешить отзывы от клиентов?",
    "Примечание к покупке", "Акционная цена", "Базовая цена", "Категории",
    "Метки", "Класс доставки", "Изображения", "Лимит скачивания",
    "Дней срока скачивания", "Родительский", "Сгруппированные товары",
    "Апсэлы", "Кросселы", "Внешний URL", "Текст кнопки", "Позиция", "Бренды",
    "Название атрибута 1", "Значения атрибутов 1", "Видимость атрибута 1",
    "Глобальный атрибут 1", "Название атрибута 2", "Значения атрибутов 2",
    "Видимость атрибута 2", "Глобальный атрибут 2", "Название атрибута 3",
    "Значения атрибутов 3", "Видимость атрибута 3", "Глобальный атрибут 3",
    "Название атрибута 4", "Значения атрибутов 4", "Видимость атрибута 4",
    "Глобальный атрибут 4", "Название атрибута 5", "Значения атрибутов 5",
    "Видимость атрибута 5", "Глобальный атрибут 5", "Название атрибута 6",
    "Значения атрибутов 6", "Видимость атрибута 6", "Глобальный атрибут 6",
    "Название атрибута 7", "Значения атрибутов 7", "Видимость атрибута 7",
    "Глобальный атрибут 7", "Название атрибута 8", "Значения атрибутов 8",
    "Видимость атрибута 8", "Глобальный атрибут 8",
    ]
    
    rows = []
    
    for product in products:
        artist = product.get('artist', 'Unknown')
        title = product.get('title', 'Untitled')
        price_str = product.get('price', '')
        label = product.get('label', '')
        format_info = product.get('format', '')
        release_date = product.get('release_date', 'Уже в продаже')
        genre = product.get('genre', '')
        description = product.get('description', '')
        tracklist = product.get('tracklist', '')
        image_urls = product.get('image_urls', [])
        
        product_name = f"{artist} - {title}"
        
        # Расчет цены
        price_eur = parse_price_eur(price_str)
        final_price = calculate_price(price_eur) if price_eur else ""
        
        # Обработка категорий
        categories = process_genres(genre, genre_map)
        
        # Изображения
        images_csv = ", ".join(image_urls) if isinstance(image_urls, list) else str(image_urls)
        
        row = {
            "ID": "",
            "Тип": "simple",
            "Артикул": "",
            "GTIN, UPC, EAN или ISBN": "",
            "Имя": product_name,
            "Опубликован": "1",
            "Рекомендуемый?": "0",
            "Видимость в каталоге": "visible",
            "Краткое описание": "",
            "Описание": description,
            "Дата начала действия скидки": "",
            "Дата окончания действия скидки": "",
            "Статус налога": "taxable",
            "Налоговый класс": "",
            "Наличие": "backorder",
            "Запасы": "",
            "Величина малых запасов": "",
            "Возможен ли предзаказ?": "0",
            "Продано индивидуально?": "0",
            "Вес (г)": "",
            "Длина (см)": "",
            "Ширина (см)": "",
            "Высота (см)": "",
            "Разрешить отзывы от клиентов?": "0",
            "Примечание к покупке": "",
            "Акционная цена": "",
            "Базовая цена": final_price,
            "Категории": categories,
            "Метки": "",
            "Класс доставки": "",
            "Изображения": images_csv,
            "Лимит скачивания": "",
            "Дней срока скачивания": "",
            "Родительский": "",
            "Сгруппированные товары": "",
            "Апсэлы": "",
            "Кросселы": "",
            "Внешний URL": "",
            "Текст кнопки": "",
            "Позиция": "0",
            "Бренды": label,
            "Название атрибута 1": "Формат",
            "Значения атрибутов 1": format_info,
            "Видимость атрибута 1": "1",
            "Глобальный атрибут 1": "0",
            "Название атрибута 2": "Лейбл",
            "Значения атрибутов 2": label,
            "Видимость атрибута 2": "1",
            "Глобальный атрибут 2": "0",
            "Название атрибута 3": "Дата релиза",
            "Значения атрибутов 3": release_date,
            "Видимость атрибута 3": "1",
            "Глобальный атрибут 3": "0",
            "Название атрибута 4": "Жанр",
            "Значения атрибутов 4": genre,
            "Видимость атрибута 4": "1",
            "Глобальный атрибут 4": "0",
            "Название атрибута 5": "Описание",
            "Значения атрибутов 5": description.replace('\n', '<br>'),
            "Видимость атрибута 5": "0",
            "Глобальный атрибут 5": "0",
            "Название атрибута 6": "Треклист",
            "Значения атрибутов 6": tracklist.replace('\n', '<br>') if tracklist else "Нет треклиста",
            "Видимость атрибута 6": "0",
            "Глобальный атрибут 6": "0",
            "Название атрибута 7": "Ссылка на товар",
            "Значения атрибутов 7": product.get('source_url', ''),
            "Видимость атрибута 7": "0",
            "Глобальный атрибут 7": "0",
            "Название атрибута 8": "Цена на сайте",
            "Значения атрибутов 8": price_str,
            "Видимость атрибута 8": "0",
            "Глобальный атрибут 8": "0",
        }
        
        rows.append(row)
        logger.info(f"{product_name} → {final_price} RUB")
    
    # Запись в CSV
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    
    logger.info(f"CSV создан: {output_file}, товаров: {len(rows)}")
    return output_file


if __name__ == "__main__":
    generate_csv()
