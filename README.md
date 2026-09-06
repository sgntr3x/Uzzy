# Uzzy — Allied Telesis Seri Terminal & Yönetim Aracı

Uzzy, Allied Telesis switch/router cihazlarına **seri port (COM) üzerinden** bağlanmayı, PuTTY benzeri bir terminal ile komut göndermeyi ve yaygın switch yapılandırma işlemlerini (VLAN, PoE, STP, port kontrolü vb.) grafik arayüzden yapmayı sağlayan bir Windows masaüstü uygulamasıdır.

Python + `customtkinter` ile yazılmıştır, arka planda `pyserial` kullanır ve Google Gemini API ile AI destekli konfigürasyon önerileri sunar.

## Özellikler

- **PuTTY tarzı terminal** — cihaz komut satırına doğrudan yazım, komut geçmişi (yukarı/aşağı ok), Tab, Ctrl+C, Ctrl+L desteği
- **Otomatik port algılama** — yeni takılan/çıkarılan seri cihazları arka planda tarar, bulduğunda otomatik bağlanır
- **Otomatik model/port sayısı algılama** — `show version` ve `show interfaces status` çıktısını okuyarak switch modelini ve port sayısını (8/12/16/24/28/48/52) tespit eder
- **Görsel port paneli** — switch portlarını tıklayarak veya sürükleyerek seçme, sağ tık ile hızlı işlem menüsü
- **Switch yapılandırma menüsü**:
  - VLAN oluşturma / VLAN atama
  - STP ayarı
  - Management IP atama
  - PoE kontrolü
  - Port aç/kapat, portları varsayılana sıfırlama
  - MAC adres tablosu görüntüleme
  - Config karşılaştırma (diff) aracı
- **Config yedekleme** — `show running-config` çıktısını otomatik olarak dosyaya kaydetme
- **Kısayollar (Shortcuts)** — sık kullanılan komutları tek tıkla gönderme, kendi kısayollarınızı ekleyip silme (`uzzy_shortcuts.json`)
- **Şablonlar (Templates)** — hazır komut şablonları (`uzzy_templates.json`)
- **✨ AI Config** — Google Gemini API ile doğal dilden switch komutu/konfigürasyon üretimi
- Terminal font boyutu ayarı, çoklu baud rate desteği (9600 - 115200)

## Kurulum

### Gereksinimler

- Python 3.9+
- Windows (seri port / iconbitmap gibi bazı işlevler Windows'a özeldir; Linux/Mac'te sınırlı çalışabilir)

### Bağımlılıkları kurun

```bash
pip install pyserial customtkinter pillow google-generativeai
```

### Gemini API Anahtarı

AI Config özelliğinin çalışması için bir Gemini API anahtarına ihtiyaç var:

1. [Google AI Studio](https://aistudio.google.com/app/apikey) üzerinden ücretsiz bir API anahtarı oluşturun.
2. `get_api_key.py` dosyasını açıp anahtarınızı girin:
   ```python
   GEMINI_API_KEY = "api_anahtariniz"
   ```
3. Bu dosyayı `.gitignore`'a ekleyerek anahtarınızın yanlışlıkla commit edilmesini önleyin.

## Kullanım

1. Switch/router'ı USB-Seri (konsol) kablosuyla bilgisayara bağlayın.
2. Uygulamayı başlatın:
   ```bash
   python main.py
   ```
3. Uzzy, yeni takılan seri portu otomatik algılayıp bağlanmayı dener. Bağlanamazsa üstteki **"Otomatik Algıla"** butonunu kullanın.
4. Bağlantı kurulduktan sonra:
   - Üst araç çubuğundan model/host bilgisini, baud rate'i görebilirsiniz.
   - Alt kısımdaki terminale doğrudan komut yazabilir veya sağdaki **kısayol butonlarını** kullanabilirsiniz.
   - **Config ▼** menüsünden VLAN, PoE, STP, port kontrolü gibi işlemlere ulaşabilirsiniz.
   - **📥 Config İndir** ile mevcut çalışan konfigürasyonu `.txt` olarak kaydedebilirsiniz.
   - **✨ AI Config** ile Gemini destekli konfigürasyon önerisi alabilirsiniz.

### .exe olarak derleme

Repoda `main.spec`, `uzzy_frontend.spec` ve `build_exe.py` bulunuyor — PyInstaller ile tek dosya `.exe` üretmek için:

```bash
pip install pyinstaller
python build_exe.py
```

## Proje Yapısı

```
Uzzy/
├── main.py                  # Giriş noktası
├── uzzy_frontend.py          # Tkinter/customtkinter arayüzü (ana GUI mantığı)
├── uzzy_backend.py           # Seri port tarama ve bağlantı yönetimi (pyserial)
├── get_api_key.py            # Gemini API anahtarı
├── port_grid.py               
├── commands.json
├── uzzy_shortcuts.json        # Kullanıcı kısayolları (çalışma zamanında oluşur/güncellenir)
├── uzzy_templates.json        # Komut şablonları
├── uzzy_icon.ico / .png       # Uygulama ikonu
├── modules/
│   ├── mac_table.py           # MAC adres tablosu penceresi
│   ├── command_builder.py     # Komut oluşturma yardımcıları
│   ├── ai_config.py           # Gemini AI Config penceresi
│   ├── switch_configs.py      # VLAN / STP / Management IP / Port kontrolü
│   ├── poe_config.py          # PoE kontrol penceresi
│   ├── config_diff.py         # Config karşılaştırma aracı
│   └── templates.py           # Şablon yöneticisi
└── main.spec / uzzy_frontend.spec / build_exe.py   # PyInstaller derleme dosyaları
```


