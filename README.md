# TikTok Comment Extractor 🎯

Herramienta profesional para extraer **TODOS** los comentarios de videos de TikTok con análisis automático.

## ⚡ Características

- ✅ Extrae **TODOS** los comentarios (no solo los primeros 20)
- 📊 Análisis automático de sentimientos (positivos, negativos, preguntas)
- 🔤 Detección de palabras clave más mencionadas
- 📈 Estadísticas completas y reportes detallados
- 💾 Exporta a JSON con datos limpios
- 🚀 Comandos rápidos para análisis

## 🚀 Instalación

```bash
# Instalar dependencias
pip install TikTokApi
playwright install chromium
```

Recomiendo crear un entorno virtual antes de instalar:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # si creas este archivo
```

## ⚡ Inicio Rápido

```bash
# 1. Extraer comentarios de un video
python scripts/tiktok/tk_scraper.py "https://www.tiktok.com/@usuario/video/ID"

# 2. Analizar comentarios extraídos
python scripts/tiktok/tk_scraper.py  # ya guarda y muestra análisis básico

# 3. Ver estadísticas rápidas
python -c "import json; d=json.load(open('data/results/comentarios_limpios.json')); print(f'Total: {len(d)} comentarios')"
```

## 💻 Uso Detallado

### Extraer Comentarios

```bash
# Extraer todos los comentarios de un video
python extractor_api_tiktokapi.py "https://www.tiktok.com/@usuario/video/ID"

# Esto genera: comentarios_api_TIMESTAMP.json
```

### Analizar Comentarios

```bash
# Analizar el archivo más reciente automáticamente
python analizar_comentarios.py

# O especificar un archivo
python analizar_comentarios.py comentarios_api_20250113_123456.json

# Esto genera:
#   - comentarios_limpios.json (sin duplicados)
#   - comentarios_por_categoria.json (categorizados)
#   - reporte_analisis.txt (análisis completo)
```

### Comandos Útiles

```bash
# Ver estadísticas rápidas
./comandos_utiles.sh stats

# Buscar palabra clave
./comandos_utiles.sh buscar "palabra"

# Listar todos los archivos
./comandos_utiles.sh listar

# Ver ayuda
./comandos_utiles.sh ayuda
```

## 📊 Archivos Generados

### Extracción
- `comentarios_api_TIMESTAMP.json` - Comentarios extraídos del video

### Análisis
- `comentarios_limpios.json` - Comentarios únicos sin duplicados
- `comentarios_por_categoria.json` - Comentarios categorizados por sentimiento
- `reporte_analisis.txt` - Reporte completo con estadísticas

## 📄 Formato del JSON (API)

```json
[
  {
    "id": 1,
    "comment_id": "7429707963905887520",
    "text": "Texto del comentario",
    "likes": 145,
    "reply_count": 3,
    "create_time": 1704067200,
    "user": {
      "username": "usuario123",
      "nickname": "Nombre Usuario",
      "verified": false
    },
    "timestamp": "2026-01-13T00:36:43.439281",
    "video_url": "https://www.tiktok.com/@..."
  }
]
```

## 📈 Análisis Incluido

El script `analizar_comentarios.py` genera automáticamente:

- 📊 **Estadísticas generales:** Total de comentarios, promedios, duplicados
- 😊 **Análisis de sentimientos:** Positivos, negativos, neutrales, preguntas
- 🔤 **Palabras clave:** Top 30 palabras más mencionadas
- 📏 **Distribución:** Por longitud de comentarios
- 🔥 **Top comentarios:** Los más largos, preguntas más comunes, etc.

## 🔧 Solución de Problemas

### Error: "ModuleNotFoundError: No module named 'TikTokApi'"
```bash
pip install TikTokApi
playwright install chromium
```

### Error: "No se pudo abrir el panel de comentarios"
- El video puede tener comentarios deshabilitados
- Verifica que la URL sea correcta
- Intenta con otro video público

### TikTok bloquea la extracción
- Espera unos minutos entre extracciones masivas
- La API no oficial puede ser bloqueada temporalmente
- Intenta con diferentes videos

### No extrae todos los comentarios
- Algunos videos muy populares pueden tener limitaciones
- TikTok puede restringir el acceso a comentarios antiguos
- Verifica que el video tenga comentarios públicos

## 📁 Estructura del Proyecto
```
trollDetector/
├── scripts/
│   ├── facebook/              # [scripts/facebook/fb_scraper.py](scripts/facebook/fb_scraper.py)
│   ├── tiktok/                # [scripts/tiktok/tk_scraper.py](scripts/tiktok/tk_scraper.py)
│   └── common/                # helpers y utilidades compartidas

├── data/
│   ├── fb_scrapes/            # scrapes de Facebook (JSON)
│   ├── tk_scrapes/            # scrapes de TikTok (JSON)
│   └── results/               # resultados / CSV / análisis

├── docs/                      # Documentación y guías ([docs/GUIA_RAPIDA.md](docs/GUIA_RAPIDA.md))
├── notebooks/                 # Notebooks (p. ej. [notebooks/botsDetector.ipynb](notebooks/botsDetector.ipynb))
└── README.md
```

## 🎯 Casos de Uso


### Ejecutar el scraper de Facebook

1. Asegúrate de que `scripts/facebook/fb-cookies.json` exista si quieres ejecutar en modo `headless`.
2. Ejecuta:

```bash
python scripts/facebook/fb_scraper.py
```

Nota: el script abre un navegador Playwright. Si necesitas login, seguirá el flujo interactivo y guardará cookies en `scripts/facebook/fb-cookies.json`.

### Ejecutar el extractor de TikTok (API)

Extrae comentarios y guarda un JSON de salida en el directorio actual:

```bash
python scripts/tiktok/tk_scraper.py "https://www.tiktok.com/@adri.zip/video/7429707963905887520"
```

El script mostrará un resumen y guardará un archivo `comentarios_api_TIMESTAMP.json`.

### Marketing e Investigación
- Analizar engagement de campañas
- Identificar influencers activos
- Detectar tendencias de comentarios

### Moderación de Contenido
- Encontrar comentarios problemáticos
- Identificar usuarios spam
- Analizar patrones de comportamiento

## 🚀 Mejoras Futuras

- [ ] Detección automática de trolls/spam con ML
- [ ] Análisis de sentimientos más avanzado (modelos NLP)
- [ ] Procesamiento batch de múltiples videos
- [ ] Dashboard web con visualizaciones
- [ ] Exportar a Excel/CSV con gráficos
- [ ] Extracción de respuestas a comentarios
- [ ] Detección de bots y usuarios sospechosos

Ideas a corto plazo:
- Añadir `requirements.txt` y `scripts/run.sh` para facilitar ejecución
- Crear un `scripts/cli.py` que unifique las llamadas a los scrapers
- Normalizar salida en `data/results/` con timestamps y metadatos

---

## ⚠️ Notas importantes

- `scripts/facebook/fb-cookies.json` contiene cookies de sesión: protégelas si el repositorio es público.
- Playwright requiere instalación de navegadores (`playwright install chromium`).
- Las APIs no oficiales pueden ser bloqueadas por TikTok; usar con moderación y respetar TOS.

Si quieres, implemento un `scripts/cli.py` y un `requirements.txt` y hago un commit.

## Advertencia Legal

Esta herramienta es solo para fines educativos y de investigación. Respeta los términos de servicio de TikTok y las leyes de privacidad aplicables. No uses esta herramienta para:
- Spam
- Acoso
- Violación de privacidad
- Scraping masivo no autorizado
