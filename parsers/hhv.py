# parsers/hhv.py
"""
Парсер для HHV.de с наследованием от BaseParser
"""
import os
import re
import time
from typing import Dict, List
from datetime import datetime
from bs4 import BeautifulSoup
from pathlib import Path
from playwright.sync_api import Page
from .base_parser import BaseParser

class HHVParser(BaseParser):
    """Парсер для сайта HHV.de"""
    def __init__(self, output_root="parsed", headless=True):
        super().__init__("HHV")
        self.base_url = "https://www.hhv.de"
        self.output_root = Path(output_root)
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.headless = headless
    
    # Оставляем метод handle_cookies, но делаем его пустым
    def handle_cookies(self, page: Page):
        """Пустая реализация обработки cookies (требуется для совместимости с BaseParser)"""
        self.logger.info("Skipping cookies handling")
        print("🍪 Пропускаем обработку cookies")
        # Ничего не делаем, но метод существует для совместимости
    
    def get_product_urls(self, category_url: str, max_products: int = 100) -> List[str]:
        """Получение URL товаров из категории HHV.de с постепенной прокруткой"""
        self.logger.info(f"Collecting product URLs from: {category_url}")
        print(f"\n🔍 Collecting product URLs from: {category_url}")
        
        page = self.setup_browser(headless=self.headless)
        if not page:
            self.logger.error("Failed to setup browser")
            print("❌ Failed to setup browser")
            return []
        
        product_urls = []
        try:
            page.goto(category_url)
            self.handle_cookies(page)
            
            self.logger.info("Waiting for initial page load...")
            print("⏳ Waiting for initial page load...")
            time.sleep(3)
            
            current_page = 1
            max_pages = 20
            
            while len(product_urls) < max_products and current_page <= max_pages:
                print(f"\n📄 Страница {current_page}")
                
                # === ПОСТЕПЕННАЯ ПРОКРУТКА (как в bsr.py, но с проверкой новых элементов) ===
                scroll_step = 400  # Маленький шаг для плавной загрузки
                pause = 0.8  # Пауза после каждого скролла
                max_stagnant = 3  # Сколько раз подряд нет новых элементов before stop
                stagnant_count = 0
                last_y = -1
                
                while len(product_urls) < max_products:
                    previous_count = len(product_urls)
                    
                    # 1. Делаем небольшой скролл вниз
                    driver.execute_script(f"window.scrollBy(0, {scroll_step});")
                    time.sleep(pause)
                    
                    # 2. Проверяем позицию скролла
                    y = driver.execute_script("return window.pageYOffset || document.documentElement.scrollTop;")
                    if y == last_y:
                        stagnant_count += 1
                    else:
                        stagnant_count = 0
                        last_y = y
                    
                    # 3. Проверяем, достигли ли низа страницы
                    at_bottom = driver.execute_script(
                        "return (window.innerHeight + window.pageYOffset) >= (document.body.scrollHeight - 5);"
                    )
                    
                    # 4. Парсим ссылки после каждого скролла
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    links = soup.select('a[href*="/records/item/"], a[href*="/records/artikel/"]')
                    
                    for link in links:
                        href = link.get('href')
                        if href:
                            clean_href = href.split('?')[0]
                            if not clean_href.startswith('http'):
                                clean_href = self.base_url + clean_href if clean_href.startswith('/') else self.base_url + '/' + clean_href
                            if clean_href not in product_urls:
                                product_urls.append(clean_href)
                    
                    # 5. Проверяем, появились ли новые товары
                    new_links = len(product_urls) - previous_count
                    if new_links > 0:
                        stagnant_count = 0  # Сброс, если нашли новые товары
                        print(f"  📊 Собрано: {len(product_urls)} (+{new_links})")
                    else:
                        stagnant_count += 1
                        print(f"  ⏳ Нет новых товаров ({stagnant_count}/{max_stagnant})...")
                    
                    # 6. Пробуем нажать 'Load More' если есть
                    if new_links == 0:
                        try:
                            load_more = driver.find_elements(By.CSS_SELECTOR, "button.load-more, a.load-more")
                            if load_more and load_more[0].is_displayed():
                                load_more[0].click()
                                print("  🖱️ Clicked Load More")
                                time.sleep(1)
                                stagnant_count = 0
                                continue
                        except:
                            pass
                    
                    # 7. Условия выхода из цикла скролла
                    if stagnant_count >= max_stagnant:
                        print(f"  ✅ Больше товаров не подгружается (stagnant={stagnant_count})")
                        break
                    
                    if at_bottom and new_links == 0:
                        print(f"  ✅ Достигнут низ страницы")
                        break
                    
                    if len(product_urls) >= max_products:
                        print(f"  ✅ Reached limit of {max_products} products")
                        break
                
                # === ПАГИНАЦИЯ (Переход на след. страницу) ===
                if len(product_urls) < max_products and current_page < max_pages:
                    print("🔎 Ищем кнопку следующей страницы...")
                    try:
                        next_btn = driver.find_elements(By.CSS_SELECTOR, "a[rel='next'], a[class*='next'], a[class*='Next']")
                        if not next_btn:
                            next_btn = driver.find_elements(By.CSS_SELECTOR, f"a[href*='p:{current_page + 1}'], a[href*='page={current_page + 1}']")
                        
                        if next_btn:
                            next_url = next_btn[0].get_attribute('href')
                            print(f"➡️ Переход на следующую страницу: {next_url}")
                            driver.get(next_url)
                            time.sleep(4)
                            current_page += 1
                        else:
                            print(f"🏁 Следующая страница не найдена. Парсинг завершен.")
                            break
                    except Exception as e:
                        print(f"⚠️ Ошибка перехода: {e}")
                        break
                else:
                    break
            
            # Выводим собранные ссылки
            print(f"\n📋 Collected URLs (Top 5):")
            for i, url in enumerate(product_urls[:5], 1):
                print(f"  [{i}] {url}")
        
        except Exception as e:
            print(f"❌ Error collecting URLs: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            try:
                driver.quit()
            except:
                pass
        
        result = product_urls[:max_products]
        print(f"\n✅ Total collected: {len(result)} product URLs")
        return result

    def parse_product_page(self, driver, url: str) -> Dict:
        """Парсинг страницы товара HHV.de"""
        print(f"\n🔍 Parsing: {url}")
        driver.get(url)
        # Убран вызов обработки cookies
        
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-highlight-name="Items::Detail::Flap::Table"] table'))
            )
            time.sleep(1)
        except Exception as e:
            print(f"❌ Failed to load product page: {e}")
            return {}
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        product_data = {}
        
        # Словарь перевода немецких полей → английские
        field_mapping = {
            'artist': 'artist',
            'künstler': 'artist',
            'title': 'title',
            'titel': 'title',
            'label': 'label',
            'format': 'format',
            'genre': 'genre',
            'style': 'style',
            'stil': 'style',
            'price': 'price',
            'preis': 'price',
            'release date': 'release_date',
            'erscheinungsdatum': 'release_date',
            'pressing': 'pressing',
            'pressung': 'pressing',
            'condition': 'condition',
            'zustand': 'condition',
        }
        
        details_div = soup.select_one('div[data-highlight-name="Items::Detail::Flap::Table"]')
        if not details_div:
            print("❌ Details div NOT found")
            return {}
        
        table = details_div.select_one('table')
        if not table:
            print("❌ Table NOT found")
            return {}
        
        rows = table.select('tbody tr')
        print(f"📊 Found {len(rows)} rows")
        
        # Парсим каждую строку
        for row in rows:
            cells = row.find_all('td')
            if len(cells) != 2:
                continue
            
            key_cell = cells[0]
            value_cell = cells[1]
            
            if 'title' not in key_cell.get('class', []):
                continue
            if 'value' not in value_cell.get('class', []):
                continue
            
            key_text = key_cell.get_text(strip=True)
            value_text = value_cell.get_text(separator=' ', strip=True)
            
            # Очищаем ключ и приводим к нижнему регистру
            key_clean = key_text.replace(':', '').strip().lower()
            
            # Ищем соответствие в словаре
            mapped_key = field_mapping.get(key_clean)
            if mapped_key:
                if mapped_key == 'artist':
                    product_data['artist'] = value_text
                    print(f"  ✅ Artist: {value_text}")
                elif mapped_key == 'title':
                    product_data['title'] = value_text
                    print(f"  ✅ Title: {value_text}")
                elif mapped_key == 'label':
                    product_data['label'] = value_text.replace('/', ', ')
                elif mapped_key == 'format':
                    product_data['format'] = value_text.split(',')[0].strip()
                elif mapped_key == 'genre':
                    product_data['genre'] = value_text
                elif mapped_key == 'style':
                    if 'genre' in product_data:
                        product_data['genre'] += f", {value_text}"
                    else:
                        product_data['genre'] = value_text
                elif mapped_key == 'price':
                    product_data['price'] = value_text
                    print(f"  ✅ Price: {value_text}")
        
        preorder_flag = soup.select_one('div[data-highlight-name="Items::Detail::Flag"].preorder')
        if preorder_flag:
            date_span = preorder_flag.select_one('span.date')
            if date_span:
                date_text = date_span.get_text(strip=True)
                print(f"  📅 Preorder date: {date_text}")
                de_match = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', date_text)
                if de_match:
                    day, month, year = de_match.groups()
                    product_data['release_date'] = f"{day.zfill(2)}.{month.zfill(2)}.{year}"
                    print(f"  ✅ Release date: {product_data['release_date']}")
                else:
                    en_match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', date_text)
                    if en_match:
                        year, month, day = en_match.groups()
                        product_data['release_date'] = f"{day.zfill(2)}.{month.zfill(2)}.{year}"
                        print(f"  ✅ Release date: {product_data['release_date']}")
            else:
                product_data['release_date'] = "Уже в продаже"
        else:
            print("  📅 No preorder - available now")
            product_data['release_date'] = "Уже в продаже"
        
        # === ОПИСАНИЕ ===
        desc_div = soup.select_one('div[data-highlight-name="Items::Detail::Flap::Text"]')
        description = ""
        if desc_div:
            # Извлекаем текст, заменяя <br> на переносы строк
            for br in desc_div.find_all('br'):
                br.replace_with('\n')
            description = desc_div.get_text(strip=True)
            print(f"  📄 Description: {len(description)} chars")
        
        product_data['description'] = description if description else "Нет описания"
        
        # Изображения
        image_urls = self.get_image_urls(soup)
        if image_urls:
            product_data['image_urls'] = image_urls
            print(f"🖼 {len(image_urls)} image(s)")
        
        # === ПАРСИНГ ТРЕКЛИСТА ===
        tracklist_div = soup.select_one('div[data-highlight-name="Items::Shared::Tracklist"]')
        if tracklist_div:
            tracks = tracklist_div.select('div.track')
            if tracks:
                tracklist_lines = []
                for idx, track in enumerate(tracks, 1):
                    # Извлекаем название трека
                    name_span = track.select_one('span.name')
                    if name_span:
                        track_name = name_span.get_text(strip=True)
                        tracklist_lines.append(f"{idx}. {track_name}")
                if tracklist_lines:
                    product_data['tracklist'] = '\n'.join(tracklist_lines)
                    print(f"🎵 Tracklist: {len(tracklist_lines)} tracks")
                else:
                    product_data['tracklist'] = "Нет треклиста"
            else:
                product_data['tracklist'] = "Нет треклиста"
        else:
            product_data['tracklist'] = "Нет треклиста"
        
        print(f"\n📦 Result:")
        print(f"   Artist: {product_data.get('artist', '❌')}")
        print(f"   Title: {product_data.get('title', '❌')}")
        print(f"   Price: {product_data.get('price', '❌')}")
        return product_data

    def get_image_urls(self, soup: BeautifulSoup) -> List[str]:
        """Извлечение URL изображений для HHV.de"""
        image_urls = []
        
        # 1. ГЛАВНОЕ изображение из основной галереи (обычно 1 картинка)
        picture_tag = soup.select_one('div.items--detail--images--base-component picture')
        if picture_tag:
            source_tag = picture_tag.find('source')
            if source_tag and source_tag.has_attr('srcset'):
                raw_srcset = source_tag['srcset']
                try:
                    # srcset может содержать несколько ссылок, берём первую
                    image_url = raw_srcset.split(',')[0].strip().split(' ')[0]
                except Exception:
                    image_url = raw_srcset.strip()
                if not image_url.startswith('http'):
                    image_url = "https:" + image_url
                if image_url not in image_urls:
                    image_urls.append(image_url)
                    print(f"  🖼 Main image: {image_url}")
        
        # 2. ДОПОЛНИТЕЛЬНЫЕ изображения из всех <picture> на странице
        all_pictures = soup.select('picture')
        for pic in all_pictures:
            source = pic.find('source')
            if source and source.has_attr('srcset'):
                srcset = source['srcset']
                try:
                    url = srcset.split(',')[0].strip().split(' ')[0]
                except:
                    url = srcset.strip()
                if not url.startswith('http'):
                    url = "https:" + url
                # Фильтруем мусор: только изображения товара (содержат items/images)
                if 'items/images' in url and url not in image_urls:
                    image_urls.append(url)
                    print(f"  🖼 Extra image: {url}")
        
        # 3. Поиск через img тегов (фоллбек)
        imgs = soup.select('img[alt*="Tyler"], img[title*="CHROMAKOPIA"]')
        for img in imgs:
            src = img.get('src') or img.get('data-src')
            if src:
                if not src.startswith('http'):
                    src = "https:" + src if src.startswith('//') else self.base_url + src
                if 'items/images' in src and src not in image_urls:
                    image_urls.append(src)
                    print(f"  🖼 Fallback image: {src}")
        
        print(f"\n📊 Total images found: {len(image_urls)}")
        return image_urls

    def save_product_info_custom(self, product_data: Dict, url: str) -> str:
        """
        Сохранение информации о товаре в формате как у VeryOk
        """
        artist = product_data.get('artist', 'Unknown Artist')
        title = product_data.get('title', 'Untitled')
        release_date = product_data.get('release_date', '')
        price = product_data.get('price', '')
        label = product_data.get('label', '')
        format_info = product_data.get('format', '')
        genre = product_data.get('genre', '')
        description = product_data.get('description', '')
        tracklist = product_data.get('tracklist', 'Нет треклиста')
        image_urls = product_data.get('image_urls', [])
        downloaded_images = product_data.get('downloaded_images', [])
        
        # Создаем безопасное имя папки
        safe_title = re.sub(r'[\\/*?:"<>|]', "", f"{artist} - {title}")
        safe_title = re.sub(r'\s+', '_', safe_title)
        
        product_folder = self.output_root / safe_title
        product_folder.mkdir(parents=True, exist_ok=True)
        
        # Записываем info.txt
        info_path = product_folder / "info.txt"
        with open(info_path, "w", encoding="utf-8") as f:
            f.write(f"Source URL: {url}\n")
            f.write(f"Site: {self.site_name}\n")
            # Основные поля
            f.write(f"artist: {artist}\n")
            f.write(f"title: {title}\n")
            # Дополнительные поля
            if label:
                f.write(f"label: {label}\n")
            if format_info:
                f.write(f"format: {format_info}\n")
            if genre:
                f.write(f"genre: {genre}\n")
            f.write(f"release_date: {release_date}\n")
            f.write(f"price: {price}\n")
            # Изображения
            f.write("image_urls:\n")
            for img_url in image_urls:
                f.write(f"  {img_url}\n")
            f.write("downloaded_images:\n")
            for img_name in downloaded_images:
                f.write(f"  {img_name}\n")
            f.write("\n")
            # Описание
            f.write("description:\n")
            if description:
                f.write(description.strip() + "\n")
            else:
                f.write("\n")
            # Треклист
            f.write("tracklist:\n")
            if tracklist and tracklist != "Нет треклиста":
                f.write(tracklist.strip() + "\n")
            else:
                f.write("Нет треклиста\n")
        
        print(f"✅ info.txt saved: {info_path}")
        return str(info_path)

    def parse_from_file(self, urls_file: str):
        """
        Парсит товары из файла со ссылками (как в VeryOk)
        """
        if not os.path.exists(urls_file):
            print(f"❌ URLs file not found: {urls_file}")
            return []
        
        with open(urls_file, "r", encoding="utf-8") as f:
            urls = [ln.strip() for ln in f if ln.strip()]
        
        if not urls:
            print(f"❌ No URLs found in {urls_file}")
            return []
        
        print(f"\n📋 Found {len(urls)} URLs to parse")
        results = []
        
        self.driver = self.setup_driver(headless=self.headless)
        if not self.driver:
            print("❌ Failed to setup driver")
            return []
        
        try:
            for i, url in enumerate(urls, 1):
                print(f"\n{'='*60}")
                print(f"Processing [{i}/{len(urls)}]")
                try:
                    product_data = self.parse_product_page(self.driver, url)
                    if product_data:
                        artist = product_data.get('artist', 'Unknown')
                        title = product_data.get('title', 'Untitled')
                        
                        # Создаем безопасное имя папки
                        safe_title = re.sub(r'[\\/*?:"<>|]', "", f"{artist} - {title}")
                        safe_title = re.sub(r'\s+', '_', safe_title)
                        
                        # Папка для товара (та же где info.txt)
                        product_folder = self.output_root / safe_title
                        product_folder.mkdir(parents=True, exist_ok=True)
                        
                        # Скачиваем изображения В ТУ ЖЕ ПАПКУ
                        image_urls = product_data.get('image_urls', [])
                        if image_urls:
                            print(f"📥 Downloading {len(image_urls)} image(s)...")
                            downloaded = []
                            for idx, img_url in enumerate(image_urls, 1):
                                # Имя файла изображения
                                img_name = f"{safe_title}" if len(image_urls) == 1 else f"{safe_title}_{idx:02d}"
                                # Скачиваем в папку товара
                                success = self.download_image_with_selenium(
                                    self.driver, img_url, str(product_folder), img_name
                                )
                                if success:
                                    downloaded.append(f"{img_name}.jpeg")
                                    print(f"  ✅ [{idx}/{len(image_urls)}] {img_name}.jpeg")
                                else:
                                    print(f"  ❌ [{idx}/{len(image_urls)}] Failed")
                            product_data['downloaded_images'] = downloaded
                        
                        # Сохраняем info.txt
                        info_path = self.save_product_info_custom(product_data, url)
                        results.append(info_path)
                        print(f"🎉 Successfully parsed: {product_data.get('title', 'Unknown')}")
                    else:
                        print(f"⚠️ Failed to parse product data")
                except Exception as e:
                    print(f"❌ Error processing URL: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Задержка между запросами
                time.sleep(1)
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                    print("\n🔚 Browser closed")
                except:
                    pass
        
        print(f"\n{'='*60}")
        print(f"✅ Parsing complete: {len(results)}/{len(urls)} successful")
        return results

    def check_sold_out_from_csv(self, csv_file: str) -> str:
        """
        Проверяет товары из CSV на статус Sold Out
        Возвращает путь к файлу sold_out.txt
        """
        import csv
        import datetime
        
        if not os.path.exists(csv_file):
            print(f"❌ CSV файл не найден: {csv_file}")
            return ""
        
        output_file = f"sold_out_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        sold_out_items = []
        
        driver = self.setup_driver(headless=self.headless)
        if not driver:
            print("❌ Failed to setup driver")
            return ""
        
        print("\n" + "="*60)
        print("🔍 ПРОВЕРКА SOLD OUT ИЗ CSV")
        print("="*60 + "\n")
        
        try:
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            print(f"📋 Найдено товаров в CSV: {len(rows)}\n")
            
            for idx, row in enumerate(rows, 1):
                # Извлекаем данные
                product_name = row.get('Имя', 'Unknown')
                source_url = row.get('Значения атрибутов 7', '').strip()
                
                # Проверяем валидность URL
                if not source_url or source_url == "" or not source_url.startswith('http'):
                    print(f"[{idx}/{len(rows)}] ⚠️ Нет ссылки: {product_name}")
                    continue
                
                # Проверяем что это именно ссылка на товар HHV
                if 'hhv.de' not in source_url or ('/records/item/' not in source_url and '/records/artikel/' not in source_url):
                    print(f"[{idx}/{len(rows)}] ⚠️ Некорректная ссылка HHV: {product_name}")
                    continue
                
                print(f"[{idx}/{len(rows)}] Проверяю: {product_name[:50]}...")
                try:
                    driver.get(source_url)
                    # Убран вызов обработки cookies
                    
                    time.sleep(1)
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    
                    # Ищем селектор Sold Out
                    sold_out_div = soup.select_one('div[data-highlight-name="Items::Detail::Availability"].sold_out')
                    availability_div = soup.select_one('div[data-highlight-name="Items::Detail::Availability"]')
                    
                    if availability_div:
                        # Проверяем наличие иконки sold_out
                        sold_out_icon = availability_div.select_one('div.icon.sold_out')
                        if sold_out_icon:
                            print(f"  ❌ SOLD OUT")
                            sold_out_items.append(f"{product_name} - {source_url}")
                        else:
                            print(f"  ✅ В наличии")
                    else:
                        # Если блока нет вообще — считаем в наличии
                        print(f"  ✅ В наличии (блок не найден)")
                except Exception as e:
                    print(f"  ⚠️ Ошибка открытия страницы: {e}")
                    sold_out_items.append(f"{product_name} - не удалось открыть - {source_url}")
                
                time.sleep(1)
            
            # Записываем результаты
            if sold_out_items:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write("SOLD OUT ТОВАРЫ:\n")
                    f.write("="*60 + "\n")
                    for item in sold_out_items:
                        f.write(item + "\n")
                
                print("\n" + "="*60)
                print(f"📝 РЕЗУЛЬТАТЫ:")
                print(f"   Всего проверено: {len(rows)}")
                print(f"   Sold Out: {len(sold_out_items)}")
                print(f"   Файл: {output_file}")
                print("="*60)
                print("\n🛑 SOLD OUT товары:")
                for item in sold_out_items:
                    print(f"  - {item}")
            else:
                print("\n✅ Все товары в наличии!")
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write("Все товары в наличии!\n")
        
        except Exception as e:
            print(f"❌ Ошибка обработки CSV: {e}")
            import traceback
            traceback.print_exc()
        finally:
            try:
                driver.quit()
            except:
                pass
        
        return output_file