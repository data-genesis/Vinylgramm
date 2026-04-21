"""
Фикстуры для тестов парсера HHV
"""
import pytest
from pathlib import Path
from playwright.sync_api import sync_playwright

# Путь к тестовым данным
TEST_DIR = Path(__file__).parent.parent
TEST_URLS_FILE = TEST_DIR / "TEST.txt"
TEST_CSV_SAMPLE = TEST_DIR / "HHV_test2.csv"


@pytest.fixture(scope="session")
def sample_urls():
    """Загрузка URL из TEST.txt"""
    if not TEST_URLS_FILE.exists():
        pytest.skip(f"Test file {TEST_URLS_FILE} not found")
    
    with open(TEST_URLS_FILE, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip() and line.startswith('http')]
    
    # Возвращаем первые 3 URL для быстрого тестирования
    return urls[:3]


@pytest.fixture(scope="session")
def expected_csv_columns():
    """Ожидаемые колонки CSV на основе образца"""
    return [
        'Имя', 'Артикул', 'Цена', 'Старая цена', 'Количество', 
        'Единица измерения количества', 'Минимальное количество в заказе',
        'Кратность количества в заказе', 'Полное описание', 'Аннотация',
        'Значения атрибутов 1', 'Значения атрибутов 2', 'Значения атрибутов 3',
        'Значения атрибутов 4', 'Значения атрибутов 5', 'Значения атрибутов 6',
        'Значения атрибутов 7', 'Значения атрибутов 8'
    ]


@pytest.fixture(scope="function")
def browser_context():
    """Создание контекста браузера Playwright для тестов"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()
        yield page
        context.close()
        browser.close()


@pytest.fixture
def test_product_data():
    """Тестовые данные продукта для проверки расчётов"""
    return {
        'artist': 'Test Artist',
        'title': 'Test Album',
        'price': '33,99 €',
        'label': 'Test Label',
        'format': 'LP',
        'genre': 'Electronic',
        'release_date': '01.01.2024'
    }


@pytest.fixture
def genre_mapping_sample():
    """Пример маппинга жанров для тестирования"""
    return {
        'electronic & dance': ['Techno', 'House', 'Trance'],
        'rock & indie': ['Rock', 'Indie', 'Alternative'],
        'organic grooves': ['Soul', 'Funk', 'Disco']
    }
