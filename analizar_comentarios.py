"""
Script para analizar y limpiar comentarios extraídos
"""

import json
from datetime import datetime
from collections import Counter
import re


def load_comments(filename):
    """Carga comentarios desde archivo JSON"""
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)


def remove_duplicates(comments):
    """Elimina comentarios duplicados basándose en el texto"""
    seen = set()
    unique = []

    for comment in comments:
        text = comment['text'].strip().lower()
        if text and text not in seen:
            seen.add(text)
            unique.append(comment)

    return unique


def analyze_sentiment_simple(text):
    """Análisis de sentimiento simple basado en palabras clave"""
    text_lower = text.lower()

    positive_words = ['excelente', 'genial', 'increíble', 'perfecto', 'bueno', 'gracias',
                      'felicitaciones', 'adoro', 'amo', 'wow', 'great', 'love', '❤️', '😊', '🔥']
    negative_words = ['malo', 'terrible', 'no funciona', 'problema', 'error', 'pésimo',
                      'odio', 'horrible', 'basura', '😡', '😠', '👎']
    question_words = ['?', 'cómo', 'qué', 'cuál', 'dónde', 'cuándo', 'quién', 'por qué']

    pos_count = sum(1 for word in positive_words if word in text_lower)
    neg_count = sum(1 for word in negative_words if word in text_lower)
    is_question = any(word in text_lower for word in question_words)

    if is_question:
        return 'pregunta'
    elif pos_count > neg_count:
        return 'positivo'
    elif neg_count > pos_count:
        return 'negativo'
    else:
        return 'neutral'


def categorize_comments(comments):
    """Categoriza comentarios por tipo"""
    categories = {
        'preguntas': [],
        'positivos': [],
        'negativos': [],
        'neutrales': [],
        'muy_cortos': [],  # menos de 10 caracteres
        'largos': []  # más de 100 caracteres
    }

    for comment in comments:
        text = comment['text']
        sentiment = analyze_sentiment_simple(text)

        # Por sentimiento
        if sentiment == 'pregunta':
            categories['preguntas'].append(comment)
        elif sentiment == 'positivo':
            categories['positivos'].append(comment)
        elif sentiment == 'negativo':
            categories['negativos'].append(comment)
        else:
            categories['neutrales'].append(comment)

        # Por longitud
        if len(text) < 10:
            categories['muy_cortos'].append(comment)
        elif len(text) > 100:
            categories['largos'].append(comment)

    return categories


def extract_keywords(comments, top_n=20):
    """Extrae las palabras clave más comunes"""
    # Stopwords en español e inglés
    stopwords = {
        'que', 'para', 'con', 'por', 'del', 'las', 'los', 'una', 'esto', 'ese', 'esta',
        'the', 'and', 'for', 'are', 'but', 'not', 'you', 'with', 'que', 'como', 'más',
        'pero', 'muy', 'todo', 'todos', 'eso', 'puede', 'hacer', 'solo', 'cuando', 'donde'
    }

    words = []
    for comment in comments:
        # Limpiar y tokenizar
        text = re.sub(r'[^\w\s]', ' ', comment['text'].lower())
        tokens = text.split()
        words.extend([w for w in tokens if len(w) > 3 and w not in stopwords])

    return Counter(words).most_common(top_n)


def generate_report(comments, output_file='reporte_analisis.txt'):
    """Genera un reporte completo del análisis"""

    # Eliminar duplicados
    unique_comments = remove_duplicates(comments)
    duplicates_removed = len(comments) - len(unique_comments)

    # Categorizar
    categories = categorize_comments(unique_comments)

    # Palabras clave
    keywords = extract_keywords(unique_comments, top_n=30)

    # Generar reporte
    report = []
    report.append("="*70)
    report.append("REPORTE DE ANÁLISIS DE COMENTARIOS DE TIKTOK")
    report.append("="*70)
    report.append(f"\nFecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"\n📊 ESTADÍSTICAS GENERALES")
    report.append(f"   Total de comentarios extraídos: {len(comments)}")
    report.append(f"   Comentarios únicos: {len(unique_comments)}")
    report.append(f"   Duplicados eliminados: {duplicates_removed}")

    report.append(f"\n📈 DISTRIBUCIÓN POR CATEGORÍA")
    report.append(f"   Preguntas: {len(categories['preguntas'])} ({len(categories['preguntas'])/len(unique_comments)*100:.1f}%)")
    report.append(f"   Positivos: {len(categories['positivos'])} ({len(categories['positivos'])/len(unique_comments)*100:.1f}%)")
    report.append(f"   Negativos: {len(categories['negativos'])} ({len(categories['negativos'])/len(unique_comments)*100:.1f}%)")
    report.append(f"   Neutrales: {len(categories['neutrales'])} ({len(categories['neutrales'])/len(unique_comments)*100:.1f}%)")

    report.append(f"\n📏 DISTRIBUCIÓN POR LONGITUD")
    report.append(f"   Muy cortos (<10 chars): {len(categories['muy_cortos'])}")
    report.append(f"   Largos (>100 chars): {len(categories['largos'])}")

    avg_length = sum(len(c['text']) for c in unique_comments) / len(unique_comments)
    report.append(f"   Longitud promedio: {avg_length:.0f} caracteres")

    report.append(f"\n🔤 TOP 30 PALABRAS CLAVE")
    for i, (word, count) in enumerate(keywords, 1):
        report.append(f"   {i:2d}. {word:20s} : {count:3d}")

    report.append(f"\n❓ TOP 10 PREGUNTAS MÁS COMUNES")
    for i, comment in enumerate(categories['preguntas'][:10], 1):
        report.append(f"   {i}. {comment['text'][:70]}...")

    report.append(f"\n😊 TOP 10 COMENTARIOS POSITIVOS")
    for i, comment in enumerate(categories['positivos'][:10], 1):
        report.append(f"   {i}. {comment['text'][:70]}...")

    report.append(f"\n😠 TOP 10 COMENTARIOS NEGATIVOS")
    for i, comment in enumerate(categories['negativos'][:10], 1):
        report.append(f"   {i}. {comment['text'][:70]}...")

    report.append(f"\n📝 COMENTARIOS MÁS LARGOS")
    longest = sorted(unique_comments, key=lambda x: len(x['text']), reverse=True)[:5]
    for i, comment in enumerate(longest, 1):
        report.append(f"   {i}. ({len(comment['text'])} chars) {comment['text'][:60]}...")

    report.append("\n" + "="*70)

    # Guardar reporte
    report_text = '\n'.join(report)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report_text)

    # Guardar comentarios limpios
    clean_file = 'comentarios_limpios.json'
    with open(clean_file, 'w', encoding='utf-8') as f:
        json.dump(unique_comments, f, ensure_ascii=False, indent=2)

    # Guardar por categorías
    categories_file = 'comentarios_por_categoria.json'
    # Convertir a formato serializable
    serializable_categories = {k: v for k, v in categories.items()}
    with open(categories_file, 'w', encoding='utf-8') as f:
        json.dump(serializable_categories, f, ensure_ascii=False, indent=2)

    return report_text, unique_comments, categories


if __name__ == "__main__":
    import sys

    # Obtener nombre del archivo
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        # Buscar el archivo más reciente
        import glob
        files = glob.glob('comentarios_*.json')
        if not files:
            print("❌ No se encontraron archivos de comentarios")
            sys.exit(1)
        filename = max(files, key=lambda x: x)

    print(f"📂 Analizando: {filename}")
    print()

    # Cargar comentarios
    comments = load_comments(filename)

    # Generar reporte
    report_text, unique_comments, categories = generate_report(comments)

    # Mostrar reporte
    print(report_text)

    print(f"\n💾 Archivos generados:")
    print(f"   ✓ reporte_analisis.txt - Reporte completo")
    print(f"   ✓ comentarios_limpios.json - {len(unique_comments)} comentarios únicos")
    print(f"   ✓ comentarios_por_categoria.json - Comentarios categorizados")
