import os
import subprocess
import sys

def build():
    print(f"Kullanılan Python: {sys.executable}")
    
    print("\n1. Gerekli kütüphaneler indiriliyor/kontrol ediliyor...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller", "google-generativeai", "customtkinter"])
    
    print("\n2. EXE dosyası oluşturuluyor (Bu işlem biraz sürebilir, lütfen bekleyin)...")
    
    # Windows için ayırıcı noktalı virgül (;), Mac/Linux için iki nokta (:)
    separator = ";" if os.name == 'nt' else ":"
    
    subprocess.check_call([
        sys.executable, "-m", "PyInstaller", 
        "--clean",
        "--noconsole", 
        "--onefile", 
        "--add-data", f"uzzy_icon.png{separator}.", 
        "--collect-all", "google.generativeai",
        "--collect-all", "google.ai.generativelanguage",
        "--collect-all", "customtkinter",
        "--collect-all", "google.api_core",
        "--collect-all", "google.auth",
        "--collect-all", "google.protobuf",
        "--collect-all", "grpc",
        "--collect-all", "pydantic",
        "--copy-metadata", "google-generativeai",
        "--copy-metadata", "google-api-core",
        "--copy-metadata", "grpcio",
        "--copy-metadata", "pydantic",
        "main.py"
    ])
    
    print("\n🎉 BAŞARILI! Lütfen projenizin içindeki 'dist' klasörüne bakın. Uygulamanız hazır!")

if __name__ == "__main__":
    build()