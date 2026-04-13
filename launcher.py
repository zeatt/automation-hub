import tkinter as tk
from tkinter import ttk, messagebox
import json
import subprocess
import threading
from pathlib import Path
from updater import GitHubUpdater

class AutomationLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Automation Hub")
        self.root.geometry("750x550")
        
        # Инициализируем обновлятор
        self.updater = GitHubUpdater()
        
        # Стек навигации
        self.navigation_stack = []  # [{"type": "root"}, {"type": "category", "data": {...}}, ...]
        
        # Загружаем манифест
        self.manifest = self.load_manifest()
        
        self.setup_ui()
        
        # Показываем главный экран (категории)
        self.show_root()
        
        # Проверяем обновления в фоне
        self.check_updates_in_background()
    
    def load_manifest(self):
        """Загружает манифест из кэша updater'а"""
        cache_manifest = self.updater.cache_dir / "manifest.json"
        if cache_manifest.exists():
            with open(cache_manifest, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        local_manifest = Path(__file__).parent / "config" / "manifest.json"
        if local_manifest.exists():
            with open(local_manifest, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return {"version": "0.0.0", "categories": []}
    
    def setup_ui(self):
        """Создаёт интерфейс"""
        # Заголовок с версией
        self.title_label = tk.Label(self.root, text=f"Automation Hub v{self.manifest['version']}", font=("Arial", 14, "bold"))
        self.title_label.pack(pady=10)
        
        # Панель навигации (хлебные крошки + кнопка Назад)
        nav_frame = ttk.Frame(self.root)
        nav_frame.pack(fill="x", padx=20, pady=5)
        
        self.back_button = ttk.Button(nav_frame, text="← Назад", command=self.go_back, state="disabled")
        self.back_button.pack(side="left")
        
        self.path_label = tk.Label(nav_frame, text="", font=("Arial", 10), fg="gray")
        self.path_label.pack(side="left", padx=10)
        
        # Рамка для контента (кнопки папок/скриптов)
        self.content_frame = ttk.LabelFrame(self.root, text="Меню", padding=10)
        self.content_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Фрейм для кнопок (сетка)
        self.buttons_frame = ttk.Frame(self.content_frame)
        self.buttons_frame.pack(fill="both", expand=True)
        
        # Кнопка проверки обновлений
        update_btn = ttk.Button(self.root, text="🔄 Проверить обновления", command=self.manual_check_updates)
        update_btn.pack(pady=5)
        
        # Статус и прогресс-бар
        self.status_var = tk.StringVar(value="Готов")
        self.progress_bar = ttk.Progressbar(self.root, mode='indeterminate')
        
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief="sunken")
        status_bar.pack(side="bottom", fill="x")
        
        # Глобальные горячие клавиши (будут настроены после загрузки)
        self.setup_hotkeys()
    
    def clear_buttons(self):
        """Очищает все кнопки"""
        for widget in self.buttons_frame.winfo_children():
            widget.destroy()
    
    def show_root(self):
        """Показывает главный экран (список категорий)"""
        self.clear_buttons()
        self.navigation_stack = [{"type": "root"}]
        self.update_navigation_ui()
        
        categories = self.manifest.get("categories", [])
        
        if not categories:
            label = tk.Label(self.buttons_frame, text="Нет доступных категорий", fg="gray")
            label.pack(pady=20)
            return
        
        # Создаём сетку 3 колонки
        row = 0
        col = 0
        max_cols = 3
        
        for category in categories:
            frame = ttk.Frame(self.buttons_frame)
            frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            
            btn = ttk.Button(
                frame,
                text=category.get("name", "Без названия"),
                command=lambda c=category: self.open_category(c),
                width=25
            )
            btn.pack()
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        # Настраиваем растягивание колонок
        for i in range(max_cols):
            self.buttons_frame.columnconfigure(i, weight=1)
    
    def open_category(self, category):
        """Открывает категорию (папку)"""
        self.navigation_stack.append({"type": "category", "data": category})
        self.update_navigation_ui()
        self.show_category_content(category)
    
    def show_category_content(self, category):
        """Показывает содержимое категории (подкатегории или скрипты)"""
        self.clear_buttons()
        
        # Проверяем, есть ли подкатегории
        subcategories = category.get("subcategories", [])
        scripts = category.get("scripts", [])
        
        if not subcategories and not scripts:
            label = tk.Label(self.buttons_frame, text="Пусто", fg="gray")
            label.pack(pady=20)
            return
        
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
        
        # Затем показываем скрипты
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
            
            # Подпись с горячей клавишей
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
        """Возврат на предыдущий уровень"""
        if len(self.navigation_stack) > 1:
            self.navigation_stack.pop()
            self.update_navigation_ui()
            
            # Определяем, что показывать
            current = self.navigation_stack[-1]
            
            if current["type"] == "root":
                self.show_root()
            elif current["type"] == "category":
                self.show_category_content(current["data"])
    
    def update_navigation_ui(self):
        """Обновляет кнопку Назад и хлебные крошки"""
        # Кнопка Назад
        if len(self.navigation_stack) > 1:
            self.back_button.config(state="normal")
        else:
            self.back_button.config(state="disabled")
        
        # Хлебные крошки
        path_parts = []
        for item in self.navigation_stack[1:]:  # пропускаем root
            if item["type"] == "category":
                path_parts.append(item["data"].get("name", "?"))
            elif item["type"] == "subcategory":
                path_parts.append(item["data"].get("name", "?"))
        
        self.path_label.config(text=" / ".join(path_parts))
    
    def setup_hotkeys(self):
        """Настраивает глобальные горячие клавиши"""
        if hasattr(self, 'hotkey_handlers'):
            for handler in self.hotkey_handlers:
                keyboard.unhook(handler)
        
        self.hotkey_handlers = []
        
        # Собираем все скрипты из всех категорий и подкатегорий
        all_scripts = []
        for category in self.manifest.get("categories", []):
            for script in category.get("scripts", []):
                all_scripts.append(script)
            for subcat in category.get("subcategories", []):
                for script in subcat.get("scripts", []):
                    all_scripts.append(script)
        
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
                handler = keyboard.add_hotkey(combo, lambda s=script: self.run_script_global(s))
                self.hotkey_handlers.append(handler)
    
    def run_script_global(self, script):
        """Запускает скрипт из глобальной горячей клавиши"""
        self.root.after(0, lambda: self.run_script(script))
    
    def run_script(self, script):
        """Запускает выбранный скрипт"""
        script_name = script["name"]
        script_path = self.updater.get_script_path(script_name)
        
        if not script_path or not script_path.exists():
            messagebox.showerror("Ошибка", f"Скрипт {script_name} не найден")
            return
        
        self.status_var.set(f"Запуск: {script.get('description', script_name)}")
        self.progress_bar.pack(side="bottom", fill="x", padx=20, pady=5)
        self.progress_bar.start(10)
        self.root.update()
        
        def execute():
            try:
                subprocess.run([str(script_path)], shell=True, timeout=60)
                self.root.after(0, self.on_script_finished)
            except Exception as e:
                self.root.after(0, lambda: self.on_script_error(str(e)))
        
        threading.Thread(target=execute, daemon=True).start()
    
    def on_script_finished(self):
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.status_var.set("Готов")
    
    def on_script_error(self, error_msg):
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.status_var.set("Ошибка")
        messagebox.showerror("Ошибка", f"Не удалось выполнить скрипт:\n{error_msg}")
    
    def check_updates_in_background(self):
        def check():
            manifest = self.updater.check_for_updates()
            if manifest:
                self.root.after(0, lambda: self.ask_update(manifest))
        
        threading.Thread(target=check, daemon=True).start()
    
    def ask_update(self, manifest):
        result = messagebox.askyesno(
            "Доступно обновление",
            f"Доступна новая версия {manifest['version']}\n\nОбновить скрипты?"
        )
        if result:
            self.perform_update(manifest)
    
    def perform_update(self, manifest):
        self.status_var.set("Обновление...")
        
        def update():
            success = self.updater.update_all_scripts(manifest)
            self.root.after(0, lambda: self.update_complete(success, manifest))
        
        threading.Thread(target=update, daemon=True).start()
    
    def update_complete(self, success, manifest):
        if success:
            self.status_var.set(f"Обновлено до версии {manifest['version']}")
            messagebox.showinfo("Успех", f"Скрипты обновлены до версии {manifest['version']}")
            self.manifest = self.load_manifest()
            self.title_label.config(text=f"Automation Hub v{self.manifest['version']}")
            self.show_root()
            self.setup_hotkeys()
        else:
            self.status_var.set("Ошибка обновления")
            messagebox.showerror("Ошибка", "Не удалось обновить скрипты")
    
    def manual_check_updates(self):
        self.status_var.set("Проверка обновлений...")
        
        def check():
            manifest = self.updater.check_for_updates()
            if manifest:
                self.root.after(0, lambda: self.ask_update(manifest))
            else:
                self.root.after(0, lambda: self.status_var.set("У вас последняя версия"))
                self.root.after(0, lambda: messagebox.showinfo("Нет обновлений", "У вас последняя версия скриптов"))
        
        threading.Thread(target=check, daemon=True).start()
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    app = AutomationLauncher(root)
    app.run()