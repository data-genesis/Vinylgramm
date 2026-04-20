"""
Модуль настройки логирования для парсера HHV
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime


# Цвета для консольного вывода
COLORS = {
    'DEBUG': '\033[36m',      # Cyan
    'INFO': '\033[32m',       # Green
    'WARNING': '\033[33m',    # Yellow
    'ERROR': '\033[31m',      # Red
    'CRITICAL': '\033[35m',   # Magenta
    'RESET': '\033[0m'        # Reset
}


class ColoredFormatter(logging.Formatter):
    """Форматтер с цветным выводом для консоли"""
    
    def format(self, record):
        log_color = COLORS.get(record.levelname, COLORS['RESET'])
        record.levelname = f"{log_color}{record.levelname}{COLORS['RESET']}"
        return super().format(record)


def setup_logger(name: str, log_file: str = None, level: int = logging.INFO, 
                 console_output: bool = True, critical_log_file: str = None) -> logging.Logger:
    """
    Настройка ротационного логгера с раздельной записью критических ошибок
    
    Args:
        name: Имя логгера
        log_file: Путь к основному файлу лога (если None - только консоль)
        level: Уровень логирования
        console_output: Выводить ли в консоль
        critical_log_file: Отдельный файл для критических ошибок
    
    Returns:
        Настроенный logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Очищаем существующие обработчики
    logger.handlers.clear()
    
    # Формат для детального логирования
    detailed_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Упрощённый формат для консоли
    console_formatter = ColoredFormatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # 1. Ротационный файловый обработчик (основной лог)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
    
    # 2. Отдельный файл для критических ошибок (CAPTCHA, блокировки, поломки библиотек)
    if critical_log_file:
        crit_path = Path(critical_log_file)
        crit_path.parent.mkdir(parents=True, exist_ok=True)
        
        critical_handler = RotatingFileHandler(
            critical_log_file,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
            encoding='utf-8'
        )
        critical_handler.setLevel(logging.CRITICAL)
        critical_handler.setFormatter(detailed_formatter)
        logger.addHandler(critical_handler)
    
    # 3. Консольный обработчик
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    return logger


def get_critical_logger(name: str = "hhv_critical") -> logging.Logger:
    """
    Получить логгер специально для критических ошибок
    
    Критические ошибки включают:
    - Обнаружение CAPTCHA
    - Блокировки (403, 429)
    - Поломки библиотек
    - Невозможность инициализации браузера
    """
    return setup_logger(
        name=name,
        log_file="logs/critical_errors.log",
        level=logging.CRITICAL,
        console_output=True,
        critical_log_file="logs/critical_errors.log"
    )
