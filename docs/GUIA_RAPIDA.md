# 🚀 Guía Rápida - Extractor de Comentarios de TikTok

## ❓ Problema: Solo obtengo 20 comentarios

El método básico con Playwright solo extrae los comentarios visibles (~20). Para obtener **TODOS** los comentarios necesitas usar una API.

## ✅ Soluciones Disponibles

### 1️⃣ Método Playwright Mejorado (Actual) ⚠️
**Archivo:** `extractor_all_comments.py`

```bash
python extractor_all_comments.py
```

**Pros:**
- Ya instalado ✓
- No necesita APIs externas
- Funciona ahora mismo

**Contras:**
- Solo extrae ~20-50 comentarios
- Limitado por el scroll de TikTok

**Resultado actual:** 20 comentarios extraídos

---

### 2️⃣ TikTokApi - Para TODOS los comentarios (Recomendado) ⭐

**Instalación:**
```bash
pip install TikTokApi
```

**Uso:**
```bash
python extractor_api_tiktokapi.py "URL_DEL_VIDEO"
```

**Pros:**
- Extrae **TODOS** los comentarios (sin límite)
- Incluye metadata completa (likes, respuestas, usuarios)
- Librería más popular y mantenida

**Contras:**
- Requiere instalación adicional
- Puede ser bloqueada temporalmente por TikTok

**Documentación:** https://github.com/davidteather/TikTok-Api

---

### 3️⃣ tiktokapipy - API Simple 🚀

**Instalación:**
```bash
pip install tiktokapipy
```

**Uso:**
```bash
python extractor_api_tiktokapipy.py "URL_DEL_VIDEO"
```

**Pros:**
- Código más simple y moderno
- Exporta a CSV automáticamente
- Fácil de usar

**Contras:**
- Actualmente tiene problemas con bloqueos de TikTok (error JSON)
- Puede no funcionar en todos los casos

**Estado:** ⚠️ Con errores actualmente debido a bloqueos de TikTok

---

## 🎯 Recomendación

### Para obtener TODOS los comentarios:

**Opción A: TikTokApi (Más confiable)**
```bash
# 1. Instalar
pip install TikTokApi

# 2. Ejecutar
python extractor_api_tiktokapi.py "https://www.tiktok.com/@adri.zip/video/7429707963905887520"
```

**Opción B: Usar servicio de terceros**
Si las APIs no funcionan, considera usar servicios pagos como:
- Apify TikTok Scraper
- ScrapingBee
- Bright Data

---

## 🔍 ¿Cuántos comentarios tiene realmente el video?

Para verificar:
1. Abre el video en TikTok
2. Mira el contador de comentarios debajo del video
3. Compara con lo que extrajiste

**Nota:** Es posible que el video de prueba solo tenga 20 comentarios realmente.

---

## 💡 Próximos Pasos

### Si quieres extraer TODOS los comentarios:

1. **Prueba TikTokApi:**
   ```bash
   pip install TikTokApi
   python extractor_api_tiktokapi.py "TU_URL"
   ```

2. **Si TikTokApi falla:** TikTok puede estar bloqueando temporalmente. Opciones:
   - Espera unas horas e intenta de nuevo
   - Usa un video diferente
   - Considera servicios pagos de scraping

3. **Para análisis de los 20 comentarios actuales:**
   - Ya tienes el archivo JSON generado
   - Puedes analizar sentimientos, palabras clave, etc.
   - El formato es compatible con herramientas de NLP

---

## 📊 Archivos Generados

Actualmente tienes:
- ✅ `comentarios_20260113_003643.json` - 20 comentarios
- ✅ `comentarios_completo_20260113_004404.json` - 20 comentarios
- ✅ Screenshots de debug
- ✅ Scripts funcionales para Playwright

---

## 🆘 Ayuda Adicional

### El video solo tiene 20 comentarios?
Verifica en TikTok directamente el contador de comentarios.

### Quiero probar con otro video
Usa cualquiera de los scripts con una URL diferente:
```bash
python extractor_all_comments.py "https://www.tiktok.com/@otro/video/123456"
```

### Necesito más información de los comentarios
Usa los extractores con API que incluyen:
- Likes por comentario
- Número de respuestas
- Info del usuario (verificado, followers)
- Timestamp exacto

---

## 📚 Recursos

- [TikTok-Api GitHub](https://github.com/davidteather/TikTok-Api)
- [tiktokapipy Docs](https://pypi.org/project/tiktokapipy/)
- [ScrapFly TikTok Guide 2026](https://scrapfly.io/blog/posts/how-to-scrape-tiktok-python-json)
