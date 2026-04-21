# Инструкция по тестированию HHV Parser после миграции на Playwright

## ✅ Что было сделано:

1. **Замена ChromeDriver на Playwright**
   - Все методы `driver.*` заменены на `page.*`
   - Удалены зависимости: `selenium`, `webdriver-manager`
   - Добавлены: `playwright`, `pytest`, `pytest-playwright`

2. **Улучшено логирование**
   - Создан модуль `utils/logging_config.py`
   - Отдельный лог для критических ошибок (`critical_errors.log`)
   - Ротация логов (10MB, 5 файлов)

3. **Написаны тесты**
   - `tests/test_price_calc.py` — тесты расчёта цены
   - `tests/test_parser_page.py` — тесты парсинга страниц
   - `tests/test_csv_export.py` — тесты экспорта CSV
   - `tests/conftest.py` — фикстуры pytest

4. **Docker-образ**
   - `Dockerfile` для Ubuntu 24.04
   - Включает все зависимости Playwright

---

## 🧪 Как протестировать:

### 1. Быстрая проверка импорта (локально)
```bash
cd /workspace
python -c "from parsers.hhv import HHVParser; print('✅ Import OK')"
```

### 2. Установка браузеров Playwright
```bash
playwright install chromium
```

### 3. Запуск тестов (локально на Mac)
```bash
# Запустить все тесты
pytest tests/ -v

# Запустить только тесты цен (быстро, без браузера)
pytest tests/test_price_calc.py -v

# Запустить тесты с покрытием
pytest tests/ --cov=parsers --cov-report=html

# Запустить один конкретный тест
pytest tests/test_price_calc.py::TestPriceCalculation::test_parse_price_eur_valid -v
```

### 4. Тестирование парсинга (реальный запрос)
```bash
# Создать файл с тестовыми URL (если нет)
echo "https://www.hhv.de/en/records/item/test-product-123" > TEST.txt

# Запустить парсер с ограничением 1 товар
python HHV_to_csv.py --urls TEST.txt --limit 1 --headless
```

### 5. Проверка логов
После запуска проверьте файлы:
```bash
ls -la *.log
cat parser.log | tail -50  # Последние записи
cat critical_errors.log    # Критические ошибки (если есть)
```

### 6. Тестирование в Docker (для Ubuntu сервера)
```bash
# Сборка образа
docker build -t hhv-parser .

# Запуск тестов в контейнере
docker run --rm hhv-parser pytest tests/test_price_calc.py -v

# Запуск парсера в контейнере
docker run --rm -v $(pwd)/output:/app/parsed hhv-parser \
    python3 HHV_to_csv.py --urls TEST.txt --limit 5
```

---

## 📋 Чек-лист проверки:

- [ ] Импорт модулей работает без ошибок
- [ ] `pytest tests/test_price_calc.py` — все тесты проходят
- [ ] Парсинг 1-2 товаров работает (ручной тест)
- [ ] Логи создаются и записываются
- [ ] CSV файл генерируется с правильной кодировкой
- [ ] Ошибки не ломают весь парсинг (graceful degradation)
- [ ] Docker-образ собирается без ошибок

---

## ⚠️ Возможные проблемы и решения:

### Ошибка "Executable not found"
```bash
playwright install chromium
playwright install-deps chromium
```

### Ошибка капчи при парсинге
- Проверьте `critical_errors.log`
- Увеличьте задержки между запросами
- Используйте прокси при необходимости

### Тесты падают с TimeoutError
- Увеличьте таймаут в `conftest.py`
- Проверьте сетевое подключение
- Используйте headless режим

---

## 📊 Критерии успешного завершения:

1. ✅ Все unit-тесты проходят (`pytest` → exit code 0)
2. ✅ Нет импортов `selenium` в коде
3. ✅ Логи пишутся в файлы с ротацией
4. ✅ Парсинг 5 товаров завершается успешно
5. ✅ CSV файл открывается в Excel без проблем с кодировкой
