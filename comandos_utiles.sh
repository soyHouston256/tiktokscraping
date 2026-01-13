#!/bin/bash
# Comandos útiles para TikTok Comment Extractor

echo "🎯 TikTok Comment Extractor - Comandos Útiles"
echo "=============================================="
echo ""

# Función para extraer comentarios
extraer() {
    if [ -z "$1" ]; then
        echo "❌ Error: Proporciona la URL del video"
        echo "Uso: ./comandos_utiles.sh extraer 'URL_DEL_VIDEO'"
        return 1
    fi

    echo "📱 Extrayendo comentarios de: $1"
    python extractor_api_tiktokapi.py "$1"
}

# Función para analizar comentarios
analizar() {
    echo "📊 Analizando comentarios..."
    python analizar_comentarios.py
}

# Función para ver estadísticas rápidas
stats() {
    FILE=${1:-comentarios_limpios.json}
    if [ ! -f "$FILE" ]; then
        echo "❌ Archivo no encontrado: $FILE"
        return 1
    fi

    echo "📈 Estadísticas de: $FILE"
    python -c "
import json
with open('$FILE') as f:
    data = json.load(f)
    print(f'Total comentarios: {len(data)}')
    print(f'Promedio longitud: {sum(len(c[\"text\"]) for c in data)/len(data):.0f} chars')
    preguntas = sum(1 for c in data if '?' in c['text'])
    print(f'Preguntas: {preguntas} ({preguntas/len(data)*100:.1f}%)')
"
}

# Función para buscar palabra clave
buscar() {
    if [ -z "$1" ]; then
        echo "❌ Error: Proporciona una palabra clave"
        echo "Uso: ./comandos_utiles.sh buscar 'palabra'"
        return 1
    fi

    FILE=${2:-comentarios_limpios.json}
    echo "🔍 Buscando '$1' en $FILE..."
    python -c "
import json
with open('$FILE') as f:
    data = json.load(f)
    matches = [c for c in data if '$1'.lower() in c['text'].lower()]
    print(f'Encontrados: {len(matches)} comentarios con \"$1\"')
    print()
    for i, c in enumerate(matches[:10], 1):
        print(f'{i}. {c[\"text\"][:80]}...')
"
}

# Función para listar todos los archivos generados
listar() {
    echo "📁 Archivos generados:"
    echo ""
    echo "📊 Scripts:"
    ls -1 *.py 2>/dev/null | while read file; do
        echo "   ✓ $file"
    done

    echo ""
    echo "📄 Datos:"
    ls -lh comentarios_*.json 2>/dev/null | awk '{print "   ✓", $9, "("$5")"}'

    echo ""
    echo "📈 Reportes:"
    ls -lh reporte_*.txt 2>/dev/null | awk '{print "   ✓", $9, "("$5")"}'
}

# Función para limpiar archivos temporales
limpiar() {
    echo "🧹 Limpiando archivos temporales..."
    rm -f debug_screenshot_*.png
    rm -f page_content.html
    echo "✓ Archivos de debug eliminados"
}

# Función para ayuda
ayuda() {
    echo "📚 Comandos disponibles:"
    echo ""
    echo "  extraer 'URL'     - Extraer comentarios de un video"
    echo "  analizar          - Analizar comentarios extraídos"
    echo "  stats [archivo]   - Mostrar estadísticas rápidas"
    echo "  buscar 'palabra'  - Buscar palabra en comentarios"
    echo "  listar            - Listar todos los archivos"
    echo "  limpiar           - Limpiar archivos temporales"
    echo "  ayuda             - Mostrar esta ayuda"
    echo ""
    echo "Ejemplos:"
    echo "  ./comandos_utiles.sh extraer 'https://www.tiktok.com/@user/video/123'"
    echo "  ./comandos_utiles.sh buscar 'claude'"
    echo "  ./comandos_utiles.sh stats comentarios_limpios.json"
}

# Main
case "$1" in
    extraer)
        extraer "$2"
        ;;
    analizar)
        analizar
        ;;
    stats)
        stats "$2"
        ;;
    buscar)
        buscar "$2" "$3"
        ;;
    listar)
        listar
        ;;
    limpiar)
        limpiar
        ;;
    ayuda|help|--help|-h)
        ayuda
        ;;
    *)
        echo "🎯 TikTok Comment Extractor"
        echo ""
        echo "Uso: ./comandos_utiles.sh [comando] [argumentos]"
        echo ""
        ayuda
        ;;
esac
