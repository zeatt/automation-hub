import requests
import json
import hashlib
import os
import sys
from pathlib import Path

class GitHubUpdater:
    """Автообновление скриптов с GitHub"""
    
    def __init__(self):
        # GitHub репозиторий (RAW доступ)
        self.raw_url = "https://raw.githubusercontent.com/zeatt/automation-hub/main"
        self.manifest_url = f"{self.raw_url}/config/manifest.json"
        
        # Локальные пути
        self.app_dir = Path(os.environ.get('LOCALAPPDATA')) / "AutomationHub"
        self.cache_dir = self.app_dir / "scripts_cache"
        self.config_dir = self.app_dir / "config_local"
        self.logs_dir = self.app_dir / "logs"
        
        # Создаём папки
        for dir_path in [self.cache_dir, self.config_dir, self.logs_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        self.version_file = self.app_dir / ".version"
    
    def get_current_version(self) -> str:
        """Читаем текущую версию из локального файла"""
        if self.version_file.exists():
            with open(self.version_file, 'r') as f:
                return f.read().strip()
        return "0.0.0"
    
    def save_version(self, version: str):
        """Сохраняем текущую версию"""
        with open(self.version_file, 'w') as f:
            f.write(version)
    
    def check_for_updates(self):
        """Проверяем наличие обновлений на GitHub"""
        try:
            # Скачиваем манифест
            response = requests.get(self.manifest_url, timeout=10)
            response.raise_for_status()
            manifest = response.json()
            
            current_version = self.get_current_version()
            
            if manifest['version'] != current_version:
                return manifest
            return None
                
        except:
            return None
    
    def download_file(self, url, save_path):
        """Скачивает файл"""
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            f.write(response.content)
        return True
    
    def update_all_scripts(self, manifest):
        """Обновляет все скрипты"""
        print(f"Обновление до версии {manifest['version']}...")
        
        for script in manifest.get('scripts', []):
            script_name = script['name']
            script_url = f"{self.raw_url}/scripts/ahk/{script_name}"
            save_path = self.cache_dir / script_name
            
            try:
                self.download_file(script_url, save_path)
                print(f"  ✓ {script_name}")
            except:
                print(f"  ✗ Ошибка: {script_name}")
        
        self.save_version(manifest['version'])
        return True
    
    def get_script_path(self, script_name):
        """Возвращает путь к скрипту (из кэша)"""
        script_path = self.cache_dir / script_name
        
        # Если скрипта нет в кэше, пытаемся скачать
        if not script_path.exists():
            manifest = self.check_for_updates()
            if manifest:
                self.update_all_scripts(manifest)
        
        return script_path if script_path.exists() else None