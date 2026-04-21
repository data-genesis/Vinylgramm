--- main.py (原始)


+++ main.py (修改后)
#!/usr/bin/env python3
"""
Точка входа для запуска парсера HHV.
Импортирует основную логику из HHV_to_csv.py
"""
import sys
import os

# Добавляем текущую директорию в путь импортов
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # Импортируем основную функцию запуска из модуля HHV_to_csv
    # Предполагается, что в HHV_to_csv.py есть функция main() или аналогичная точка входа
    from HHV_to_csv import main as run_parser

    if __name__ == "__main__":
        print("Запуск парсера HHV...")
        run_parser()

except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Убедитесь, что файл HHV_to_csv.py существует и содержит функцию main().")
    sys.exit(1)
except Exception as e:
    print(f"Критическая ошибка при запуске: {e}")
    sys.exit(1)
