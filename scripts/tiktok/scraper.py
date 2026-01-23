"""
Extractor de comentarios de TikTok usando Playwright
Extiende BaseScraper para estructura unificada.

Uso:
python -m scripts.tiktok.scraper "https://www.tiktok.com/@usuario/video/ID"
python -m scripts.tiktok.scraper --login  # Para guardar cookies
"""

import asyncio
import json
import re
import sys
import time
from pathlib import Path
from typing import List, Optional

from playwright.async_api import async_playwright, Page, BrowserContext

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.common.base_scraper import BaseScraper
from scripts.common.models import ScrapeResult, Post, PostAuthor, Comment, Attachment

# Configuración de rutas
SCRIPT_DIR = Path(__file__).resolve().parent
COOKIES_FILE = SCRIPT_DIR / "tiktok-cookies.json"


class TikTokScraper(BaseScraper):
    """Scraper for TikTok videos and comments using Playwright."""

    def __init__(self, output_dir: Optional[Path] = None):
        super().__init__(output_dir)
        self.page: Optional[Page] = None
        self.context: Optional[BrowserContext] = None

    @property
    def platform_name(self) -> str:
        return "tiktok"

    async def _load_cookies(self, context: BrowserContext) -> bool:
        """Load saved cookies if they exist."""
        try:
            if COOKIES_FILE.exists():
                cookies = json.loads(COOKIES_FILE.read_text())
                # Ensure all cookie values are strings
                for cookie in cookies:
                    if 'value' in cookie and not isinstance(cookie['value'], str):
                        cookie['value'] = str(cookie['value'])
                await context.add_cookies(cookies)
                print("✅ Cookies cargadas")
                return True
        except Exception as e:
            print(f"⚠️ No se pudieron cargar cookies: {e}")
        return False

    async def _save_cookies(self, context: BrowserContext):
        """Save session cookies."""
        try:
            cookies = await context.cookies()
            COOKIES_FILE.write_text(json.dumps(cookies, indent=2))
            print("✅ Cookies guardadas")
        except Exception as e:
            print(f"⚠️ Error guardando cookies: {e}")

    async def login_and_save_cookies(self):
        """Open browser for manual TikTok login and save cookies."""
        print("\n" + "=" * 60)
        print("🔐 LOGIN DE TIKTOK")
        print("=" * 60)
        print("1. Se abrirá un navegador con TikTok")
        print("2. Inicia sesión en tu cuenta")
        print("3. El script detectará automáticamente cuando estés logueado")
        print("=" * 60 + "\n")

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                channel="chrome",
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = await browser.new_context(
                viewport={"width": 1440, "height": 900},
                locale="es-PE",
            )
            page = await context.new_page()
            await page.goto("https://www.tiktok.com/login")

            print("⏳ Esperando login... (máximo 5 minutos)")
            max_wait = 300
            start = time.time()

            while time.time() - start < max_wait:
                try:
                    logged_in = await page.evaluate('''() => {
                        const hasAvatar = document.querySelector('[data-e2e="profile-icon"]') ||
                                         document.querySelector('a[href*="/profile"]') ||
                                         document.querySelector('[class*="DivAvatarContainer"]');
                        const noLoginButton = !document.querySelector('[data-e2e="top-login-button"]');
                        return hasAvatar || (noLoginButton && window.location.pathname !== '/login');
                    }''')

                    if logged_in:
                        print("✅ Login detectado!")
                        break
                except Exception:
                    pass

                await page.wait_for_timeout(2000)

            await self._save_cookies(context)
            print(f"   Guardadas {len(await context.cookies())} cookies")
            await browser.close()

        print("\n✅ Cookies guardadas. Ahora puedes ejecutar el scraper.")

    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from TikTok URL."""
        if "/video/" in url:
            return url.split("/video/")[1].split("?")[0]
        return None

    async def scrape(
        self,
        url: str,
        max_comments: Optional[int] = None,
        headless: bool = False,
        include_replies: bool = True
    ) -> ScrapeResult:
        """
        Scrape a TikTok video and its comments using Playwright.
        """
        start_time = time.time()
        result = self.create_result(url)

        video_id = self._extract_video_id(url)
        if not video_id:
            result.error = "URL inválida. Debe contener '/video/ID'"
            return result

        print(f"📱 Extrayendo comentarios del video ID: {video_id}")

        async with async_playwright() as p:
            # Launch browser with Chrome
            browser = await p.chromium.launch(
                headless=headless,
                channel="chrome",
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                ]
            )

            context = await browser.new_context(
                viewport={"width": 1440, "height": 900},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                locale="es-PE",
            )

            # Load cookies
            await self._load_cookies(context)

            page = await context.new_page()
            self.page = page
            self.context = context

            try:
                print(f"🔗 Navegando a: {url}")
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(3000)

                # Close any popups
                await self._close_popups(page)

                # Wait for video to load
                await self._wait_for_video(page)

                # Extract post data
                result.post = await self._extract_post_data(page=page, video_id=video_id, url=url)

                # Expand and extract comments
                result.comments = await self._extract_comments(
                    page=page,
                    max_comments=max_comments,
                    include_replies=include_replies
                )

                # Save cookies
                await self._save_cookies(context)

            except Exception as e:
                result.error = str(e)
                print(f"❌ Error al extraer: {e}")
                import traceback
                traceback.print_exc()

            await browser.close()

        result.scrape_duration_seconds = time.time() - start_time
        return result

    async def _close_popups(self, page: Page):
        """Close any TikTok popups."""
        print("🔄 Cerrando popups...")
        try:
            # Close cookie consent
            close_btns = await page.query_selector_all('button:has-text("Decline"), button:has-text("Rechazar")')
            for btn in close_btns:
                try:
                    if await btn.is_visible():
                        await btn.click()
                        await page.wait_for_timeout(500)
                except Exception:
                    pass

            # Close login popup if appears
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(500)
        except Exception:
            pass

    async def _wait_for_video(self, page: Page):
        """Wait for video content to load."""
        print("⏳ Esperando que cargue el video...")
        try:
            await page.wait_for_selector('[data-e2e="browse-video"], video', timeout=15000)
            await page.wait_for_timeout(2000)
            print("   ✅ Video cargado")
        except Exception:
            print("   ⚠️ Timeout esperando video")

    async def _extract_post_data(self, page: Page = None, video_id: str = "", url: str = "", **kwargs) -> Post:
        """Extract video metadata using Playwright."""
        print("📊 Extrayendo datos del video...")
        post = Post(post_id=video_id)

        try:
            # Description
            desc_el = await page.query_selector('[data-e2e="browse-video-desc"], [data-e2e="video-desc"]')
            if desc_el:
                post.text = await desc_el.inner_text()

            # Author
            author_el = await page.query_selector('[data-e2e="browse-username"], [data-e2e="video-author-uniqueid"]')
            if author_el:
                username = await author_el.inner_text()
                post.author = PostAuthor(
                    username=username.replace("@", ""),
                    name=username
                )

            # Stats
            try:
                likes_el = await page.query_selector('[data-e2e="browse-like-count"], [data-e2e="like-count"]')
                if likes_el:
                    likes_text = await likes_el.inner_text()
                    post.likes = self._parse_count(likes_text)

                comments_el = await page.query_selector('[data-e2e="browse-comment-count"], [data-e2e="comment-count"]')
                if comments_el:
                    comments_text = await comments_el.inner_text()
                    post.comments_total = self._parse_count(comments_text)

                shares_el = await page.query_selector('[data-e2e="share-count"]')
                if shares_el:
                    shares_text = await shares_el.inner_text()
                    post.shares = self._parse_count(shares_text)
            except Exception:
                pass

            print(f"   Descripción: {post.text[:50]}..." if post.text and len(post.text) > 50 else f"   Descripción: {post.text}")
            print(f"   Likes: {post.likes:,}")
            print(f"   Comentarios: {post.comments_total:,}")

        except Exception as e:
            print(f"⚠️ Error extrayendo datos: {e}")

        return post

    def _parse_count(self, text: str) -> int:
        """Parse count string like '1.2K' or '1.5M' to integer."""
        if not text:
            return 0
        text = text.strip().upper()
        try:
            if 'K' in text:
                return int(float(text.replace('K', '')) * 1000)
            elif 'M' in text:
                return int(float(text.replace('M', '')) * 1000000)
            else:
                return int(text.replace(',', '').replace('.', ''))
        except Exception:
            return 0

    async def _expand_comments(self, page: Page, max_iterations: int = 100):
        """Expand comments by scrolling the comment section."""
        print("📜 Expandiendo comentarios...")

        # First, find the comment section
        await page.wait_for_timeout(2000)

        last_count = 0
        no_change_count = 0

        for iteration in range(max_iterations):
            # Scroll the page to load more comments
            try:
                await page.evaluate('''() => {
                    // Try multiple selectors for comment section
                    const selectors = [
                        '[data-e2e="comment-list"]',
                        '[class*="DivCommentListContainer"]',
                        '[class*="comment-list"]',
                        'div[class*="CommentList"]'
                    ];

                    for (const sel of selectors) {
                        const el = document.querySelector(sel);
                        if (el) {
                            el.scrollTop = el.scrollHeight;
                            return;
                        }
                    }

                    // Fallback: scroll the page
                    window.scrollBy(0, 800);
                }''')
            except Exception:
                pass

            await page.wait_for_timeout(800)

            # Count comments using multiple selectors
            try:
                current = await page.evaluate('''() => {
                    const selectors = [
                        '[data-e2e="comment-item"]',
                        '[class*="DivCommentItemContainer"]',
                        '[class*="CommentItem"]',
                        'div[class*="comment-item"]'
                    ];

                    for (const sel of selectors) {
                        const items = document.querySelectorAll(sel);
                        if (items.length > 0) return items.length;
                    }

                    // Try to find by structure
                    const usernames = document.querySelectorAll('a[href*="/@"][class*="Link"]');
                    return usernames.length;
                }''')
            except Exception:
                current = last_count

            if iteration % 10 == 0:
                print(f"   🔄 Iteración {iteration}: {current} comentarios")

            if current == last_count:
                no_change_count += 1
            else:
                no_change_count = 0

            last_count = current

            if no_change_count >= 5 and iteration > 5:
                break

        print(f"✅ Expansión completada: {last_count} comentarios visibles")
        return last_count

    async def _extract_comments(
        self,
        page: Page = None,
        max_comments: Optional[int] = None,
        include_replies: bool = True,
        **kwargs
    ) -> List[Comment]:
        """Extract comments using Playwright."""
        comments = []

        print("\n💬 Extrayendo comentarios...")

        # First expand comments
        await self._expand_comments(page)

        # Extract comments using JavaScript for better DOM access
        try:
            raw_comments = await page.evaluate('''() => {
                const comments = [];

                // Find all links to user profiles that are likely comment authors
                const userLinks = document.querySelectorAll('a[href*="/@"]');

                userLinks.forEach((link, idx) => {
                    try {
                        const username = link.textContent.trim().replace('@', '');
                        if (!username || username.length < 2) return;

                        // Find the parent comment container (go up until we find a reasonable container)
                        let container = link.parentElement;
                        for (let i = 0; i < 5 && container; i++) {
                            // Check if this looks like a comment container
                            if (container.className && (
                                container.className.includes('Comment') ||
                                container.className.includes('comment') ||
                                container.getAttribute('data-e2e')?.includes('comment')
                            )) {
                                break;
                            }
                            container = container.parentElement;
                        }

                        if (!container) return;

                        // Find comment text - all text in container except username and UI elements
                        const allText = container.textContent || '';
                        let text = allText
                            .replace(username, '')
                            .replace(/@\\w+/g, '')
                            .replace(/\\d+[KkMm]?\\s*(likes?|Reply|respuesta|Responder|Ver)/gi, '')
                            .replace(/hace \\d+.*/gi, '')
                            .replace(/\\d+[hmd]\\s*/gi, '')
                            .trim();

                        // Clean up the text
                        text = text.split('\\n')[0].trim();  // Take first line

                        if (!text || text.length < 2) return;

                        // Find likes
                        let likes = 0;
                        const likesMatch = allText.match(/(\\d+[KkMm]?)\\s*(likes?|me gusta)/i);
                        if (likesMatch) {
                            const likesText = likesMatch[1];
                            if (likesText.toUpperCase().includes('K')) {
                                likes = Math.floor(parseFloat(likesText) * 1000);
                            } else if (likesText.toUpperCase().includes('M')) {
                                likes = Math.floor(parseFloat(likesText) * 1000000);
                            } else {
                                likes = parseInt(likesText) || 0;
                            }
                        }

                        // Avoid duplicates
                        const existing = comments.find(c => c.username === username && c.text === text);
                        if (existing) return;

                        comments.push({
                            username: username,
                            text: text.substring(0, 1000),
                            likes: likes,
                            isReply: false
                        });
                    } catch (e) {
                        // Skip errored
                    }
                });

                return comments;
            }''')

            print(f"   🔍 Procesando {len(raw_comments)} comentarios encontrados...")

            for idx, raw in enumerate(raw_comments):
                if max_comments and idx >= max_comments:
                    break

                try:
                    user = self.create_user(
                        user_id=raw['username'],
                        username=raw['username'],
                        display_name=raw['username']
                    )

                    comment_obj = self.create_comment(
                        index=idx + 1,
                        comment_id=str(idx + 1),
                        text=raw['text'],
                        user=user,
                        likes=raw['likes'],
                        is_reply=raw['isReply'],
                        created_at=int(time.time())
                    )

                    comments.append(comment_obj)

                    if (idx + 1) % 50 == 0:
                        print(f"   📊 Extraídos: {idx + 1}")

                except Exception:
                    continue

        except Exception as e:
            print(f"❌ Error extrayendo comentarios: {e}")
            import traceback
            traceback.print_exc()

        print(f"\n✅ Total extraídos: {len(comments)} comentarios")

        # Detect duplicates (info only)
        text_counts = {}
        for c in comments:
            text_counts[c.text] = text_counts.get(c.text, 0) + 1
        duplicates = {k: v for k, v in text_counts.items() if v > 1}
        if duplicates:
            print(f"   🔍 Detectados {len(duplicates)} textos duplicados (posibles bots)")

        return comments


async def main():
    """Entry point."""
    scraper = TikTokScraper()

    # Check for login command
    if len(sys.argv) > 1 and sys.argv[1] == "--login":
        await scraper.login_and_save_cookies()
        return

    if len(sys.argv) > 1:
        video_url = sys.argv[1]
    else:
        video_url = "https://www.tiktok.com/@soyhouston256/video/7532014709122272517"

    print("=" * 60)
    print("🚀 TIKTOK SCRAPER (Playwright)")
    print("=" * 60)
    print(f"Video: {video_url}\n")

    result = await scraper.scrape(
        video_url,
        headless=False,
        include_replies=True
    )

    if result.comments or result.post.post_id:
        scraper.save_result(result)
        scraper.print_summary(result)

        if result.comments:
            print("\n💬 MUESTRA DE COMENTARIOS:")
            print("-" * 40)
            for comment in result.comments[:10]:
                reply_marker = "↳ " if comment.is_reply else ""
                print(f"{reply_marker}@{comment.user.username} ({comment.likes} likes)")
                text_preview = comment.text[:80] + "..." if len(comment.text) > 80 else comment.text
                print(f"   {text_preview}")
                print()
    else:
        print("\n❌ No se pudieron extraer comentarios")
        if result.error:
            print(f"   Error: {result.error}")


if __name__ == "__main__":
    asyncio.run(main())
