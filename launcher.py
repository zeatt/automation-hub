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
        self.root.geometry("550x500")
        
        # Инициализируем обновлятор
        self.updater = GitHubUpdater()
        
        # Загружаем манифест (сначала локальный, потом с GitHub)
        self.manifest = self.load_manifest()
        
        self.setup_ui()
        
        # Проверяем обновления в фоне
        self.check_updates_in_background()
    
    def load_manifest(self):
        """Загружает манифест из локальной папки или из кэша"""
        # Сначала пробуем из папки проекта (для разработки)
        local_manifest = Path(__file__).parent / "config" / "manifest.json"
        if local_manifest.exists():
            with open(local_manifest, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # Потом из кэша updater'а
        cache_manifest = self.updater.cache_dir / "manifest.json"
        if cache_manifest.exists():
            with open(cache_manifest, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return {"version": "0.0.0", "scripts": []}
    
    def check_updates_in_background(self):
        """Проверяет обновления в фоновом потоке"""
        def check():
            manifest = self.updater.check_for_updates()
            if manifest:
                # Показываем диалог в главном потоке
                self.root.after(0, lambda: self.ask_update(manifest))
        
        thread = threading.Thread(target=check, daemon=True)
        thread.start()
    
    def ask_update(self, manifest):
        """Спрашиваем пользователя об обновлении"""
        result = messagebox.askyesno(
            "Доступно обновление",
            f"Доступна новая версия {manifest['version']}\n\n"
            f"Обновить скрипты?"
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
            # Обновляем интерфейс
            self.refresh_scripts()
        else:
            self.status_var.set("Ошибка обновления")
            messagebox.showerror("Ошибка", "Не удалось обновить скрипты")
    
    def refresh_scripts(self):
        """Обновляет список скриптов в интерфейсе"""
        self.manifest = self.load_manifest()
        
        # Очищаем старые кнопки
        for btn in self.buttons:
            btn.destroy()
        self.buttons.clear()
        
        # Создаём новые кнопки
        for script in self.manifest.get("scripts", []):
            btn = ttk.Button(
                self.buttons_frame, 
                text=script.get("description", script["name"]),
                command=lambda s=script: self.run_script(s),
                width=45
            )
            btn.pack(pady=3)
            self.buttons.append(btn)
        
        # Обновляем заголовок с версией
        self.title_label.config(text=f"Automation Hub v{self.manifest['version']}")
    
    def setup_ui(self):
        # Заголовок с версией
        self.title_label = tk.Label(self.root, text=f"Automation Hub v{self.manifest['version']}", font=("Arial", 14, "bold"))
        self.title_label.pack(pady=10)
        
        # Рамка для кнопок
        frame = ttk.LabelFrame(self.root, text="Доступные скрипты", padding=10)
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Создаём фрейм для кнопок (чтобы можно было очищать)
        self.buttons_frame = ttk.Frame(frame)
        self.buttons_frame.pack(fill="both", expand=True)
        
        # Создаём кнопки для каждого скрипта из манифеста
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
        
        # Если скриптов нет
        if not self.buttons:
            label = tk.Label(self.buttons_frame, text="Нет доступных скриптов", fg="gray")
            label.pack(pady=20)
        
        # Кнопка "Проверить обновления" вручную
        update_btn = ttk.Button(frame, text="🔄 Проверить обновления", command=self.manual_check_updates)
        update_btn.pack(pady=10)
        
        # Статус
        self.status_var = tk.StringVar(value="Готов")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief="sunken")
        status_bar.pack(side="bottom", fill="x")
    
    def manual_check_updates(self):
        """Ручная проверка обновлений"""
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
        
        # Получаем путь к скрипту из кэша
        script_path = self.updater.get_script_path(script_name)
        
        if not script_path or not script_path.exists():
            messagebox.showerror("Ошибка", f"Скрипт {script_name} не найден. Попробуйте обновить.")
            return
        
        self.status_var.set(f"Запуск: {script_name}")
        
        def execute():
            try:
                subprocess.run([str(script_path)], shell=True, timeout=60)
                self.root.after(0, lambda: self.status_var.set("Готов"))
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set("Ошибка"))
                self.root.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
        
        threading.Thread(target=execute, daemon=True).start()
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    app = AutomationLauncher(root)
    app.run()