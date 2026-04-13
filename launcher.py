import tkinter as tk
from tkinter import ttk, messagebox
import json
import subprocess
import threading
from pathlib import Path
from updater import GitHubUpdater
import keyboard

class AutomationLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Automation Hub")
        self.root.geometry("550x500")
        
        # Инициализируем обновлятор
        self.updater = GitHubUpdater()
        
        # Загружаем манифест
        self.manifest = self.load_manifest()
        
        self.setup_ui()
        
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
        
        return {"version": "0.0.0", "scripts": []}
    
    def check_updates_in_background(self):
        """Проверяет обновления в фоновом потоке"""
        def check():
            manifest = self.updater.check_for_updates()
            if manifest:
                self.root.after(0, lambda: self.ask_update(manifest))
        
        thread = threading.Thread(target=check, daemon=True)
        thread.start()
    
    def ask_update(self, manifest):
        """Спрашиваем пользователя об обновлении"""
        result = messagebox.askyesno(
            "Доступно обновление",
            f"Доступна новая версия {manifest['version']}\n\nОбновить скрипты?"
        )
        if result:
            self.perform_update(manifest)
    
    def perform_update(self, manifest):
        """Выполняет обновление в фоне"""
        self.status_var.set("Обновление...")
        
        def update():
            success = self.updater.update_all_scripts(manifest)
            self.root.after(0, lambda: self.update_complete(success, manifest))
        
        thread = threading.Thread(target=update, daemon=True)
        thread.start()
    
    def update_complete(self, success, manifest):
        """После завершения обновления"""
        if success:
            self.status_var.set(f"Обновлено до версии {manifest['version']}")
            messagebox.showinfo("Успех", f"Скрипты обновлены до версии {manifest['version']}")
            self.refresh_scripts()
        else:
            self.status_var.set("Ошибка обновления")
            messagebox.showerror("Ошибка", "Не удалось обновить скрипты")
    
    def refresh_scripts(self):
        """Обновляет список скриптов в интерфейсе"""
        self.manifest = self.load_manifest()
        
        for btn in self.buttons:
            btn.destroy()
        self.buttons.clear()
        
        for script in self.manifest.get("scripts", []):
            btn = ttk.Button(
                self.buttons_frame, 
                text=script.get("description", script["name"]),
                command=lambda s=script: self.run_script(s),
                width=45
            )
            btn.pack(pady=3)
            self.buttons.append(btn)
        
        self.title_label.config(text=f"Automation Hub v{self.manifest['version']}")
        
        # Пересоздаём горячие клавиши
        self.setup_hotkeys()
    
    def setup_hotkeys(self):
        """Настраивает глобальные горячие клавиши (работают везде)"""
        # Отвязываем старые хоткеи, если есть
        if hasattr(self, 'hotkey_handlers'):
            for handler in self.hotkey_handlers:
                keyboard.unhook(handler)
        
        self.hotkey_handlers = []
        
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
        
        for script in self.manifest.get("scripts", []):
            hotkey = script.get("hotkey", "")
            if hotkey in hotkey_map:
                combo = hotkey_map[hotkey]
                handler = keyboard.add_hotkey(combo, lambda s=script: self.run_script_global(s))
                self.hotkey_handlers.append(handler)
        
        self.status_var.set("Горячие клавиши: Ctrl+1, Ctrl+2... (работают везде)")
    
    def run_script_global(self, script):
        """Запускает скрипт из глобальной горячей клавиши (безопасно для потоков)"""
        self.root.after(0, lambda: self.run_script(script))
    
    def setup_ui(self):
        self.title_label = tk.Label(self.root, text=f"Automation Hub v{self.manifest['version']}", font=("Arial", 14, "bold"))
        self.title_label.pack(pady=10)
        
        frame = ttk.LabelFrame(self.root, text="Доступные скрипты", padding=10)
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.buttons_frame = ttk.Frame(frame)
        self.buttons_frame.pack(fill="both", expand=True)
        
        self.buttons = []
        for script in self.manifest.get("scripts", []):
            btn = ttk.Button(
                self.buttons_frame, 
                text=script.get("description", script["name"]),
                command=lambda s=script: self.run_script(s),
                width=45
            )
            btn.pack(pady=3)
            self.buttons.append(btn)
        
        if not self.buttons:
            label = tk.Label(self.buttons_frame, text="Нет доступных скриптов", fg="gray")
            label.pack(pady=20)
        
        update_btn = ttk.Button(frame, text="🔄 Проверить обновления", command=self.manual_check_updates)
        update_btn.pack(pady=10)
        
        self.status_var = tk.StringVar(value="Готов")
        self.progress_bar = ttk.Progressbar(self.root, mode='indeterminate')
        
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief="sunken")
        status_bar.pack(side="bottom", fill="x")
        
        # Настраиваем горячие клавиши
        self.setup_hotkeys()
    
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
    
    def run_script(self, script):
        """Запускает выбранный скрипт из кэша"""
        script_name = script["name"]
        
        script_path = self.updater.get_script_path(script_name)
        
        if not script_path or not script_path.exists():
            messagebox.showerror("Ошибка", f"Скрипт {script_name} не найден. Попробуйте обновить.")
            return
        
        self.status_var.set(f"Запуск: {script_name}")
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
        messagebox.showinfo("Готово", "Скрипт выполнен успешно!")
    
    def on_script_error(self, error_msg):
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.status_var.set("Ошибка")
        messagebox.showerror("Ошибка", f"Не удалось выполнить скрипт:\n{error_msg}")
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    app = AutomationLauncher(root)
    app.run()