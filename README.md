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

## ⚡ Inicio Rápido

```bash
# 1. Extraer comentarios de un video
python extractor_api_tiktokapi.py "https://www.tiktok.com/@usuario/video/ID"

# 2. Analizar comentarios extraídos
python analizar_comentarios.py

# 3. Ver estadísticas rápidas
./comandos_utiles.sh stats
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

### Solo extrae 20 comentarios
**Solución:** Usa `extractor_api_tiktokapi.py` o `extractor_api_tiktokapipy.py` en lugar del método básico de Playwright.

### Error: "No se pudo abrir el panel de comentarios"
- El video puede tener comentarios deshabilitados
- Intenta con un video diferente
- Verifica que la URL sea correcta

### Error: "ModuleNotFoundError: No module named 'TikTokApi'"
```bash
pip install TikTokApi
# o
pip install tiktokapipy
```

### Error: "Playwright not installed"
```bash
playwright install chromium
```

### El navegador no se abre (headless=True)
Cambia `headless=False` a `headless=True` en el código si quieres ver el navegador.

### TikTok bloquea la extracción
- Espera unos minutos entre extracciones
- Usa diferentes videos
- Las APIs no oficiales pueden ser bloqueadas temporalmente

## 📁 Archivos del Proyecto

```
trollDetector/
├── detector.py                      # Script original (fixed)
├── extractor.py                     # Script básico mejorado
├── extractor_all_comments.py        # Método 1: Playwright con scroll
├── extractor_api_tiktokapi.py       # Método 2: TikTokApi (Recomendado) ⭐
├── extractor_api_tiktokapipy.py     # Método 3: tiktokapipy (Simple) 🚀
├── README.md                        # Este archivo
├── comentarios_*.json               # Comentarios extraídos (JSON)
├── comentarios_*.csv                # Comentarios extraídos (CSV)
└── debug_screenshot_*.png           # Screenshots de debug
```

## 🎯 Casos de Uso

### Análisis de Sentimientos
Usa los comentarios extraídos con herramientas de NLP para detectar:
- Sentimientos positivos/negativos
- Trolls y spam
- Temas principales de discusión

### Marketing e Investigación
- Analizar engagement de campañas
- Identificar influencers activos
- Detectar tendencias de comentarios

### Moderación de Contenido
- Encontrar comentarios problemáticos
- Identificar usuarios spam
- Analizar patrones de comportamiento

## 🚀 Próximas Mejoras

- [ ] Detección automática de trolls/spam usando ML
- [ ] Análisis de sentimientos integrado
- [ ] Soporte para múltiples videos (batch)
- [ ] Interfaz web con dashboard
- [ ] Extracción de respuestas a comentarios
- [ ] Exportar a Excel con gráficos
- [ ] Detección de bots

## Advertencia Legal

Esta herramienta es solo para fines educativos y de investigación. Respeta los términos de servicio de TikTok y las leyes de privacidad aplicables. No uses esta herramienta para:
- Spam
- Acoso
- Violación de privacidad
- Scraping masivo no autorizado
