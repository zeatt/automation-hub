import tkinter as tk
from tkinter import ttk
import json
import os
from pathlib import Path

class AutomationLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Automation Hub")
        self.root.geometry("500x400")
        
        # Определяем пути
        self.app_dir = Path(__file__).parent
        self.config_dir = self.app_dir / "config"
        self.scripts_dir = self.app_dir / "scripts"
        
        # Загружаем манифест
        self.manifest = self.load_manifest()
        
        self.setup_ui()
    
    def load_manifest(self):
        manifest_path = self.config_dir / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"version": "1.0.0", "scripts": []}
    
    def setup_ui(self):
        # Заголовок с версией
        title = tk.Label(self.root, text=f"Automation Hub v{self.manifest['version']}", font=("Arial", 14, "bold"))
        title.pack(pady=10)
        
        # Рамка для кнопок
        frame = ttk.LabelFrame(self.root, text="Доступные скрипты", padding=10)
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Временная заглушка
        label = tk.Label(frame, text="Здесь будут кнопки для запуска скриптов", fg="gray")
        label.pack(pady=20)
        
        # Статус
        self.status_var = tk.StringVar(value="Готов")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief="sunken")
        status_bar.pack(side="bottom", fill="x")
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    app = AutomationLauncher(root)
    app.run()