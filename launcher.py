# ============================================================
# ИМПОРТЫ (подключаем необходимые библиотеки)
# ============================================================

import win32gui          # Для работы с окнами Windows (поиск и активация)
import win32con          # Константы для работы с окнами (SW_RESTORE и т.д.)
import tkinter as tk     # Главная библиотека для создания интерфейса
from tkinter import ttk, messagebox  # Стилизованные виджеты и диалоговые окна
import json              # Для работы с JSON файлами (manifest)
import subprocess        # Для запуска внешних программ (AHK скриптов)
import threading         # Для многопоточности (чтобы интерфейс не зависал)
from pathlib import Path # Удобная работа с путями к файлам
from updater import GitHubUpdater  # Наш модуль для обновления скриптов
import keyboard          # Для глобальных горячих клавиш
import sys               # Для системных операций (выход из программы)
import os                # Для работы с операционной системой (пути, файлы)
import atexit            # Для выполнения кода при закрытии программы
import tempfile          # Для создания временных файлов (блокировка)
from datetime import datetime  # Для временных меток в логах


# ============================================================
# БЛОКИРОВКА ДВОЙНОГО ЗАПУСКА
# ============================================================

def check_single_instance():
    """
    Проверяет, не запущено ли уже приложение.
    Если запущено - активирует существующее окно и закрывает новое.
    Если не запущено - создаёт файл-блокировку и запускается.
    """
    # Создаём временный файл-блокировку в папке TEMP
    lock_file = os.path.join(tempfile.gettempdir(), "timetotravel.lock")
    
    try:
        # Пробуем создать файл. Если получилось - приложение не запущено
        global lock_fd
        lock_fd = open(lock_file, 'x')
        
        # При закрытии программы удаляем файл-блокировку
        def cleanup():
            try:
                lock_fd.close()
                os.remove(lock_file)
            except:
                pass
        
        atexit.register(cleanup)
        return True  # Запускаем новую копию
        
    except FileExistsError:
        # Файл существует - приложение уже запущено
        # Находим окно с названием "Время Путешествий"
        def enum_windows_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                window_text = win32gui.GetWindowText(hwnd)
                if "Время Путешествий" in window_text:
                    windows.append(hwnd)
        
        windows = []
        win32gui.EnumWindows(enum_windows_callback, windows)
        
        if windows:
            hwnd = windows[0]
            # Если окно свёрнуто - разворачиваем
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            # Поднимаем окно на передний план
            win32gui.SetForegroundWindow(hwnd)
        
        return False  # Не запускаем новую копию


# ============================================================
# ЛОГИРОВАНИЕ ОШИБОК
# ============================================================

def log_error(error_msg):
    """
    Записывает ошибку в файл лога.
    Логи хранятся в: %LOCALAPPDATA%\TimeToTravel\logs\error.log
    """
    try:
        # Создаём папку для логов (если её нет)
        log_dir = os.path.join(os.environ.get('LOCALAPPDATA'), "TimeToTravel", "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "error.log")
        
        # Добавляем запись с временной меткой
        with open(log_file, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {error_msg}\n")
    except:
        pass  # Если лог не записался - не критично


# ============================================================
# ГЛАВНЫЙ КЛАСС ПРИЛОЖЕНИЯ
# ============================================================

class AutomationLauncher:
    """Главный класс приложения 'Время Путешествий'"""
    
    def __init__(self, root):
        """Конструктор - вызывается при создании приложения"""
        self.root = root
        self.root.title("Время Путешествий")  # Заголовок окна
        self.root.geometry("750x550")         # Размер окна (ширина x высота)
        
        # ===== НАСТРОЙКИ ВНЕШНЕГО ВИДА (меняй здесь!) =====
        # Размер окна: можно изменить на 800x600, 900x650 и т.д.
        # Количество колонок в сетке: max_cols = 2, 3 или 4
        # Ширина кнопок: width = 25, 30, 35
        # Отступы между кнопками: padx=5, pady=5
        # ====================================================
        
        # Инициализируем модуль обновления
        try:
            self.updater = GitHubUpdater()
        except Exception as e:
            log_error(f"Ошибка инициализации updater: {e}")
            messagebox.showerror("Ошибка", f"Не удалось инициализировать обновлятор:\n{e}")
            sys.exit(1)
        
        # Стек навигации (хранит историю переходов по папкам)
        self.navigation_stack = []
        
        # Флаг - выполняется ли сейчас какой-то скрипт
        self.script_running = False
        
        # Загружаем манифест (список скриптов и категорий)
        self.manifest = self.load_manifest()
        
        # Создаём интерфейс
        self.setup_ui()
        
        # Показываем главный экран (список категорий)
        self.show_root()
        
        # Проверяем обновления в фоновом режиме
        self.check_updates_in_background()
    
    def load_manifest(self):
        """
        Загружает файл manifest.json
        Сначала ищет в кэше, потом в папке проекта
        """
        try:
            # Пробуем загрузить из кэша (куда скачиваются обновления)
            cache_manifest = self.updater.cache_dir / "manifest.json"
            if cache_manifest.exists():
                with open(cache_manifest, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            # Если в кэше нет - берём из папки проекта (для разработки)
            local_manifest = Path(__file__).parent / "config" / "manifest.json"
            if local_manifest.exists():
                with open(local_manifest, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            log_error(f"Ошибка загрузки манифеста: {e}")
        
        # Если ничего не загрузилось - возвращаем пустой манифест
        return {"version": "0.0.0", "categories": []}
    
    def setup_ui(self):
        """Создаёт все элементы интерфейса"""
        
        # ===== ЗАГОЛОВОК ОКНА =====
        self.title_label = tk.Label(
            self.root, 
            text=f"Время Путешествий v{self.manifest['version']}", 
            font=("Arial", 14, "bold")  # Шрифт и размер заголовка
        )
        self.title_label.pack(pady=10)
        
        # ===== ПАНЕЛЬ НАВИГАЦИИ (кнопка "Назад" и путь) =====
        nav_frame = ttk.Frame(self.root)
        nav_frame.pack(fill="x", padx=20, pady=5)
        
        # Кнопка "Назад" (изначально неактивна)
        self.back_button = ttk.Button(nav_frame, text="← Назад", command=self.go_back, state="disabled")
        self.back_button.pack(side="left")
        
        # Путь (хлебные крошки)
        self.path_label = tk.Label(nav_frame, text="", font=("Arial", 10), fg="gray")
        self.path_label.pack(side="left", padx=10)
        
        # Индикатор интернета (🌐 = есть, ⚠️ = нет)
        self.network_status = tk.Label(nav_frame, text="🌐", font=("Arial", 10))
        self.network_status.pack(side="right", padx=5)
        
        # ===== ОСНОВНАЯ ОБЛАСТЬ (сетка с кнопками) =====
        self.content_frame = ttk.LabelFrame(self.root, text="Меню", padding=10)
        self.content_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Фрейм, в который будут помещаться кнопки (очищается при навигации)
        self.buttons_frame = ttk.Frame(self.content_frame)
        self.buttons_frame.pack(fill="both", expand=True)
        
        # ===== КНОПКА ПРОВЕРКИ ОБНОВЛЕНИЙ =====
        update_btn = ttk.Button(self.root, text="🔄 Проверить обновления", command=self.manual_check_updates)
        update_btn.pack(pady=5)
        
        # ===== СТРОКА СОСТОЯНИЯ =====
        self.status_var = tk.StringVar(value="Готов")
        self.progress_bar = ttk.Progressbar(self.root, mode='indeterminate')  # Бегущая полоска
        
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief="sunken")
        status_bar.pack(side="bottom", fill="x")
        
        # ===== ГОРЯЧИЕ КЛАВИШИ =====
        self.setup_hotkeys()
        
        # ===== ПРОВЕРКА ИНТЕРНЕТА =====
        self.check_internet()
    
    def check_internet(self):
        """Проверяет наличие интернета и обновляет индикатор"""
        def check():
            try:
                import requests
                requests.get("https://github.com", timeout=5)
                self.root.after(0, lambda: self.network_status.config(text="🌐", fg="green"))
            except:
                self.root.after(0, lambda: self.network_status.config(text="⚠️ Нет интернета", fg="red"))
                self.root.after(0, lambda: self.status_var.set("Нет интернета. Обновления недоступны."))
        
        threading.Thread(target=check, daemon=True).start()
    
    def clear_buttons(self):
        """Очищает все кнопки из основной области"""
        for widget in self.buttons_frame.winfo_children():
            widget.destroy()
    
    def show_root(self):
        """
        Показывает главный экран (список категорий/папок)
        Это первый экран, который видит пользователь
        """
        self.clear_buttons()
        self.navigation_stack = [{"type": "root"}]
        self.update_navigation_ui()
        
        # Получаем список категорий из манифеста
        categories = self.manifest.get("categories", [])
        
        if not categories:
            label = tk.Label(self.buttons_frame, text="Нет доступных категорий", fg="gray")
            label.pack(pady=20)
            return
        
        # ===== НАСТРОЙКИ СЕТКИ (меняй здесь!) =====
        row = 0          # Текущая строка
        col = 0          # Текущая колонка
        max_cols = 3     # Количество колонок (можно 2, 3 или 4)
        # ==========================================
        
        for category in categories:
            # Создаём рамку для кнопки (чтобы добавить подпись)
            frame = ttk.Frame(self.buttons_frame)
            frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            # padx/pady - отступы между кнопками (можно увеличить)
            
            # ===== НАСТРОЙКИ КНОПОК =====
            btn = ttk.Button(
                frame,
                text=category.get("name", "Без названия"),
                command=lambda c=category: self.open_category(c),
                width=25      # Ширина кнопки (можно 30, 35)
            )
            # ============================
            btn.pack()
            
            # Переход к следующей позиции в сетке
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        # Растягиваем колонки, чтобы кнопки занимали всё пространство
        for i in range(max_cols):
            self.buttons_frame.columnconfigure(i, weight=1)
    
    def open_category(self, category):
        """Открывает категорию (папку) - показывает её содержимое"""
        self.navigation_stack.append({"type": "category", "data": category})
        self.update_navigation_ui()
        self.show_category_content(category)
    
    def show_category_content(self, category):
        """Показывает содержимое категории (подкатегории и скрипты)"""
        self.clear_buttons()
        
        subcategories = category.get("subcategories", [])
        scripts = category.get("scripts", [])
        
        if not subcategories and not scripts:
            label = tk.Label(self.buttons_frame, text="Пусто", fg="gray")
            label.pack(pady=20)
            return
        
        # Настройки сетки (те же, что и в show_root)
        row = 0
        col = 0
        max_cols = 3
        
        # Сначала показываем подкатегории (папки)
        for subcat in subcategories:
            frame = ttk.Frame(self.buttons_frame)
            frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            
            btn = ttk.Button(
                frame,
                text=subcat.get("name", "Без названия"),
                command=lambda s=subcat: self.open_subcategory(s),
                width=25
            )
            btn.pack()
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        # Затем показываем скрипты (действия)
        for script in scripts:
            frame = ttk.Frame(self.buttons_frame)
            frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            
            btn = ttk.Button(
                frame,
                text=script.get("description", script.get("name", "Без названия")),
                command=lambda s=script: self.run_script(s),
                width=25
            )
            btn.pack()
            
            # Если у скрипта есть горячая клавиша - показываем её под кнопкой
            hotkey = script.get("hotkey", "")
            if hotkey:
                hotkey_label = tk.Label(frame, text=hotkey, font=("Arial", 8), fg="gray")
                hotkey_label.pack()
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        for i in range(max_cols):
            self.buttons_frame.columnconfigure(i, weight=1)
    
    def open_subcategory(self, subcategory):
        """Открывает подкатегорию (показывает её скрипты)"""
        self.navigation_stack.append({"type": "subcategory", "data": subcategory})
        self.update_navigation_ui()
        
        self.clear_buttons()
        
        scripts = subcategory.get("scripts", [])
        
        if not scripts:
            label = tk.Label(self.buttons_frame, text="Нет скриптов", fg="gray")
            label.pack(pady=20)
            return
        
        row = 0
        col = 0
        max_cols = 3
        
        for script in scripts:
            frame = ttk.Frame(self.buttons_frame)
            frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            
            btn = ttk.Button(
                frame,
                text=script.get("description", script.get("name", "Без названия")),
                command=lambda s=script: self.run_script(s),
                width=25
            )
            btn.pack()
            
            hotkey = script.get("hotkey", "")
            if hotkey:
                hotkey_label = tk.Label(frame, text=hotkey, font=("Arial", 8), fg="gray")
                hotkey_label.pack()
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        for i in range(max_cols):
            self.buttons_frame.columnconfigure(i, weight=1)
    
    def go_back(self):
        """Возврат на предыдущий уровень (кнопка "Назад")"""
        if len(self.navigation_stack) > 1:
            self.navigation_stack.pop()
            self.update_navigation_ui()
            
            current = self.navigation_stack[-1]
            
            if current["type"] == "root":
                self.show_root()
            elif current["type"] == "category":
                self.show_category_content(current["data"])
    
    def update_navigation_ui(self):
        """Обновляет состояние кнопки "Назад" и хлебные крошки"""
        # Активируем/деактивируем кнопку "Назад"
        if len(self.navigation_stack) > 1:
            self.back_button.config(state="normal")
        else:
            self.back_button.config(state="disabled")
        
        # Формируем путь (хлебные крошки)
        path_parts = []
        for item in self.navigation_stack[1:]:
            if item["type"] == "category":
                path_parts.append(item["data"].get("name", "?"))
            elif item["type"] == "subcategory":
                path_parts.append(item["data"].get("name", "?"))
        
        self.path_label.config(text=" / ".join(path_parts))
    
    def setup_hotkeys(self):
        """Настраивает глобальные горячие клавиши (Ctrl+1, Ctrl+2 и т.д.)"""
        # Отвязываем старые хоткеи, если есть
        if hasattr(self, 'hotkey_handlers'):
            for handler in self.hotkey_handlers:
                try:
                    keyboard.unhook(handler)
                except:
                    pass
        
        self.hotkey_handlers = []
        
        # Собираем все скрипты из всех категорий и подкатегорий
        all_scripts = []
        for category in self.manifest.get("categories", []):
            for script in category.get("scripts", []):
                all_scripts.append(script)
            for subcat in category.get("subcategories", []):
                for script in subcat.get("scripts", []):
                    all_scripts.append(script)
        
        # Соответствие между текстовым обозначением и форматом библиотеки keyboard
        hotkey_map = {
            'Ctrl+1': 'ctrl+1',
            'Ctrl+2': 'ctrl+2',
            'Ctrl+3': 'ctrl+3',
            'Ctrl+4': 'ctrl+4',
            'Ctrl+5': 'ctrl+5',
            'Ctrl+6': 'ctrl+6',
            'Ctrl+7': 'ctrl+7',
            'Ctrl+8': 'ctrl+8',
            'Ctrl+9': 'ctrl+9',
            'Ctrl+0': 'ctrl+0',
        }
        
        for script in all_scripts:
            hotkey = script.get("hotkey", "")
            if hotkey in hotkey_map:
                combo = hotkey_map[hotkey]
                try:
                    handler = keyboard.add_hotkey(combo, lambda s=script: self.run_script_global(s))
                    self.hotkey_handlers.append(handler)
                except Exception as e:
                    log_error(f"Ошибка установки горячей клавиши {hotkey}: {e}")
    
    def run_script_global(self, script):
        """Запускает скрипт из глобальной горячей клавиши (перекидывает в главный поток)"""
        self.root.after(0, lambda: self.run_script(script))
    
    def run_script(self, script):
        """Запускает выбранный скрипт (AHK файл)"""
        # Защита: нельзя запустить новый скрипт, пока выполняется старый
        if self.script_running:
            messagebox.showwarning("Внимание", "Дождитесь завершения текущего скрипта")
            return
        
        script_name = script["name"]
        script_path = self.updater.get_script_path(script_name)
        
        # Если скрипта нет в кэше - предлагаем переустановить
        if not script_path or not script_path.exists():
            result = messagebox.askyesno(
                "Ошибка",
                f"Скрипт {script_name} не найден.\n\n"
                f"Возможно, кэш повреждён. Переустановить скрипты?"
            )
            if result:
                self.repair_cache()
            return
        
        # Запускаем скрипт
        self.script_running = True
        self.status_var.set(f"Запуск: {script.get('description', script_name)}")
        self.progress_bar.pack(side="bottom", fill="x", padx=20, pady=5)
        self.progress_bar.start(10)  # Запускаем анимацию прогресс-бара
        self.root.update()
        
        def execute():
            try:
                # Запускаем AHK скрипт с таймаутом 60 секунд
                result = subprocess.run([str(script_path)], shell=True, timeout=60, capture_output=True, text=True)
                if result.returncode != 0:
                    log_error(f"Скрипт {script_name} завершился с кодом {result.returncode}: {result.stderr}")
                self.root.after(0, self.on_script_finished)
            except subprocess.TimeoutExpired:
                log_error(f"Скрипт {script_name} превысил время ожидания (60 сек)")
                self.root.after(0, lambda: self.on_script_error("Превышено время ожидания (60 секунд)"))
            except Exception as e:
                log_error(f"Ошибка выполнения скрипта {script_name}: {e}")
                self.root.after(0, lambda: self.on_script_error(str(e)))
        
        threading.Thread(target=execute, daemon=True).start()
    
    def repair_cache(self):
        """Переустанавливает скрипты при повреждённом кэше"""
        self.status_var.set("Восстановление кэша...")
        
        def repair():
            try:
                import shutil
                cache_dir = self.updater.cache_dir
                if cache_dir.exists():
                    shutil.rmtree(cache_dir)
                cache_dir.mkdir(parents=True, exist_ok=True)
                
                manifest = self.updater.check_for_updates()
                if manifest:
                    self.updater.update_all_scripts(manifest)
                    self.root.after(0, lambda: messagebox.showinfo("Успех", "Кэш восстановлен. Перезапустите приложение."))
                else:
                    self.root.after(0, lambda: messagebox.showerror("Ошибка", "Не удалось восстановить кэш. Проверьте интернет."))
            except Exception as e:
                log_error(f"Ошибка восстановления кэша: {e}")
                self.root.after(0, lambda: messagebox.showerror("Ошибка", f"Не удалось восстановить кэш:\n{e}"))
            finally:
                self.root.after(0, lambda: self.status_var.set("Готов"))
        
        threading.Thread(target=repair, daemon=True).start()
    
    def on_script_finished(self):
        """Вызывается после успешного завершения скрипта"""
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.status_var.set("Готов")
        self.script_running = False
    
    def on_script_error(self, error_msg):
        """Вызывается при ошибке выполнения скрипта"""
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.status_var.set("Ошибка")
        self.script_running = False
        messagebox.showerror("Ошибка", f"Не удалось выполнить скрипт:\n{error_msg}")
    
    def check_updates_in_background(self):
        """Проверяет наличие обновлений в фоновом режиме"""
        def check():
            try:
                manifest = self.updater.check_for_updates()
                if manifest:
                    self.root.after(0, lambda: self.ask_update(manifest))
            except Exception as e:
                log_error(f"Ошибка проверки обновлений: {e}")
        
        threading.Thread(target=check, daemon=True).start()
    
    def ask_update(self, manifest):
        """Показывает диалог с предложением обновиться"""
        # Не предлагать обновление, если выполняется скрипт
        if self.script_running:
            return
        
        result = messagebox.askyesno(
            "Доступно обновление",
            f"Доступна новая версия {manifest['version']}\n\nОбновить скрипты?"
        )
        if result:
            self.perform_update(manifest)
    
    def perform_update(self, manifest):
        """Выполняет обновление скриптов"""
        self.status_var.set("Обновление...")
        
        def update():
            try:
                success = self.updater.update_all_scripts(manifest)
                self.root.after(0, lambda: self.update_complete(success, manifest))
            except Exception as e:
                log_error(f"Ошибка обновления: {e}")
                self.root.after(0, lambda: self.update_complete(False, manifest))
        
        threading.Thread(target=update, daemon=True).start()
    
    def update_complete(self, success, manifest):
        """Вызывается после завершения обновления"""
        if success:
            self.status_var.set(f"Обновлено до версии {manifest['version']}")
            messagebox.showinfo("Успех", f"Скрипты обновлены до версии {manifest['version']}")
            self.manifest = self.load_manifest()
            self.title_label.config(text=f"Время Путешествий v{self.manifest['version']}")
            self.show_root()
            self.setup_hotkeys()
        else:
            self.status_var.set("Ошибка обновления")
            messagebox.showerror("Ошибка", "Не удалось обновить скрипты.\nПроверьте интернет и попробуйте снова.")
    
    def manual_check_updates(self):
        """Ручная проверка обновлений (по кнопке)"""
        if self.script_running:
            messagebox.showwarning("Внимание", "Дождитесь завершения текущего скрипта")
            return
        
        self.status_var.set("Проверка обновлений...")
        
        def check():
            try:
                manifest = self.updater.check_for_updates()
                if manifest:
                    self.root.after(0, lambda: self.ask_update(manifest))
                else:
                    self.root.after(0, lambda: self.status_var.set("У вас последняя версия"))
                    self.root.after(0, lambda: messagebox.showinfo("Нет обновлений", "У вас последняя версия скриптов"))
            except Exception as e:
                log_error(f"Ошибка ручной проверки: {e}")
                self.root.after(0, lambda: self.status_var.set("Ошибка проверки"))
                self.root.after(0, lambda: messagebox.showerror("Ошибка", f"Не удалось проверить обновления:\n{e}"))
        
        threading.Thread(target=check, daemon=True).start()
    
    def run(self):
        """Запускает главный цикл приложения"""
        self.root.mainloop()


# ============================================================
# ТОЧКА ВХОДА (место, с которого начинается программа)
# ============================================================

if __name__ == "__main__":
    # Сначала проверяем, не запущено ли уже приложение
    if not check_single_instance():
        sys.exit(0)
    
    # Запускаем приложение
    try:
        root = tk.Tk()
        app = AutomationLauncher(root)
        app.run()
    except Exception as e:
        log_error(f"Критическая ошибка при запуске: {e}")
        messagebox.showerror("Критическая ошибка", f"Приложение не может запуститься:\n{e}\n\nОбратитесь к разработчику.")
        sys.exit(1)