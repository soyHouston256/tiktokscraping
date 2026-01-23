"""
Facebook Post Scraper usando Playwright
Extiende BaseScraper para estructura unificada.

Uso:
python -m scripts.facebook.scraper "https://www.facebook.com/..."
"""

import asyncio
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from playwright.async_api import async_playwright, Page, BrowserContext

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.common.base_scraper import BaseScraper
from scripts.common.models import ScrapeResult, Post, PostAuthor, Comment, Attachment

# Configuración de rutas
SCRIPT_DIR = Path(__file__).resolve().parent
COOKIES_FILE = SCRIPT_DIR / "fb-cookies.json"


class FacebookScraper(BaseScraper):
    """Scraper for Facebook posts and comments."""

    def __init__(self, output_dir: Optional[Path] = None):
        super().__init__(output_dir)
        self.page: Optional[Page] = None
        self.context: Optional[BrowserContext] = None
        self._modal = None  # Reference to modal if post opens in overlay

    @property
    def platform_name(self) -> str:
        return "facebook"

    # =========================================================================
    # Cookie Management
    # =========================================================================

    async def _load_cookies(self, context: BrowserContext) -> bool:
        """Load saved cookies if they exist."""
        try:
            if COOKIES_FILE.exists():
                cookies = json.loads(COOKIES_FILE.read_text())
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

    async def _is_logged_in(self, page: Page) -> bool:
        """Check if user is logged in."""
        try:
            await page.wait_for_timeout(2000)

            login_form = await page.query_selector('form[action*="login"]')
            if login_form:
                return False

            logged_indicators = [
                '[aria-label="Tu perfil"]',
                '[aria-label="Your profile"]',
                '[aria-label="Cuenta"]',
                '[aria-label="Account"]',
                'div[role="navigation"] a[href*="/me/"]',
            ]

            for selector in logged_indicators:
                el = await page.query_selector(selector)
                if el:
                    return True

            if 'login' in page.url.lower():
                return False

            return True
        except Exception:
            return False

    async def _wait_for_login(self, page: Page, context: BrowserContext) -> bool:
        """Wait for user to log in manually."""
        print("\n" + "=" * 60)
        print("🔐 NECESITAS HACER LOGIN EN FACEBOOK")
        print("=" * 60)
        print("1. Inicia sesión en la ventana del navegador")
        print("2. Una vez logueado, las cookies se guardarán automáticamente")
        print("=" * 60 + "\n")

        await page.goto("https://www.facebook.com/login")

        max_wait = 300
        start = time.time()

        while time.time() - start < max_wait:
            if await self._is_logged_in(page):
                print("✅ Login detectado!")
                await self._save_cookies(context)
                return True
            await page.wait_for_timeout(2000)

        print("❌ Timeout esperando login")
        return False

    # =========================================================================
    # Comment Expansion
    # =========================================================================

    async def _select_all_comments_filter(self, page: Page) -> bool:
        """Change comment filter to 'All comments'."""
        print("🔧 Cambiando filtro a 'Todos los comentarios'...")

        try:
            filter_selectors = [
                'span:has-text("Más relevantes")',
                'span:has-text("Most relevant")',
                'div[aria-haspopup="menu"]:has-text("relevantes")',
                'div[aria-haspopup="menu"]:has-text("relevant")',
            ]

            dropdown_clicked = False

            for selector in filter_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for el in elements:
                        if await el.is_visible():
                            await el.click()
                            await page.wait_for_timeout(1000)
                            dropdown_clicked = True
                            break
                    if dropdown_clicked:
                        break
                except Exception:
                    continue

            if dropdown_clicked:
                all_comments_selectors = [
                    'span:has-text("Todos los comentarios")',
                    'span:has-text("All comments")',
                    'div[role="menuitem"]:has-text("Todos")',
                    'div[role="menuitem"]:has-text("All comments")',
                ]

                for selector in all_comments_selectors:
                    try:
                        options = await page.query_selector_all(selector)
                        for opt in options:
                            if await opt.is_visible():
                                text = await opt.inner_text()
                                if 'todos' in text.lower() or 'all' in text.lower():
                                    await opt.click()
                                    await page.wait_for_timeout(2000)
                                    print(f"   ✅ Seleccionado: '{text}'")
                                    return True
                    except Exception:
                        continue

            print("   ⚠️ No se pudo cambiar el filtro de comentarios")
            return False

        except Exception as e:
            print(f"   ⚠️ Error cambiando filtro: {e}")
            return False

    async def _get_comment_count_from_page(self, page: Page) -> int:
        """Try to get total comment count from page."""
        try:
            page_text = await page.inner_text('body')

            patterns = [
                r'(\d+[\d,.]*)\s*[Kk]?\s*comentarios',
                r'(\d+[\d,.]*)\s*[Kk]?\s*comments',
            ]

            for pattern in patterns:
                matches = re.findall(pattern, page_text)
                for match in matches:
                    num_str = match.replace(',', '').replace('.', '')
                    try:
                        num = int(num_str)
                        if num > 10:
                            return num
                    except ValueError:
                        continue

        except Exception:
            pass

        return 0

    async def _is_page_open(self, page: Page) -> bool:
        """Check if page is still open and usable."""
        try:
            # Try to evaluate something on the page
            result = await page.evaluate('document.readyState')
            if result in ['complete', 'interactive']:
                # Also check we're not on a blocked/error page
                url = page.url
                if 'checkpoint' in url or 'login' in url:
                    print("   ⚠️ Detectada página de checkpoint/login")
                    return False
                return True
            return False
        except Exception as e:
            print(f"   ⚠️ Página no responde: {str(e)[:50]}")
            return False

    async def _safe_scroll(self, page: Page, x: int, y: int) -> bool:
        """Safely scroll the page or modal, return False if page closed."""
        try:
            # Check if we have a modal open
            if hasattr(self, '_modal') and self._modal:
                await page.evaluate(f'''() => {{
                    const modal = document.querySelector('div[role="dialog"]');
                    if (modal) {{
                        // Find scrollable container within modal
                        const scrollable = modal.querySelector('[style*="overflow"]') ||
                                          modal.querySelector('div[class*="scroll"]') ||
                                          modal;
                        if (scrollable.scrollBy) {{
                            scrollable.scrollBy({x}, {y});
                        }} else {{
                            scrollable.scrollTop += {y};
                        }}
                    }} else {{
                        window.scrollBy({x}, {y});
                    }}
                }}''')
            else:
                await page.evaluate(f'window.scrollBy({x}, {y})')
            return True
        except Exception:
            return False

    async def _close_all_popups(self, page: Page):
        """Close secondary popups but NOT the main post modal."""
        print("🔄 Cerrando popups secundarios...")

        # Check if we have a main post modal open - don't close it!
        has_post_modal = hasattr(self, '_modal') and self._modal

        for _ in range(2):
            closed_any = False

            # 1. Close cookie/consent popups (not the main modal)
            consent_selectors = [
                'div[aria-label*="cookie"]',
                'div[aria-label*="Cookie"]',
                'button[data-cookiebanner]',
                '[data-testid="cookie-policy-manage-dialog"]',
            ]

            for selector in consent_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for el in elements:
                        try:
                            if await el.is_visible():
                                close_btn = await el.query_selector('[aria-label*="lose"], [aria-label*="errar"]')
                                if close_btn:
                                    await close_btn.click()
                                    closed_any = True
                                    await page.wait_for_timeout(500)
                                    print("   ✅ Cerrado popup de cookies")
                        except Exception:
                            continue
                except Exception:
                    continue

            # 2. Close login nag popups (but preserve main dialog)
            try:
                # Find dialogs that are NOT the main post modal
                dialogs = await page.query_selector_all('div[role="dialog"]')
                for dialog in dialogs:
                    try:
                        aria_label = await dialog.get_attribute('aria-label') or ""
                        # Skip if it's a post modal
                        if 'publicación' in aria_label.lower() or 'post' in aria_label.lower():
                            continue
                        # Skip if it contains comments/articles
                        articles = await dialog.query_selector_all('div[role="article"]')
                        if len(articles) > 0:
                            continue

                        # This is probably a secondary popup - close it
                        close_btn = await dialog.query_selector('[aria-label="Cerrar"], [aria-label="Close"]')
                        if close_btn and await close_btn.is_visible():
                            await close_btn.click()
                            closed_any = True
                            await page.wait_for_timeout(500)
                            print("   ✅ Cerrado popup secundario")
                    except Exception:
                        continue
            except Exception:
                pass

            if not closed_any:
                break

            await page.wait_for_timeout(300)

    async def _wait_for_post_modal(self, page: Page) -> bool:
        """Wait for post modal to appear (Facebook opens posts in overlay)."""
        print("🔍 Buscando modal de publicación...")

        try:
            # Facebook post modals have role="dialog"
            modal_selectors = [
                'div[role="dialog"][aria-label*="publicación"]',
                'div[role="dialog"][aria-label*="post"]',
                'div[role="dialog"][aria-label*="Publicación"]',
                'div[role="dialog"]',
            ]

            for selector in modal_selectors:
                try:
                    modal = await page.wait_for_selector(selector, timeout=5000)
                    if modal:
                        print("   ✅ Modal detectado")
                        # Store reference to work within modal
                        self._modal = modal
                        return True
                except Exception:
                    continue

            # No modal found - might be a direct post page
            print("   ℹ️ No hay modal, usando página directa")
            self._modal = None
            return False

        except Exception as e:
            print(f"   ⚠️ Error buscando modal: {e}")
            self._modal = None
            return False

    async def _wait_for_comments_section(self, page: Page):
        """Wait for comments section to be fully loaded and visible."""
        print("⏳ Esperando sección de comentarios...")

        try:
            # Determine context (modal or full page)
            context = self._modal if hasattr(self, '_modal') and self._modal else page

            # Wait for article elements (comments) to appear
            for _ in range(10):
                try:
                    articles = await context.query_selector_all('div[role="article"]')
                    if len(articles) >= 1:
                        print(f"   ✅ Encontrados {len(articles)} elementos")
                        break
                except Exception:
                    # If modal closed, fall back to page
                    articles = await page.query_selector_all('div[role="article"]')
                    if len(articles) >= 1:
                        print(f"   ✅ Encontrados {len(articles)} elementos (página)")
                        break
                await page.wait_for_timeout(1000)

            # If in modal, scroll within the modal
            if hasattr(self, '_modal') and self._modal:
                try:
                    # Scroll within modal to load more comments
                    await page.evaluate('''() => {
                        const modal = document.querySelector('div[role="dialog"]');
                        if (modal) {
                            const scrollable = modal.querySelector('[style*="overflow"]') || modal;
                            scrollable.scrollTop = scrollable.scrollHeight;
                        }
                    }''')
                    await page.wait_for_timeout(1500)
                except Exception:
                    pass
            else:
                # Scroll to comments section on page
                try:
                    comment_section = await page.query_selector('ul[role="list"], div[aria-label*="comentario"], div[aria-label*="comment"]')
                    if comment_section:
                        await comment_section.scroll_into_view_if_needed()
                        await page.wait_for_timeout(1000)
                except Exception:
                    pass

            # Wait a bit more for lazy-loaded content
            await page.wait_for_timeout(2000)

        except Exception as e:
            print(f"   ⚠️ Error esperando comentarios: {e}")

    async def _find_modal_scrollable(self, page: Page):
        """Find the scrollable container inside the modal."""
        try:
            # Facebook modals have a specific scrollable div
            scrollable = await page.evaluate('''() => {
                const modal = document.querySelector('div[role="dialog"]');
                if (!modal) return null;

                // Find the scrollable container - usually has overflow-y: auto/scroll
                const candidates = modal.querySelectorAll('div');
                for (const div of candidates) {
                    const style = window.getComputedStyle(div);
                    const overflowY = style.overflowY;
                    const height = div.scrollHeight;

                    if ((overflowY === 'auto' || overflowY === 'scroll') && height > 500) {
                        // Return a selector we can use
                        return true;
                    }
                }
                return false;
            }''')
            return scrollable
        except Exception:
            return False

    async def _scroll_modal(self, page: Page, direction: int = 1) -> bool:
        """Scroll inside the modal. direction: 1 = down, -1 = up."""
        try:
            scroll_amount = 800 * direction
            result = await page.evaluate(f'''() => {{
                const modal = document.querySelector('div[role="dialog"]');
                if (!modal) return false;

                // Find scrollable container
                const candidates = Array.from(modal.querySelectorAll('div'));
                for (const div of candidates) {{
                    const style = window.getComputedStyle(div);
                    if ((style.overflowY === 'auto' || style.overflowY === 'scroll') && div.scrollHeight > 500) {{
                        const before = div.scrollTop;
                        div.scrollBy(0, {scroll_amount});
                        return div.scrollTop !== before;
                    }}
                }}

                // Fallback: try scrolling the modal itself
                modal.scrollBy(0, {scroll_amount});
                return true;
            }}''')
            return result
        except Exception:
            return False

    async def _expand_comments(self, page: Page, max_iterations: int = 300):
        """Expand comments by scrolling and clicking expansion buttons."""
        print("📜 Expandiendo comentarios...")

        try:
            target_comments = await self._get_comment_count_from_page(page)
            if target_comments > 0:
                print(f"   📊 Comentarios detectados: {target_comments}")
        except Exception:
            target_comments = 0

        # Patterns for expand buttons (Spanish and English)
        expand_patterns = [
            "Ver más comentarios",
            "View more comments",
            "Ver comentarios anteriores",
            "View previous comments",
            "más comentarios",
            "more comments",
        ]

        last_count = 0
        no_change_count = 0
        total_clicks = 0
        is_modal = hasattr(self, '_modal') and self._modal

        for iteration in range(max_iterations):
            # Check page health every 10 iterations
            if iteration > 0 and iteration % 10 == 0:
                if not await self._is_page_open(page):
                    print("   ⚠️ Página cerrada, deteniendo expansión")
                    break

            clicks = 0

            # Scroll within modal or page
            if is_modal:
                # Alternate between scrolling down and up to trigger lazy loading
                direction = 1 if iteration % 3 != 2 else -1
                await self._scroll_modal(page, direction)
            else:
                if iteration % 2 == 0:
                    await self._safe_scroll(page, 0, 800)
                else:
                    await self._safe_scroll(page, 0, -200)

            await page.wait_for_timeout(300)

            # Find and click expand buttons
            try:
                # Get all buttons with role="button"
                all_buttons = await page.query_selector_all('div[role="dialog"] [role="button"]') if is_modal else await page.query_selector_all('[role="button"]')

                for btn in all_buttons:
                    try:
                        if not await btn.is_visible():
                            continue

                        text = (await btn.inner_text()).lower()

                        # Check if this is an expand button
                        is_expand = any(pattern.lower() in text for pattern in expand_patterns)

                        if is_expand:
                            await btn.scroll_into_view_if_needed()
                            await page.wait_for_timeout(100)
                            await btn.click()
                            clicks += 1
                            total_clicks += 1
                            await page.wait_for_timeout(500)

                            # Don't click too many in one iteration
                            if clicks >= 3:
                                break
                    except Exception:
                        continue
            except Exception:
                pass

            # Count current articles
            try:
                if is_modal:
                    try:
                        current = len(await page.query_selector_all('div[role="dialog"] div[role="article"]'))
                    except Exception:
                        current = len(await page.query_selector_all('div[role="article"]'))
                else:
                    current = len(await page.query_selector_all('div[role="article"]'))
            except Exception:
                current = last_count

            # Progress logging
            if iteration % 15 == 0:
                print(f"   🔄 Iteración {iteration}: {current} elementos, {total_clicks} clics")

            # Track changes
            if current == last_count:
                no_change_count += 1
            else:
                no_change_count = 0

            last_count = current

            # Exit conditions
            if clicks == 0 and no_change_count >= 8:
                # Try one more aggressive scroll
                if is_modal:
                    await page.evaluate('''() => {
                        const modal = document.querySelector('div[role="dialog"]');
                        if (modal) {
                            const divs = modal.querySelectorAll('div');
                            for (const div of divs) {
                                const style = window.getComputedStyle(div);
                                if (style.overflowY === 'auto' || style.overflowY === 'scroll') {
                                    div.scrollTop = div.scrollHeight;
                                    break;
                                }
                            }
                        }
                    }''')
                await page.wait_for_timeout(1500)

                # Check if new content loaded
                new_count = len(await page.query_selector_all('div[role="dialog"] div[role="article"]')) if is_modal else len(await page.query_selector_all('div[role="article"]'))

                if new_count == current and iteration > 30:
                    print(f"   ℹ️ No hay más contenido para cargar")
                    break

            # Target reached
            if target_comments > 0 and current >= target_comments * 0.85:
                print(f"   ✅ Alcanzado ~85% del objetivo ({current}/{target_comments})")
                break

            await page.wait_for_timeout(150)

        print(f"✅ Expansión completada: {total_clicks} clics, ~{last_count} elementos")

    async def _expand_all_replies(self, page: Page) -> int:
        """Expand all nested replies."""
        print("   📂 Expandiendo respuestas anidadas...")

        total_expanded = 0
        is_modal = hasattr(self, '_modal') and self._modal

        # Patterns for reply expansion buttons
        reply_patterns = [
            r'ver.*\d+.*respuesta',
            r'view.*\d+.*repl',
            r'\d+\s*respuesta',
            r'\d+\s*repl',
        ]
        reply_texts = ['más respuestas', 'more replies', 'ver respuestas', 'view replies']

        for round_num in range(30):
            if round_num > 0 and round_num % 5 == 0:
                if not await self._is_page_open(page):
                    break

            expanded = 0

            try:
                # Get buttons from modal or page
                if is_modal:
                    buttons = await page.query_selector_all('div[role="dialog"] [role="button"]')
                else:
                    buttons = await page.query_selector_all('[role="button"]')

                for btn in buttons:
                    try:
                        if not await btn.is_visible():
                            continue

                        text = (await btn.inner_text()).lower()

                        # Check patterns
                        is_reply_btn = any(re.search(p, text) for p in reply_patterns)
                        is_reply_btn = is_reply_btn or any(t in text for t in reply_texts)

                        if is_reply_btn:
                            await btn.scroll_into_view_if_needed()
                            await page.wait_for_timeout(100)
                            await btn.click()
                            expanded += 1
                            total_expanded += 1
                            await page.wait_for_timeout(400)

                            if expanded >= 5:  # Limit per round
                                break
                    except Exception:
                        continue

            except Exception:
                break

            if expanded == 0:
                break

            # Scroll to find more
            if is_modal:
                await self._scroll_modal(page, 1)
            else:
                await self._safe_scroll(page, 0, 400)
            await page.wait_for_timeout(300)

        if total_expanded > 0:
            print(f"   ✅ Expandidas {total_expanded} secciones de respuestas")

        return total_expanded

    # =========================================================================
    # Data Extraction
    # =========================================================================

    async def _extract_comment_likes(self, article) -> int:
        """Extract likes count from a comment."""
        try:
            like_selectors = [
                'span[aria-label*="reacción"]',
                'span[aria-label*="reaction"]',
                '[aria-label*="reacción"]',
            ]

            for selector in like_selectors:
                try:
                    el = await article.query_selector(selector)
                    if el:
                        aria = await el.get_attribute('aria-label') or ""
                        nums = re.findall(r'\d+', aria)
                        if nums:
                            return int(nums[0])
                except Exception:
                    continue

            spans = await article.query_selector_all('span')
            for span in spans:
                try:
                    text = (await span.inner_text()).strip()
                    if re.match(r'^\d+[KkMm]?$', text):
                        num = text.replace('K', '000').replace('k', '000')
                        num = int(re.sub(r'[^\d]', '', num))
                        if 0 < num < 1000000:
                            parent = await span.evaluate('el => el.parentElement?.innerHTML || ""')
                            if 'reaction' in parent.lower() or 'like' in parent.lower():
                                return num
                except Exception:
                    continue

        except Exception:
            pass

        return 0

    async def _extract_reactions(self, page: Page) -> dict:
        """Extract reactions from post."""
        reactions = {"total": 0, "like": 0, "love": 0, "haha": 0, "wow": 0, "sad": 0, "angry": 0}

        try:
            page_html = await page.content()

            patterns = [
                r'>(\d+)\s*mil<',
                r'>(\d+[.,]\d+)\s*[Kk]<',
                r'>(\d+)\s*[Kk]<',
            ]

            for pattern in patterns:
                match = re.search(pattern, page_html, re.IGNORECASE)
                if match:
                    num_str = match.group(1)
                    if 'mil' in pattern or 'k' in pattern.lower():
                        reactions["total"] = int(float(num_str.replace(',', '.')) * 1000)
                    else:
                        reactions["total"] = int(num_str.replace(',', '').replace('.', ''))

                    if reactions["total"] > 10:
                        break

            if reactions["total"] > 0:
                reactions["like"] = reactions["total"]

            print(f"   💜 Reacciones: {reactions['total']} total")

        except Exception as e:
            print(f"   ⚠️ Error extrayendo reacciones: {e}")

        return reactions

    async def _extract_post_id(self, url: str) -> str:
        """Extract post ID from URL."""
        patterns = [
            r'fbid=(\d+)',
            r'/posts/(\d+)',
            r'/posts/pfbid(\w+)',
            r'/photo[^/]*/(\d+)',
            r'story_fbid=(\d+)',
        ]
        return self.extract_id_from_url(url, patterns)

    async def _extract_post_text(self, page: Page) -> str:
        """Extract main post text."""
        try:
            selectors = [
                'div[data-ad-comet-preview="message"]',
                'div[data-ad-preview="message"]',
            ]

            for selector in selectors:
                el = await page.query_selector(selector)
                if el:
                    text = await el.inner_text()
                    if text and len(text.strip()) > 5:
                        return text.strip()

            blocks = await page.query_selector_all('div[dir="auto"]')
            for block in blocks[:10]:
                text = await block.inner_text()
                if text and len(text.strip()) > 50:
                    return text.strip()

        except Exception as e:
            print(f"⚠️ Error extrayendo texto del post: {e}")

        return ""

    async def _extract_author_info(self, page: Page) -> PostAuthor:
        """Extract post author information."""
        author = PostAuthor()

        try:
            author_link = await page.query_selector('h2 a[role="link"], strong a[role="link"]')
            if author_link:
                author.name = await author_link.inner_text()
                author.profile_url = await author_link.get_attribute('href') or ""

                if author.profile_url:
                    match = re.search(r'/(\d+)|/([^/?]+)', author.profile_url)
                    if match:
                        author.id = match.group(1) or match.group(2)
                        author.username = author.id

            profile_img = await page.query_selector('image[*|href], svg image')
            if profile_img:
                href = await profile_img.get_attribute('xlink:href')
                if href:
                    author.profile_picture = href

        except Exception as e:
            print(f"⚠️ Error extrayendo autor: {e}")

        return author

    async def _extract_attachments(self, page: Page) -> List[Attachment]:
        """Extract media attachments."""
        attachments = []

        try:
            images = await page.query_selector_all('img[data-visualcompletion="media-vc-image"]')
            for img in images:
                src = await img.get_attribute('src')
                alt = await img.get_attribute('alt') or ""

                if src and 'emoji' not in src.lower() and 'static' not in src.lower():
                    parent_link = await img.evaluate('el => el.closest("a")?.href')

                    img_id = ""
                    if parent_link:
                        match = re.search(r'fbid=(\d+)', str(parent_link))
                        if match:
                            img_id = match.group(1)

                    attachments.append(Attachment(
                        type="photo",
                        url=parent_link or src,
                        id=img_id,
                        caption=alt
                    ))

            videos = await page.query_selector_all('video, div[data-video-id]')
            for video in videos:
                video_id = await video.get_attribute('data-video-id') or ""
                video_url = await video.evaluate('el => el.closest("a")?.href') or ""

                attachments.append(Attachment(
                    type="video",
                    url=video_url,
                    id=video_id
                ))

        except Exception as e:
            print(f"⚠️ Error extrayendo adjuntos: {e}")

        return attachments

    # =========================================================================
    # Main Scraping Methods
    # =========================================================================

    async def scrape(
        self,
        url: str,
        headless: bool = False
    ) -> ScrapeResult:
        """
        Scrape a Facebook post and its comments.

        Args:
            url: Facebook post URL
            headless: Run browser in headless mode

        Returns:
            ScrapeResult with post data and comments
        """
        start_time = time.time()
        result = self.create_result(url)

        async with async_playwright() as p:
            # Try to connect to existing Chrome, or launch new one
            browser = None
            context = None

            # Option 1: Try CDP connection to running Chrome (port 9222)
            try:
                browser = await p.chromium.connect_over_cdp("http://localhost:9222")
                context = browser.contexts[0] if browser.contexts else await browser.new_context()
                print("✅ Conectado a Chrome existente via CDP")
            except Exception:
                pass

            # Option 2: Launch fresh Chrome with our settings
            if not browser:
                print("ℹ️ Iniciando nuevo navegador...")
                browser = await p.chromium.launch(
                    headless=headless,
                    channel="chrome",
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                    ]
                )
                context = await browser.new_context(
                    viewport={'width': 1440, 'height': 900},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                    locale='es-PE',
                )
                await self._load_cookies(context)

            page = await context.new_page()

            print(f"🔗 Navegando a: {url}")
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                await page.wait_for_timeout(3000)

                # Check if we were redirected (share URLs redirect)
                current_url = page.url
                if current_url != url:
                    print(f"   ↪️ Redirigido a: {current_url[:80]}...")

                # Wait for modal if post opens in overlay
                await self._wait_for_post_modal(page)

            except Exception as e:
                print(f"⚠️ Navegación con timeout: {e}")

            # Check if logged in, if not, wait for manual login
            if not await self._is_logged_in(page):
                if not await self._wait_for_login(page, context):
                    await context.close()
                    result.error = "Login required"
                    return result

                # Navigate back to the URL after login
                try:
                    await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                    await page.wait_for_timeout(3000)
                    await self._wait_for_post_modal(page)
                except Exception:
                    pass

            # Save cookies for next time
            await self._save_cookies(context)

            try:
                # Wait longer for page to fully render
                print("⏳ Esperando que la página cargue completamente...")
                await page.wait_for_timeout(3000)

                # Verify we're on a valid page
                if not await self._is_page_open(page):
                    print("⚠️ La página no está disponible")
                    result.error = "Page not accessible - may need fresh login"
                    await context.close()
                    return result

                # Close ALL popups and overlays
                await self._close_all_popups(page)
                await page.wait_for_timeout(1000)

                # Wait for comments section to be visible
                await self._wait_for_comments_section(page)

                print("🔍 Analizando página...")

                await self._select_all_comments_filter(page)
                await self._expand_comments(page)

                print("📊 Extrayendo datos del post...")

                # Check if page is still open before extracting
                if await self._is_page_open(page):
                    result.post = await self._extract_post_data(page=page, url=url)
                    result.comments = await self._extract_comments(page=page, post_text=result.post.text)
                else:
                    print("⚠️ Página cerrada antes de extraer datos")
                    result.error = "Page closed unexpectedly"

            except Exception as e:
                error_msg = str(e)
                if "Target" in error_msg and "closed" in error_msg:
                    print(f"⚠️ El navegador se cerró inesperadamente")
                    result.error = "Browser closed unexpectedly - Facebook may have detected automation"
                else:
                    print(f"⚠️ Error durante scraping: {e}")
                    result.error = str(e)

            try:
                await context.close()
            except Exception:
                pass

        result.scrape_duration_seconds = time.time() - start_time
        return result

    async def _extract_post_data(self, page: Page, url: str) -> Post:
        """Extract post metadata."""
        post_id = await self._extract_post_id(url)
        post = Post(post_id=post_id)

        post.text = await self._extract_post_text(page)
        post.author = await self._extract_author_info(page)
        post.attachments = await self._extract_attachments(page)

        reactions = await self._extract_reactions(page)
        post.likes = reactions["total"]
        post.extra_metrics = {k: v for k, v in reactions.items() if k != "total"}

        return post

    async def _extract_comments(
        self,
        page: Page,
        post_text: str = ""
    ) -> List[Comment]:
        """Extract comments from post."""
        comments = []
        comment_index = 0

        # Check if page is still open
        if not await self._is_page_open(page):
            print("⚠️ Página cerrada, no se pueden extraer comentarios")
            return comments

        post_text_clean = post_text.strip()[:200] if post_text else ""

        print("📝 Extrayendo comentarios...")

        try:
            # Expand "See more" in comment texts
            try:
                see_more_btns = await page.query_selector_all(
                    'div[role="button"]:has-text("Ver más"), div[role="button"]:has-text("See more")'
                )
                for btn in see_more_btns:
                    try:
                        if await btn.is_visible():
                            await btn.click()
                            await page.wait_for_timeout(150)
                    except Exception:
                        pass
            except Exception:
                pass

            if await self._is_page_open(page):
                await self._expand_all_replies(page)
                await page.wait_for_timeout(2000)

            # Get articles from modal if available, otherwise from page
            if hasattr(self, '_modal') and self._modal:
                try:
                    articles = await self._modal.query_selector_all('div[role="article"]')
                except Exception:
                    articles = await page.query_selector_all('div[role="article"]')
            else:
                articles = await page.query_selector_all('div[role="article"]')
            print(f"   🔍 Procesando {len(articles)} elementos...")

            for article in articles:
                try:
                    aria_label = await article.get_attribute('aria-label') or ""

                    if 'post' in aria_label.lower() or 'publicación' in aria_label.lower():
                        continue

                    # Check if reply
                    is_reply = False
                    try:
                        nesting = await article.evaluate('''el => {
                            let level = 0;
                            let parent = el.parentElement;
                            while (parent) {
                                if (parent.tagName === 'UL' || parent.tagName === 'LI') level++;
                                parent = parent.parentElement;
                            }
                            return level;
                        }''')
                        is_reply = nesting > 2
                    except Exception:
                        pass

                    # Extract author
                    author_name = ""
                    author_id = ""
                    author_url = ""

                    author_selectors = [
                        'a[role="link"] > span > span',
                        'a[role="link"] span',
                    ]

                    for sel in author_selectors:
                        author_el = await article.query_selector(sel)
                        if author_el:
                            name = await author_el.inner_text()
                            if name and 1 < len(name.strip()) < 100:
                                author_name = name.strip()
                                try:
                                    parent_link = await author_el.evaluate('el => el.closest("a")?.href')
                                    if parent_link and 'facebook.com' in parent_link:
                                        author_url = parent_link
                                        match = re.search(r'facebook\.com/([^/?]+)', parent_link)
                                        if match:
                                            author_id = match.group(1)
                                except Exception:
                                    pass
                                break

                    if not author_name:
                        continue

                    # Extract text
                    text_elements = await article.query_selector_all('div[dir="auto"]')
                    all_texts = []

                    ui_texts = ['me gusta', 'like', 'responder', 'reply', 'ver más', 'see more']

                    for text_el in text_elements:
                        try:
                            text = (await text_el.inner_text()).strip()
                            if not text or len(text) < 1:
                                continue

                            text_lower = text.lower()

                            if text_lower in ui_texts:
                                continue
                            if re.match(r'^\d+\s*(h|d|m|sem|min)s?\.?$', text_lower):
                                continue
                            if text_lower == author_name.lower():
                                continue

                            all_texts.append(text)
                        except Exception:
                            continue

                    comment_text = max(all_texts, key=len) if all_texts else ""

                    if not comment_text:
                        continue

                    comment_text = self.clean_text(comment_text)

                    # No filtering - extract all comments, including duplicates
                    # Analysis/deduplication will be done later

                    # Extract likes
                    likes = await self._extract_comment_likes(article)

                    # Extract timestamp
                    created_at = int(datetime.now().timestamp())
                    try:
                        time_selectors = ['abbr[data-utime]', 'a[href*="comment_id"] > span:last-child']
                        for time_sel in time_selectors:
                            time_el = await article.query_selector(time_sel)
                            if time_el:
                                utime = await time_el.get_attribute('data-utime')
                                if utime:
                                    created_at = int(utime)
                                    break

                                time_text = await time_el.inner_text()
                                if time_text:
                                    created_at = self.parse_relative_time(time_text)
                                    break
                    except Exception:
                        pass

                    # Extract comment ID from author URL
                    comment_id = ""
                    if author_url:
                        match = re.search(r'comment_id=([^&]+)', author_url)
                        if match:
                            comment_id = match.group(1)

                    comment_index += 1

                    user = self.create_user(
                        user_id=author_id,
                        username=author_id,
                        display_name=author_name,
                        profile_url=author_url
                    )

                    comment_obj = self.create_comment(
                        index=comment_index,
                        comment_id=comment_id or str(comment_index),
                        text=comment_text,
                        user=user,
                        likes=likes,
                        is_reply=is_reply,
                        created_at=created_at
                    )

                    comments.append(comment_obj)

                except Exception:
                    continue

            print(f"   ✅ Extraídos {len(comments)} comentarios")

            replies_count = sum(1 for c in comments if c.is_reply)
            if replies_count > 0:
                print(f"   📝 De los cuales {replies_count} son respuestas")

            # Detect duplicates
            text_counts = {}
            for c in comments:
                text_counts[c.text] = text_counts.get(c.text, 0) + 1
            duplicates = {k: v for k, v in text_counts.items() if v > 1}
            if duplicates:
                print(f"   🔍 Detectados {len(duplicates)} textos duplicados (posibles bots)")

        except Exception as e:
            print(f"⚠️ Error extrayendo comentarios: {e}")

        return comments


async def main():
    """Entry point."""
    if len(sys.argv) > 1:
        post_url = sys.argv[1]
    else:
        post_url = "https://www.facebook.com/photo/?fbid=1373912744767705&set=a.610764161082571"

    print("=" * 60)
    print("🔍 FACEBOOK SCRAPER")
    print("=" * 60)

    scraper = FacebookScraper()
    result = await scraper.scrape(post_url, headless=False)

    if result.comments or result.post.post_id:
        scraper.save_result(result)
        scraper.print_summary(result)

        if result.comments:
            print("\n💬 MUESTRA DE COMENTARIOS:")
            print("-" * 40)
            for comment in result.comments[:5]:
                text_preview = comment.text[:60] + "..." if len(comment.text) > 60 else comment.text
                print(f"   [{comment.user.display_name}]: {text_preview}")
    else:
        print("\n❌ No se pudieron extraer datos")
        if result.error:
            print(f"   Error: {result.error}")

    return result


if __name__ == "__main__":
    asyncio.run(main())
