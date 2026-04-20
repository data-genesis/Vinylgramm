"""
Базовый класс для всех парсеров
"""
import os
import re
import time
import logging
from datetime import datetime
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext, Response
from bs4 import BeautifulSoup
import requests
from PIL import Image
from io import BytesIO
import base64
import sys
import traceback
from pathlib import Path

from exceptions import (
    ParserError, 
    BrowserInitError, 
    PageLoadError, 
    ParsingError, 
    ImageDownloadError,
    CaptchaDetectedError
)
from utils.logging_config import setup_logger, get_critical_logger


class BaseParser(ABC):
    """Базовый класс для всех парсеров"""
    
    def __init__(self, site_name: str):
        self.site_name = site_name
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.logger = None
        self.critical_logger = None
        self.setup_logging()
    
    def setup_logging(self):
        """Настройка логирования для парсера"""
        log_dir = Path("logs") / "parser"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_filename = log_dir / f"{self.site_name.lower()}_parser_log_{timestamp}.txt"
        critical_log_filename = log_dir.parent / f"critical_{self.site_name.lower()}_{timestamp}.log"
        
        # Основной логгер
        self.logger = setup_logger(
            name=f"{self.site_name}.parser",
            log_file=str(log_filename),
            level=logging.INFO,
            console_output=True,
            critical_log_file=str(critical_log_filename)
        )
        
        # Логгер критических ошибок
        self.critical_logger = get_critical_logger(f"{self.site_name}.critical")
        
        self.logger.info(f"=== {self.site_name} parser session started ===")
        self.logger.info(f"Log file: {log_filename}")
    
    def setup_browser(self, headless: bool = True) -> Optional[Page]:
        """
        Инициализация браузера Playwright с настройками для macOS/Linux
        
        Args:
            headless: Запуск в безголовом режиме
        
        Returns:
            Page объект или None при ошибке
        """
        self.logger.info(f"Setting up browser for {self.site_name} (headless={headless})...")
        print(f"🌐 Setting up browser for {self.site_name}...")
        
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Инициализация Playwright
                self.playwright = sync_playwright().start()
                
                # Запуск браузера
                browser_args = [
                    "--disable-gpu",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                    "--disable-extensions",
                    "--disable-plugins",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                ]
                
                if headless:
                    browser_args.append("--headless")
                    self.logger.info("Headless mode: ON")
                    print("  🔇 Headless mode: ON")
                else:
                    self.logger.info("Headless mode: OFF")
                    print("  🔊 Headless mode: OFF")
                
                self.browser = self.playwright.chromium.launch(
                    headless=headless,
                    args=browser_args
                )
                
                # Настройка контекста
                self.context = self.browser.new_context(
                    viewport={"width": 1920, "height": 1200},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
                    locale="en-US",
                    timezone_id="UTC"
                )
                
                self.page = self.context.new_page()
                self.page.set_default_timeout(30000)  # 30 секунд
                self.page.set_default_navigation_timeout(30000)
                
                self.logger.info(f"Browser started successfully on attempt {attempt + 1}")
                print(f"✅ Browser started OK for {self.site_name}!")
                return self.page
                
            except Exception as e:
                error_msg = f"Attempt {attempt + 1}/{max_retries} failed: {str(e)[:200]}"
                self.logger.error(error_msg)
                print(f"❌ {error_msg}...")
                
                if attempt == max_retries - 1:
                    self.critical_logger.critical(
                        f"Failed to initialize browser after {max_retries} attempts: {e}",
                        exc_info=True
                    )
                    print(f"❌ Failed all browser launch attempts")
                    return None
                
                # Попытка перезапуска с видимым режимом при критических ошибках
                if 'SIGKILL' in str(e) or '-9' in str(e):
                    self.logger.warning("SIGKILL detected, retrying with visible mode...")
                    print("🔄 SIGKILL detected! Retrying VISIBLE browser...")
                    headless = False
                
                time.sleep(2 ** attempt)  # Экспоненциальная задержка
        
        return None
    
    def close_browser(self):
        """Закрытие браузера и очистка ресурсов"""
        try:
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            self.logger.info("Browser closed successfully")
        except Exception as e:
            self.logger.error(f"Error closing browser: {e}")
    
    @abstractmethod
    def handle_cookies(self, page: Page):
        pass
    
    @abstractmethod
    def get_product_urls(self, category_url: str, max_products: int = 100) -> List[str]:
        pass
    
    @abstractmethod
    def parse_product_page(self, page: Page, url: str) -> Dict:
        pass
    
    @abstractmethod
    def get_image_urls(self, soup: BeautifulSoup) -> List[str]:
        pass
    
    def download_image(self, image_url: str, folder_path: str, image_name: str, max_retries: int = 3) -> bool:
        """
        Загрузка изображений через Playwright и requests
        
        Args:
            image_url: URL изображения
            folder_path: Путь к папке для сохранения
            image_name: Имя файла (без расширения)
            max_retries: Максимальное количество попыток
        
        Returns:
            True если успешно, False иначе
        """
        for attempt in range(max_retries):
            try:
                self.logger.info(f"Image download attempt {attempt + 1}/{max_retries}: {image_url}")
                
                # Пробуем загрузить через requests (быстрее)
                response = requests.get(image_url, timeout=30, stream=True)
                response.raise_for_status()
                
                # Проверка на CAPTCHA или блокировку
                if 'captcha' in response.url.lower() or response.status_code == 403:
                    self.critical_logger.critical(
                        f"CAPTCHA or block detected while downloading image: {image_url}"
                    )
                    raise CaptchaDetectedError(f"CAPTCHA detected for image: {image_url}")
                
                img_bytes = response.content
                
                # Создаём папку если не существует
                Path(folder_path).mkdir(parents=True, exist_ok=True)
                img_path = Path(folder_path) / f"{image_name}.jpeg"
                
                with open(img_path, 'wb') as f:
                    f.write(img_bytes)
                
                # Оптимизация изображения
                try:
                    image = Image.open(img_path)
                    image = image.convert('RGB')
                    image.save(img_path, format='JPEG', quality=92, optimize=True)
                except Exception as opt_e:
                    self.logger.warning(f"Image optimization failed: {opt_e}")
                
                self.logger.info(f"Saved: {img_path}")
                print(f"✅ Saved: {image_name}.jpeg")
                return True
                
            except CaptchaDetectedError:
                raise
            except Exception as e:
                self.logger.error(f"Image error (attempt {attempt + 1}): {e}")
                print(f"❌ Image error ({attempt+1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
        
        self.logger.error(f"Failed to download image after {max_retries} attempts: {image_url}")
        return False
    
    def create_safe_filename(self, artist: str, title: str) -> str:
        full_title = f"{artist} - {title}"
        safe = re.sub(r'[\\/*?:"<>|]', "", full_title)
        safe = re.sub(r'\s+', '_', safe)
        datestamp = datetime.now().strftime("%Y%m%d")
        return f"{safe}_{datestamp}"
    
    def save_product_info(self, product_data: Dict, url: str, output_folder: str = "parsed") -> Optional[str]:
        """Сохранение информации о товаре"""
        artist = product_data.get('artist', 'Unknown')
        title = product_data.get('title', 'Unknown')
        
        safe_folder = re.sub(r'[\\/*?:"<>|]', "", f"{artist} - {title}")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"{safe_folder}_{timestamp}"
        folder_path = os.path.join(output_folder, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        
        info_parts = [
            f"URL: {url}",
            f"Site: {self.site_name}",
            "",
        ]
        
        for key, value in product_data.items():
            if isinstance(value, list):
                info_parts.append(f"{key.upper()}:")
                for item in value:
                    info_parts.append(f"  - {item}")
            else:
                info_parts.append(f"{key.upper()}: {value}")
        
        info_text = '\n'.join(info_parts)
        info_file = os.path.join(folder_path, "info.txt")
        
        try:
            with open(info_file, 'w', encoding='utf-8') as f:
                f.write(info_text)
            print(f"📄 Saved: {info_file}")
            return info_file
        except Exception as e:
            print(f"❌ Save failed: {e}")
            return None
