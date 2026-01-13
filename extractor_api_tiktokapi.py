"""
Extractor de comentarios de TikTok usando TikTokApi
Esta librería puede obtener TODOS los comentarios de un video

Instalación:
pip install TikTokApi
playwright install chromium

Uso:
python extractor_api_tiktokapi.py "https://www.tiktok.com/@usuario/video/ID"
"""

from TikTokApi import TikTokApi
import asyncio
import json
from datetime import datetime


async def get_all_comments_api(video_url, max_comments=None):
    """
    Extrae comentarios usando la API no oficial de TikTok

    Args:
        video_url: URL del video
        max_comments: Máximo de comentarios a extraer (None = todos)

    Returns:
        Lista de comentarios con metadata
    """
    # Extraer video ID de la URL
    video_id = video_url.split("/video/")[1].split("?")[0] if "/video/" in video_url else None

    if not video_id:
        print("❌ URL inválida. Debe contener '/video/ID'")
        return []

    print(f"📱 Extrayendo comentarios del video ID: {video_id}")

    async with TikTokApi() as api:
        try:
            # Crear objeto de video
            await api.create_sessions(
                num_sessions=1,
                sleep_after=3,
                headless=False
            )

            video = api.video(id=video_id)

            # Obtener información del video
            try:
                video_info = await video.info()
                print(f"\n📊 Información del video:")
                if hasattr(video_info, 'desc'):
                    print(f"   Descripción: {video_info.desc[:50]}...")
                if hasattr(video_info, 'stats'):
                    print(f"   Likes: {getattr(video_info.stats, 'diggCount', 'N/A')}")
                    print(f"   Comentarios: {getattr(video_info.stats, 'commentCount', 'N/A')}")
                    print(f"   Shares: {getattr(video_info.stats, 'shareCount', 'N/A')}")
            except Exception as e:
                print(f"⚠ No se pudo obtener info del video: {e}")

            print(f"\n💬 Extrayendo comentarios...")

            comments = []
            count = 0

            # Iterar sobre todos los comentarios
            async for comment in video.comments(count=max_comments if max_comments else 100000):
                count += 1

                try:
                    # Extraer datos usando atributos del objeto Comment
                    comment_data = {
                        'id': count,
                        'comment_id': getattr(comment, 'cid', ''),
                        'text': getattr(comment, 'text', ''),
                        'likes': getattr(comment, 'digg_count', 0),
                        'reply_count': getattr(comment, 'reply_comment_total', 0),
                        'create_time': getattr(comment, 'create_time', 0),
                        'user': {
                            'username': getattr(comment.user, 'unique_id', '') if hasattr(comment, 'user') else '',
                            'nickname': getattr(comment.user, 'nickname', '') if hasattr(comment, 'user') else '',
                            'verified': getattr(comment.user, 'verified', False) if hasattr(comment, 'user') else False
                        },
                        'timestamp': datetime.now().isoformat(),
                        'video_url': video_url
                    }

                    comments.append(comment_data)

                    # Mostrar progreso
                    if count % 50 == 0:
                        print(f"   Comentarios extraídos: {count}")

                except Exception as e:
                    print(f"   ⚠ Error procesando comentario {count}: {e}")
                    continue

                # Límite opcional
                if max_comments and count >= max_comments:
                    break

            print(f"\n✅ Total de comentarios extraídos: {len(comments)}")
            return comments

        except Exception as e:
            print(f"❌ Error al extraer comentarios: {e}")
            import traceback
            traceback.print_exc()
            return []


async def save_comments(comments, filename=None):
    """Guarda comentarios en archivo JSON"""
    if not comments:
        print("No hay comentarios para guardar")
        return

    if not filename:
        filename = f"comentarios_api_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(comments, f, ensure_ascii=False, indent=2)

    print(f"💾 Comentarios guardados en: {filename}")


async def analyze_comments(comments):
    """Análisis de los comentarios"""
    if not comments:
        return

    print("\n" + "="*60)
    print("📊 ANÁLISIS DE COMENTARIOS")
    print("="*60)

    total = len(comments)
    total_likes = sum(c['likes'] for c in comments)
    avg_likes = total_likes / total if total > 0 else 0

    # Top comentarios por likes
    top_liked = sorted(comments, key=lambda x: x['likes'], reverse=True)[:5]

    print(f"\n📈 Estadísticas:")
    print(f"   Total de comentarios: {total}")
    print(f"   Total de likes en comentarios: {total_likes}")
    print(f"   Promedio de likes por comentario: {avg_likes:.1f}")

    # Comentarios con más likes
    print(f"\n🔥 Top 5 comentarios con más likes:")
    for i, comment in enumerate(top_liked, 1):
        print(f"\n   {i}. ({comment['likes']} likes) @{comment['user']['username']}")
        print(f"      {comment['text'][:100]}...")

    # Usuarios verificados
    verified = [c for c in comments if c['user']['verified']]
    print(f"\n✓ Comentarios de usuarios verificados: {len(verified)}")

    # Comentarios con respuestas
    with_replies = [c for c in comments if c['reply_count'] > 0]
    print(f"💬 Comentarios con respuestas: {len(with_replies)}")


async def main():
    import sys

    # Obtener URL del video
    if len(sys.argv) > 1:
        video_url = sys.argv[1]
    else:
        video_url = "https://www.tiktok.com/@adri.zip/video/7429707963905887520"

    print("="*60)
    print("🚀 EXTRACTOR DE COMENTARIOS - TikTokApi")
    print("="*60)
    print(f"Video: {video_url}\n")

    # Extraer comentarios
    comments = await get_all_comments_api(video_url)

    if comments:
        # Guardar en archivo
        await save_comments(comments)

        # Análisis
        await analyze_comments(comments)

        # Mostrar algunos comentarios
        print("\n" + "="*60)
        print("💬 MUESTRA DE COMENTARIOS")
        print("="*60)
        for comment in comments[:10]:
            print(f"\n{comment['id']}. @{comment['user']['username']} ({comment['likes']} likes)")
            print(f"   {comment['text']}")
    else:
        print("\n❌ No se pudieron extraer comentarios")


if __name__ == "__main__":
    asyncio.run(main())
