"""
Базовый класс для всех парсеров сайтов
"""
import os
import re
import time
import logging
import subprocess
from datetime import datetime
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import requests
from PIL import Image
from io import BytesIO
import base64
import sys
import traceback


class BaseParser(ABC):
    """Базовый класс для всех парсеров"""
    
    def __init__(self, site_name: str):
        self.site_name = site_name
        self.driver = None
        self.setup_logging()
    
    def setup_logging(self):
        """Настройка логирования для парсера"""
        log_dir = os.path.join("logs", "parser")
        try:
            os.makedirs(log_dir, exist_ok=True)
        except Exception:
            pass
        log_filename = os.path.join(log_dir, f"{self.site_name}_parser_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        logging.basicConfig(
            filename=log_filename,
            level=logging.INFO,
            format='%(asctime)s %(levelname)s %(message)s',
            encoding='utf-8'
        )
        logging.info(f"=== {self.site_name} parser session started ===")
    
    def setup_driver(self, headless=True) -> Optional[webdriver.Chrome]:
        """Инициализация Chrome WebDriver с общими настройками для macOS"""
        print(f"Setting up browser driver for {self.site_name}...")
        
        def build_options(headless_mode):
            opts = Options()
            
            if headless_mode:
                opts.add_argument("--headless")
                print("  🔇 Headless mode: ON")
            else:
                print("  🔊 Headless mode: OFF")
            
            # Общие опции
            opts.add_argument("--disable-gpu")
            opts.add_argument("--window-size=1920,1200")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-web-security")
            opts.add_argument("--disable-features=VizDisplayCompositor")
            opts.add_argument("--disable-extensions")
            opts.add_argument("--disable-plugins")
            
            # macOS-specific для предотвращения SIGKILL (-9)
            opts.add_argument("--disable-background-timer-throttling")
            opts.add_argument("--disable-backgrounding-occluded-windows")
            opts.add_argument("--disable-renderer-backgrounding")
            opts.add_argument("--disable-field-trial-config")
            opts.add_argument("--enable-automation")
            opts.add_argument("--disable-infobars")
            
            opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36")
            opts.add_argument('log-level=3')
            opts.add_experimental_option('excludeSwitches', ['enable-logging'])
            
            return opts
        
        options = build_options(headless)
        
        try:
            # Поиск chromedriver
            driver_path = None
            candidates = [
                os.path.join("chromedriver", "chromedriver"),
                "/usr/local/bin/chromedriver",
                os.getenv("CHROMEDRIVER"),
            ]
            
            for cand in candidates:
                if cand and os.path.exists(cand):
                    driver_path = os.path.abspath(cand)
                    try:
                        result = subprocess.run([driver_path, '--version'], capture_output=True, text=True, timeout=5)
                        if result.returncode == 0:
                            version = result.stdout.strip()
                            print(f"✅ Local driver found: {driver_path}")
                            print(f"   Version: {version}")
                            break
                    except:
                        pass
            
            # Service setup
            if driver_path:
                print("🔄 Testing local driver...")
                try:
                    service = ChromeService(executable_path=driver_path)
                    service.start()
                    service.stop()
                    print("✅ Local driver tested OK")
                except Exception as test_e:
                    print(f"⚠️ Local test failed ({test_e}), using manager")
                    driver_path = None
            
            if not driver_path:
                print("🔄 Downloading compatible ChromeDriver via webdriver-manager...")
                service = ChromeService(ChromeDriverManager().install())
            else:
                service = ChromeService(executable_path=driver_path)
            
            # Попытки запуска
            for attempt in range(2):
                try:
                    print(f"\n🚀 Launch attempt {attempt+1}/2 (headless={headless})")
                    driver = webdriver.Chrome(service=service, options=options)
                    driver.set_page_load_timeout(30)
                    driver.implicitly_wait(10)
                    print(f"✅ Driver started OK for {self.site_name}!")
                    return driver
                except Exception as drive_e:
                    print(f"❌ Attempt {attempt+1} failed: {str(drive_e)[:200]}...")
                    
                    if attempt == 0 and ('-9' in str(drive_e) or 'SIGKILL' in str(drive_e)):
                        print("🔄 SIGKILL (-9) detected! Retrying VISIBLE browser...")
                        headless = False
                        options = build_options(False)  # Перестроить без headless
                        continue
                    break
            
            print(f"❌ Failed all driver launch attempts")
            return None
            
        except Exception as e:
            print(f"❌ Setup error: {e}")
            traceback.print_exc()
            return None

    
    @abstractmethod
    def handle_cookies(self, driver):
        pass
    
    @abstractmethod
    def get_product_urls(self, category_url: str, max_products: int = 100) -> List[str]:
        pass
    
    @abstractmethod
    def parse_product_page(self, driver, url: str) -> Dict:
        pass
    
    @abstractmethod
    def get_image_urls(self, soup: BeautifulSoup) -> List[str]:
        pass
    
    def download_image_with_selenium(self, driver, image_url: str, folder_path: str, image_name: str, max_retries: int = 3) -> bool:
        """Универсальная функция загрузки изображений через Selenium"""
        for attempt in range(max_retries):
            try:
                logging.info(f"Image download attempt {attempt + 1}/{max_retries}: {image_url}")
                
                driver.set_script_timeout(60)
                
                js_script = """
                var url = arguments[0];
                var callback = arguments[1];
                var xhr = new XMLHttpRequest();
                xhr.timeout = 30000;
                xhr.onload = function() {
                    var reader = new FileReader();
                    reader.onloadend = function() {
                        callback(reader.result);
                    }
                    reader.readAsDataURL(xhr.response);
                };
                xhr.onerror = function() { callback(null); };
                xhr.ontimeout = function() { callback(null); };
                xhr.open('GET', url);
                xhr.responseType = 'blob';
                xhr.send();
                """
                
                base64_data = driver.execute_async_script(js_script, image_url)
                
                if base64_data is None:
                    print(f"❌ Image XHR failed: {image_url}")
                    continue
                
                header, encoded = base64_data.split(",", 1)
                img_bytes = base64.b64decode(encoded)
                
                os.makedirs(folder_path, exist_ok=True)
                img_path = os.path.join(folder_path, f"{image_name}.jpeg")
                with open(img_path, 'wb') as f:
                    f.write(img_bytes)
                
                # Оптимизация изображения
                try:
                    image = Image.open(img_path)
                    image = image.convert('RGB')
                    image.save(img_path, format='JPEG', quality=92, optimize=True)
                except:
                    pass
                
                print(f"✅ Saved: {img_name}.jpeg")
                return True
            except Exception as e:
                print(f"❌ Image error ({attempt+1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
        
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
