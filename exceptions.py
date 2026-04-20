"""
Кастомные исключения для парсера HHV
"""


class ParserError(Exception):
    """Базовое исключение парсера"""
    pass


class BrowserInitError(ParserError):
    """Ошибка инициализации браузера (Playwright)"""
    pass


class PageLoadError(ParserError):
    """Ошибка загрузки страницы"""
    pass


class ParsingError(ParserError):
    """Ошибка парсинга данных"""
    pass


class ImageDownloadError(ParserError):
    """Ошибка загрузки изображения"""
    pass


class CaptchaDetectedError(ParserError):
    """Обнаружена CAPTCHA или блокировка"""
    pass


class ConfigurationError(ParserError):
    """Ошибка конфигурации"""
    pass
