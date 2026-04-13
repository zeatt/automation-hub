import requests
import json
import os
from pathlib import Path

class GitHubUpdater:
    def __init__(self):
        self.raw_url = "https://raw.githubusercontent.com/zeatt/automation-hub/main"
        self.manifest_url = f"{self.raw_url}/config/manifest.json"
        
        self.app_dir = Path(os.environ.get('LOCALAPPDATA')) / "TimeToTravel"
        self.cache_dir = self.app_dir / "scripts_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.version_file = self.app_dir / ".version"
        self.local_manifest_path = self.cache_dir / "manifest.json"
    
    def get_current_version(self):
        if self.local_manifest_path.exists():
            try:
                with open(self.local_manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                    return manifest.get('version', '0.0.0')
            except:
                pass
        return "0.0.0"
    
    def save_manifest(self, manifest):
        with open(self.local_manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        with open(self.version_file, 'w') as f:
            f.write(manifest['version'])
    
    def check_for_updates(self):
        try:
            response = requests.get(self.manifest_url, timeout=10)
            response.raise_for_status()
            remote_manifest = response.json()
            remote_version = remote_manifest.get('version', '0.0.0')
            
            local_version = self.get_current_version()
            
            if remote_version != local_version:
                return remote_manifest
            return None
        except Exception as e:
            print(f"Ошибка: {e}")
            return None
    
    def download_file(self, url, save_path):
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            f.write(response.content)
    
    def update_all_scripts(self, manifest):
        """Обновляет все скрипты и сохраняет манифест"""
        print(f"Обновление до версии {manifest['version']}...")
        
        # Сохраняем манифест в кэш
        manifest_path = self.cache_dir / "manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        print("  ✓ manifest.json сохранён")
        
        # Собираем все скрипты из новой структуры (categories)
        all_scripts = []
        for category in manifest.get("categories", []):
            # Скрипты на уровне категории
            for script in category.get("scripts", []):
                all_scripts.append(script)
            # Скрипты в подкатегориях
            for subcat in category.get("subcategories", []):
                for script in subcat.get("scripts", []):
                    all_scripts.append(script)
        
        # Скачиваем каждый скрипт
        for script in all_scripts:
            script_name = script["name"]
            script_url = f"{self.raw_url}/scripts/ahk/{script_name}"
            save_path = self.cache_dir / script_name
            
            try:
                self.download_file(script_url, save_path)
                print(f"  ✓ {script_name}")
            except Exception as e:
                print(f"  ✗ Ошибка: {script_name} - {e}")
        
        self.save_version(manifest['version'])
        return True
    
    def get_script_path(self, script_name):
        script_path = self.cache_dir / script_name
        return script_path if script_path.exists() else None