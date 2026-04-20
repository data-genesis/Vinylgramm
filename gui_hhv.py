import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import sys
import datetime
from pathlib import Path
import threading

import importlib
if 'parsers.base_parser' in sys.modules:
    importlib.reload(sys.modules['parsers.base_parser'])
if 'parsers.hhv' in sys.modules:
    importlib.reload(sys.modules['parsers.hhv'])

from parsers.hhv import HHVParser

# Настройки логов
_LOG_DIR = os.path.join("logs", "parser")
os.makedirs(_LOG_DIR, exist_ok=True)
GUI_LOG_FILE = os.path.join(
    _LOG_DIR, "hhv_gui_log_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".txt"
)

DEFAULT_CATALOG_URL = "https://www.hhv.de/en-DE-EUR-uk/records/catalog/filter/vinyl-I1M65N4S6U9"
BASE_URL = "https://www.hhv.de"

# === СТИЛИ MATRIX ===
BG_BLACK = "#0a0e14"
FG_GREEN = "#00ff41"
FG_DARK_GREEN = "#00aa2b"
LABEL_BG = "#151b24"
ENTRY_BG = "#2d3035"
ENTRY_FG = "#00ff41"
BUTTON_BG = "#3d4146"
BUTTON_FG = "#00ff41"
BUTTON_ACTIVE_BG = "#3a3f44"

class TextRedirector:
    """Перенаправление stdout в текстовый виджет"""
    def __init__(self, widget, log_file, tag="stdout"):
        self.widget = widget
        self.log_file = log_file
        self.tag = tag

    def write(self, s):
        if not s:
            return
        try:
            self.log_file.write(s)
        except Exception:
            pass
        self.widget.configure(state="normal")
        self.widget.insert("end", s, self.tag)
        self.widget.see("end")
        self.widget.configure(state="disabled")

    def flush(self):
        try:
            self.log_file.flush()
        except Exception:
            pass


class MetalButton(tk.Button):
    """Кнопка с металлическим градиентом"""
    def __init__(self, parent, **kwargs):
        # Извлекаем font из kwargs если есть, иначе дефолтный
        btn_font = kwargs.pop('font', ("Consolas", 10, "bold"))
        
        super().__init__(
            parent,
            relief="raised",
            bd=3,
            bg="#4a5568",
            fg="#00ff41",
            activebackground="#5a6578",
            activeforeground="#00ff00",
            font=btn_font,  # Используем извлеченный font
            cursor="hand2",
            **kwargs
        )
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
    
    def on_enter(self, e):
        self.config(bg="#2a2d31", fg="#00ff00")
    
    def on_leave(self, e):
        self.config(bg="#3E4349", fg="#00ff41")



class HHVGUI:
    """GUI для парсера HHV.de - MATRIX STYLE"""
    
    def __init__(self, master: tk.Tk):
        self.master = master
        master.title("⚡ HHV.de Collector & Parser ⚡")
        master.geometry("950x800")
        master.configure(bg=BG_BLACK)

        # Переменные
        self.catalog_url = tk.StringVar(value=DEFAULT_CATALOG_URL)
        self.urls_file = tk.StringVar(value=str(Path.cwd() / "hhv_urls.txt"))
        self.images_folder = tk.StringVar(value="images_for_upload")
        self.max_links_var = tk.IntVar(value=100)
        self.headless_var = tk.BooleanVar(value=True)

        # Лог файл
        self.log_file = open(GUI_LOG_FILE, "w", encoding="utf-8")
        self.original_stdout = sys.stdout

        root = tk.Frame(master, bg=BG_BLACK)
        root.pack(fill="both", expand=True, padx=15, pady=15)

        # === ЗАГОЛОВОК ===
        title_frame = tk.Frame(root, bg=BG_BLACK)
        title_frame.pack(fill="x", pady=(0, 15))
        
        title_label = tk.Label(
            title_frame,
            text="⚡ HHV.de PARSER ⚡",
            font=("Consolas", 20, "bold"),
            fg=FG_GREEN,
            bg=BG_BLACK
        )
        title_label.pack()
        
        subtitle = tk.Label(
            title_frame,
            text="Vinyl Records Data Extraction System",
            font=("Consolas", 10),
            fg=FG_DARK_GREEN,
            bg=BG_BLACK
        )
        subtitle.pack()

        # === СБОР ССЫЛОК ===
        collection_frame = tk.LabelFrame(
            root,
            text=" 🔗 Сбор ссылок с HHV.de ",
            bg=LABEL_BG,
            fg=FG_GREEN,
            font=("Consolas", 11, "bold"),
            bd=2,
            relief="groove"
        )
        collection_frame.pack(fill="x", pady=(0, 10))

        # URL каталога
        url_row = tk.Frame(collection_frame, bg=LABEL_BG)
        url_row.pack(fill="x", pady=8, padx=10)
        tk.Label(
            url_row,
            text="URL каталога:",
            width=20,
            anchor="w",
            bg=LABEL_BG,
            fg=FG_GREEN,
            font=("Consolas", 9)
        ).pack(side="left")
        self.catalog_url_entry = tk.Entry(
            url_row,
            textvariable=self.catalog_url,
            bg=ENTRY_BG,
            fg=ENTRY_FG,
            insertbackground=FG_GREEN,
            font=("Consolas", 9),
            relief="sunken",
            bd=2
        )
        self.catalog_url_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        # Файл для ссылок
        file_row = tk.Frame(collection_frame, bg=LABEL_BG)
        file_row.pack(fill="x", pady=5, padx=10)
        tk.Label(
            file_row,
            text="Файл ссылок:",
            width=20,
            anchor="w",
            bg=LABEL_BG,
            fg=FG_GREEN,
            font=("Consolas", 9)
        ).pack(side="left")
        self.urls_file_entry = tk.Entry(
            file_row,
            textvariable=self.urls_file,
            bg=ENTRY_BG,
            fg=ENTRY_FG,
            insertbackground=FG_GREEN,
            font=("Consolas", 9),
            relief="sunken",
            bd=2
        )
        self.urls_file_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        choose_btn = MetalButton(file_row, text="📁", command=self.choose_urls_file, width=3)
        choose_btn.pack(side="left")

        # Макс ссылок
        max_links_frame = tk.Frame(collection_frame, bg=LABEL_BG)
        max_links_frame.pack(fill="x", pady=5, padx=10)
        tk.Label(
            max_links_frame,
            text="Макс. ссылок (0=все):",
            width=20,
            anchor="w",
            bg=LABEL_BG,
            fg=FG_GREEN,
            font=("Consolas", 9)
        ).pack(side="left")
        tk.Spinbox(
            max_links_frame,
            from_=0,
            to=10000,
            textvariable=self.max_links_var,
            bg=ENTRY_BG,
            fg=ENTRY_FG,
            buttonbackground="#4a5568",
            font=("Consolas", 9),
            relief="sunken",
            bd=2
        ).pack(side="left", padx=(0, 5))

        # Headless режим
        headless_frame = tk.Frame(collection_frame, bg=LABEL_BG)
        headless_frame.pack(fill="x", pady=5, padx=10)
        tk.Checkbutton(
            headless_frame,
            text="🔍 Headless режим (фоновый браузер)",
            variable=self.headless_var,
            bg=LABEL_BG,
            fg=FG_GREEN,
            selectcolor=ENTRY_BG,
            activebackground=LABEL_BG,
            activeforeground=FG_GREEN,
            font=("Consolas", 9)
        ).pack(side="left")

        # Кнопка сбора
        MetalButton(
            collection_frame,
            text="📥 СОБРАТЬ ССЫЛКИ С КАТАЛОГА",
            command=self.start_collect_links,
            font=("Consolas", 11, "bold")
        ).pack(fill="x", pady=10, padx=10)
        
        soldout_frame = tk.LabelFrame(
            root,
            text=" 🛑 Проверка Sold Out ",
            bg=LABEL_BG,
            fg=FG_GREEN,
            font=("Consolas", 11, "bold"),
            bd=2,
            relief="groove"
        )
        soldout_frame.pack(fill="x", pady=(0, 10))
        
        # CSV файл для проверки
        csv_row = tk.Frame(soldout_frame, bg=LABEL_BG)
        csv_row.pack(fill="x", pady=8, padx=10)
        tk.Label(
            csv_row,
            text="CSV файл:",
            width=20,
            anchor="w",
            bg=LABEL_BG,
            fg=FG_GREEN,
            font=("Consolas", 9)
        ).pack(side="left")
        
        self.csv_file_var = tk.StringVar(value="HHV_output.csv")
        self.csv_file_entry = tk.Entry(
            csv_row,
            textvariable=self.csv_file_var,
            bg=ENTRY_BG,
            fg=ENTRY_FG,
            insertbackground=FG_GREEN,
            font=("Consolas", 9),
            relief="sunken",
            bd=2
        )
        self.csv_file_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        choose_csv_btn = MetalButton(csv_row, text="📁", command=self.choose_csv_file, width=3)
        choose_csv_btn.pack(side="left")
        
        # Кнопка проверки
        MetalButton(
            soldout_frame,
            text="🛑 ПРОВЕРИТЬ SOLD OUT",
            command=self.start_check_sold_out,
            font=("Consolas", 11, "bold")
        ).pack(fill="x", pady=10, padx=10)


        # === ПАРСЕР ===
        parser_frame = tk.LabelFrame(
            root,
            text=" 🚀 Парсинг товаров ",
            bg=LABEL_BG,
            fg=FG_GREEN,
            font=("Consolas", 11, "bold"),
            bd=2,
            relief="groove"
        )
        parser_frame.pack(fill="x", pady=(0, 10))
        
        MetalButton(
            parser_frame,
            text="🚀 ПАРСИТЬ ИЗ ФАЙЛА",
            command=self.start_parse_from_file,
            font=("Consolas", 11, "bold")
        ).pack(fill="x", pady=10, padx=10)

        # === ЛОГ ===
        log_box = tk.LabelFrame(
            root,
            text=" 📊 Лог работы парсера ",
            bg=LABEL_BG,
            fg=FG_GREEN,
            font=("Consolas", 11, "bold"),
            bd=2,
            relief="groove"
        )
        log_box.pack(fill="both", expand=True)
        
        self.log_text = tk.Text(
            log_box,
            height=20,
            wrap="word",
            bg="#000000",
            fg="#00ff41",
            font=("Consolas", 9),
            insertbackground=FG_GREEN,
            selectbackground="#003300",
            relief="sunken",
            bd=2
        )
        self.log_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Стили для текста
        self.log_text.tag_config("stdout", foreground="#00ff41")
        self.log_text.tag_config("error", foreground="#ff0000")
        
        # Перенаправляем stdout
        sys.stdout = TextRedirector(self.log_text, self.log_file, "stdout")

    def choose_urls_file(self):
        """Выбор файла для сохранения ссылок"""
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            initialfile="hhv_urls.txt"
        )
        if path:
            self.urls_file.set(path)

    def choose_csv_file(self):
        """Выбор CSV файла для проверки"""
        path = filedialog.askopenfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile="HHV_output.csv"
        )
        if path:
            self.csv_file_var.set(path)

    def check_sold_out(self):
        """Проверка Sold Out из CSV"""
        csv_path = self.csv_file_var.get().strip()
        if not os.path.exists(csv_path):
            print("❌ CSV файл не найден.")
            messagebox.showerror("Ошибка", "CSV файл не найден!")
            return
        
        headless = self.headless_var.get()
        parser = HHVParser(headless=headless)
        output_file = parser.check_sold_out_from_csv(csv_path)
        
        if output_file:
            messagebox.showinfo("Готово", f"Проверка завершена!\n\nРезультаты: {output_file}")

    def start_check_sold_out(self):
        """Запуск проверки Sold Out в потоке"""
        threading.Thread(target=self.check_sold_out, daemon=True).start()


    def start_parse_from_file(self):
        """Запуск парсинга из файла в отдельном потоке"""
        file_path = self.urls_file.get().strip()
        if not os.path.exists(file_path):
            print("❌ Файл со ссылками не найден.")
            messagebox.showerror("Ошибка", "Файл со ссылками не найден!")
            return

        # Сохраняем headless ДО создания потока
        headless = self.headless_var.get()

        def run_parser():
            print("\n" + "="*60)
            print("🚀 НАЧИНАЕМ ПАРСИТЬ...")
            print("="*60 + "\n")
            
            # Используем сохраненное значение headless
            parser = HHVParser(output_root="parsed", headless=headless)
            parser.parse_from_file(file_path)
            
            print("\n" + "="*60)
            print("✅ ПАРСИНГ ГОТОВ")
            print("="*60 + "\n")

        threading.Thread(target=run_parser, daemon=True).start()


    def collect_links(self):
        """Сбор ссылок с каталога HHV.de"""
        catalog_url_str = self.catalog_url.get().strip()
        if not catalog_url_str:
            print("❌ Не указан URL каталога.")
            return

        max_links = self.max_links_var.get()
        output_file = self.urls_file.get().strip()
        if not output_file:
            print("❌ Не указан файл для сохранения ссылок.")
            return

        headless = self.headless_var.get()

        print("\n" + "="*60)
        print(f"🔍 Начинаю сбор ссылок с HHV.de")
        print(f"📂 Каталог: {catalog_url_str}")
        print(f"📊 Максимум: {max_links if max_links > 0 else 'все'}")
        print(f"🖥️ Режим: {'Headless' if headless else 'С окном'}")
        print("="*60 + "\n")

        try:
            parser = HHVParser(headless=headless)
            collected_links = parser.get_product_urls(catalog_url_str, max_links if max_links > 0 else 1000)

            if collected_links:
                try:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        for link in collected_links:
                            f.write(link + '\n')
                    print(f"\n✅ Ссылки сохранены: {len(collected_links)} → {output_file}")
                    messagebox.showinfo("Успех", f"Собрано {len(collected_links)} ссылок!\n\nСохранено в: {output_file}")
                except Exception as e:
                    print(f"❌ Ошибка записи файла: {e}")
                    messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {e}")
            else:
                print("❌ Ссылок не найдено.")
                messagebox.showwarning("Внимание", "Ссылки не найдены.")
                
        except Exception as e:
            print(f"❌ Ошибка при сборе ссылок: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Ошибка", f"Произошла ошибка:\n{e}")

    def start_collect_links(self):
        """Запуск сбора ссылок в отдельном потоке"""
        threading.Thread(target=self.collect_links, daemon=True).start()

    def on_closing(self):
        """Обработка закрытия окна"""
        try:
            sys.stdout = self.original_stdout
            self.log_file.close()
        except:
            pass
        self.master.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = HHVGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
