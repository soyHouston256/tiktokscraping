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
            # Try to connect to existing Chrome, or launch new one
            browser = None
            context = None
            using_cdp = False

            # Option 1: Try CDP connection to running Chrome (port 9222)
            try:
                browser = await p.chromium.connect_over_cdp("http://localhost:9222")
                context = browser.contexts[0] if browser.contexts else await browser.new_context()
                print("✅ Conectado a Chrome existente via CDP")
                using_cdp = True
            except Exception:
                pass

            # Option 2: Launch fresh Chrome with our settings
            if not browser:
                print("ℹ️ Iniciando nuevo navegador...")
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

                # Load cookies only for new browser
                await self._load_cookies(context)

            # Use existing page if available (better session state), or create new one
            if using_cdp and context.pages:
                page = context.pages[0]
                print("   Usando pestaña existente")
            else:
                page = await context.new_page()

            self.page = page
            self.context = context

            try:
                print(f"🔗 Navegando a: {url}")
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                except Exception as nav_error:
                    # If navigation fails, try with networkidle or just wait
                    if "ERR_HTTP_RESPONSE_CODE_FAILURE" in str(nav_error):
                        print("   ⚠️ Error HTTP - reintentando con diferente estrategia...")
                        await page.wait_for_timeout(2000)
                        # Try going to TikTok home first, then to the video
                        await page.goto("https://www.tiktok.com", wait_until="domcontentloaded", timeout=30000)
                        await page.wait_for_timeout(2000)
                        await page.goto(url, wait_until="commit", timeout=60000)
                    else:
                        raise nav_error

                # Wait longer for page to fully load
                print("⏳ Esperando que la página cargue...")
                await page.wait_for_timeout(5000)

                # Close any popups
                await self._close_popups(page)

                # Check if cookies are valid - if not, prompt user
                cookies_valid = await self._check_session_valid(page)
                if not cookies_valid:
                    print("\n" + "=" * 60)
                    print("⚠️  SESIÓN NO VÁLIDA O EXPIRADA")
                    print("=" * 60)
                    print("Por favor:")
                    print("  1. Inicia sesión en TikTok en el navegador abierto")
                    print("  2. Completa cualquier captcha que aparezca")
                    print("  3. El script detectará cuando estés listo")
                    print("=" * 60 + "\n")

                    # Wait for login and/or captcha to be completed
                    if not await self._wait_for_login_and_captcha(page):
                        result.error = "Login/captcha timeout"
                        if not using_cdp:
                            await browser.close()
                        return result
                else:
                    print("   Continuando con sesión activa...")

                # Wait for video to load
                await self._wait_for_video(page)

                # Extract post data
                result.post = await self._extract_post_data(page=page, video_id=video_id, url=url)

                # Open comments panel first
                await self._open_comments_panel(page)

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

            # Only close browser if we launched it (not CDP)
            if not using_cdp:
                await browser.close()
            else:
                # Just close the page we created, not the whole browser
                try:
                    await page.close()
                except Exception:
                    pass

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

    async def _check_session_valid(self, page: Page) -> bool:
        """Check if current session is valid (user is logged in)."""
        try:
            is_logged_in = await page.evaluate('''() => {
                // Check for clear indicators of being logged in
                const profileIcon = document.querySelector('[data-e2e="profile-icon"]');
                const uploadButton = document.querySelector('[data-e2e="upload-icon"]');
                const avatarInHeader = document.querySelector('header [class*="Avatar"], header img[class*="avatar"]');

                // Check for login buttons (indicates NOT logged in)
                const loginButton = document.querySelector('[data-e2e="top-login-button"]');

                // If we find profile/upload icons and no login button, we're logged in
                if ((profileIcon || uploadButton || avatarInHeader) && !loginButton) {
                    return true;
                }

                // If there's a login button visible, we're not logged in
                if (loginButton) {
                    return false;
                }

                // Uncertain - return false to be safe
                return false;
            }''')

            if is_logged_in:
                print("✅ Sesión válida detectada")
                return True
            else:
                print("⚠️  No se detectó sesión válida")
                return False

        except Exception as e:
            print(f"⚠️  Error verificando sesión: {e}")
            return False

    async def _wait_for_login_and_captcha(self, page: Page):
        """Wait for user to login and complete any captcha challenges."""
        print("\n" + "=" * 60)
        print("🔐 ESPERANDO LOGIN Y/O CAPTCHA")
        print("=" * 60)
        print("1. Si aparece login, inicia sesión")
        print("2. Si aparece captcha/verificación, complétalo")
        print("3. El script esperará hasta que confirmes (Enter)")
        print("=" * 60 + "\n")

        max_wait = 300  # 5 minutos máximo
        start = time.time()
        last_status = ""
        login_required = False
        captcha_required = False

        # First, check if we need login by looking for login prompts
        await page.wait_for_timeout(3000)  # Wait for page to fully load

        while time.time() - start < max_wait:
            try:
                status = await page.evaluate('''() => {
                    // Check for captcha anywhere on page
                    const captcha = document.querySelector('[class*="captcha"], [id*="captcha"], [class*="verify"], iframe[src*="captcha"], [class*="Captcha"]');
                    if (captcha) return 'captcha';

                    // Check for login modal
                    const loginModal = document.querySelector('[data-e2e="login-modal"], [class*="LoginModal"], [class*="login-modal"]');
                    if (loginModal) return 'login_modal';

                    // Check for login page
                    if (window.location.pathname.includes('/login')) return 'login_page';

                    // Check for login prompt in comments section
                    const commentArea = document.querySelector('[class*="CommentList"], [class*="comment"]');
                    if (commentArea) {
                        const loginPromptInComments = commentArea.querySelector('[class*="login"], button[class*="Login"]');
                        if (loginPromptInComments) return 'login_in_comments';
                    }

                    // Check for generic login button that blocks content
                    const loginButton = document.querySelector('[data-e2e="comment-login-button"], button:has-text("Log in to comment")');
                    if (loginButton) return 'login_required';

                    // Check if logged in - look for profile icon AND avatar in header
                    const profileIcon = document.querySelector('[data-e2e="profile-icon"]');
                    const avatarInHeader = document.querySelector('header [class*="Avatar"], header img[class*="avatar"]');
                    const uploadButton = document.querySelector('[data-e2e="upload-icon"]');

                    if (profileIcon || avatarInHeader || uploadButton) return 'logged_in';

                    // Check if video is visible but we're not sure about login
                    const video = document.querySelector('video, [data-e2e="browse-video"]');
                    if (video) return 'video_loaded';

                    return 'loading';
                }''')

                if status != last_status:
                    if status == 'captcha':
                        print("   ⚠️ Captcha detectado - Por favor complétalo...")
                        captcha_required = True
                    elif status in ['login_modal', 'login_page', 'login_in_comments', 'login_required']:
                        print("   🔐 Login requerido - Por favor inicia sesión...")
                        login_required = True
                    elif status == 'logged_in':
                        print("   ✅ Sesión detectada!")
                        if not captcha_required:
                            # Give user a moment to see the status
                            await page.wait_for_timeout(2000)
                            return True
                    elif status == 'video_loaded':
                        print("   📹 Video cargado, verificando sesión...")
                    last_status = status

                # Only proceed automatically if we detected login AND no captcha pending
                if status == 'logged_in' and not captcha_required:
                    await page.wait_for_timeout(2000)
                    return True

                # If captcha was required but now it's gone, check again
                if captcha_required and status not in ['captcha']:
                    print("   ✅ Captcha completado!")
                    captcha_required = False
                    # Continue to wait for login confirmation

            except Exception as e:
                pass

            await page.wait_for_timeout(2000)

            # Every 30 seconds, remind user
            elapsed = int(time.time() - start)
            if elapsed > 0 and elapsed % 30 == 0:
                print(f"   ⏳ Esperando... ({elapsed}s)")

        print("   ⚠️ Timeout esperando login/captcha")
        return False

    async def _wait_for_video(self, page: Page):
        """Wait for video content to load."""
        print("⏳ Esperando que cargue el video...")
        try:
            await page.wait_for_selector('[data-e2e="browse-video"], video', timeout=15000)
            await page.wait_for_timeout(2000)
            print("   ✅ Video cargado")
        except Exception:
            print("   ⚠️ Timeout esperando video")

    async def _open_comments_panel(self, page: Page):
        """Open the comments panel by clicking on comment icon."""
        print("💬 Abriendo panel de comentarios...")
        try:
            # Click on comment icon to open comments panel
            comment_btn = await page.query_selector('[data-e2e="comment-icon"], [data-e2e="browse-comment-icon"]')
            if comment_btn:
                await comment_btn.click()
                await page.wait_for_timeout(2000)
                print("   ✅ Panel de comentarios abierto")
            else:
                # Try clicking on comment count
                comment_count = await page.query_selector('[data-e2e="comment-count"], [data-e2e="browse-comment-count"]')
                if comment_count:
                    await comment_count.click()
                    await page.wait_for_timeout(2000)
                    print("   ✅ Panel de comentarios abierto (via count)")

            # Wait for comments to load
            await page.wait_for_timeout(3000)

            # Check if comments loaded
            loaded = await page.evaluate('''() => {
                return document.querySelectorAll('a[href*="/@"]').length;
            }''')
            print(f"   📊 Links de usuario encontrados: {loaded}")

        except Exception as e:
            print(f"   ⚠️ Error abriendo comentarios: {e}")

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

    async def _expand_comments(self, page: Page, max_iterations: int = 300):
        """Expand comments by scrolling the comment section."""
        print("📜 Expandiendo comentarios...")

        await page.wait_for_timeout(2000)

        last_count = 0
        no_change_count = 0

        for iteration in range(max_iterations):
            # Scroll the comment container
            try:
                await page.evaluate('''() => {
                    // Find the scrollable comment container
                    const commentList = document.querySelector('[class*="DivCommentListContainer"]');
                    if (commentList) {
                        // Scroll the container itself
                        commentList.scrollTop = commentList.scrollHeight;

                        // Also try scrolling parent containers
                        let parent = commentList.parentElement;
                        for (let i = 0; i < 3 && parent; i++) {
                            if (parent.scrollHeight > parent.clientHeight + 50) {
                                parent.scrollTop = parent.scrollHeight;
                            }
                            parent = parent.parentElement;
                        }
                    }

                    // Also try the main content area
                    const contentArea = document.querySelector('[class*="DivContentContainer"], [class*="DivBrowserModeContainer"]');
                    if (contentArea && contentArea.scrollHeight > contentArea.clientHeight) {
                        contentArea.scrollTop = contentArea.scrollHeight;
                    }
                }''')
            except Exception:
                pass

            await page.wait_for_timeout(800)

            # Click "View more comments" buttons
            try:
                await page.evaluate('''() => {
                    const moreButtons = document.querySelectorAll('[class*="ViewMore"], [class*="view-more"], [class*="PViewMoreButton"]');
                    moreButtons.forEach(btn => {
                        if (btn.offsetParent !== null) {
                            btn.click();
                        }
                    });
                }''')
            except Exception:
                pass

            # Count current comments (main + replies)
            try:
                current = await page.evaluate('''() => {
                    const commentList = document.querySelector('[class*="DivCommentListContainer"]');
                    if (commentList) {
                        return commentList.querySelectorAll('[class*="DivCommentItemWrapper"]').length;
                    }
                    return 0;
                }''')
            except Exception:
                current = last_count

            if iteration % 20 == 0:
                print(f"   🔄 Iteración {iteration}: {current} comentarios")

            if current == last_count:
                no_change_count += 1
            else:
                no_change_count = 0

            last_count = current

            # Need more iterations without change before stopping
            if no_change_count >= 10 and iteration > 15:
                break

        print(f"✅ Expansión completada: {last_count} comentarios visibles")

        # Now expand replies
        await self._expand_replies(page)

        return last_count

    async def _expand_replies(self, page: Page):
        """Click on 'View X replies' buttons to load reply threads."""
        print("📂 Expandiendo respuestas...")

        total_expanded = 0
        max_rounds = 10

        for round in range(max_rounds):
            # Find and click "View X replies" buttons
            try:
                clicked = await page.evaluate('''() => {
                    let clickCount = 0;

                    // Find all "View replies" buttons that haven't been clicked
                    const replyButtons = document.querySelectorAll(
                        '[class*="DivViewMoreRepliesWrapper"], ' +
                        '[class*="DivViewRepliesContainer"], ' +
                        '[class*="ViewReplies"]'
                    );

                    replyButtons.forEach(btn => {
                        // Check if it's visible and contains "View" or "Ver" text
                        if (btn.offsetParent !== null && !btn.dataset.expanded) {
                            const text = btn.textContent.toLowerCase();
                            if ((text.includes('view') && text.includes('repl')) ||
                                (text.includes('ver') && text.includes('respuesta'))) {
                                btn.click();
                                btn.dataset.expanded = 'true';
                                clickCount++;
                            }
                        }
                    });

                    return clickCount;
                }''')

                if clicked > 0:
                    total_expanded += clicked
                    await page.wait_for_timeout(1500)  # Wait for replies to load
                else:
                    # No more buttons to click
                    break

            except Exception:
                break

        if total_expanded > 0:
            print(f"   ✅ Expandidas {total_expanded} secciones de respuestas")
        else:
            print("   ℹ️ No hay respuestas para expandir")

    async def _extract_comments(
        self,
        page: Page = None,
        max_comments: Optional[int] = None,
        include_replies: bool = True,
        **kwargs
    ) -> List[Comment]:
        """Extract comments using Playwright - DOM-based extraction."""
        comments = []

        print("\n💬 Extrayendo comentarios...")

        # First expand comments
        await self._expand_comments(page)

        # Extract comments from DOM elements
        try:
            raw_comments = await page.evaluate('''() => {
                const comments = [];

                // Find comment list container first
                const commentList = document.querySelector('[class*="DivCommentListContainer"]');
                if (!commentList) return comments;

                // Find all comment items inside the list (use ItemWrapper not ObjectWrapper to avoid duplicates)
                const wrappers = commentList.querySelectorAll('[class*="DivCommentItemWrapper"]');

                wrappers.forEach((wrapper, index) => {
                    try {
                        // Get username - look for the username element with data-e2e
                        const usernameEl = wrapper.querySelector('[data-e2e*="comment-username"] a, [data-e2e*="comment-username"] p');
                        let username = '';
                        let userId = '';

                        if (usernameEl) {
                            username = usernameEl.textContent.trim();
                            const link = usernameEl.closest('a') || usernameEl.querySelector('a');
                            if (link) {
                                const href = link.getAttribute('href') || '';
                                userId = href.replace('/@', '').split('?')[0];
                            }
                        }

                        // Fallback: get first link in avatar/header area
                        if (!username) {
                            const avatarLink = wrapper.querySelector('a[href*="/@"]');
                            if (avatarLink) {
                                const href = avatarLink.getAttribute('href') || '';
                                userId = href.replace('/@', '').split('?')[0];
                                // Get display name from the header
                                const nameEl = wrapper.querySelector('p[class*="StyledTUXText"], [class*="UsernameContent"] p');
                                username = nameEl ? nameEl.textContent.trim() : userId;
                            }
                        }

                        if (!username && !userId) return;
                        if (!username) username = userId;
                        if (!userId) userId = username;

                        // Get comment text from data-e2e="comment-level-1"
                        let text = '';
                        const textEl = wrapper.querySelector('[data-e2e*="comment-level"]');
                        if (textEl) {
                            text = textEl.textContent.trim();
                        }

                        // Fallback: look for content wrapper
                        if (!text) {
                            const contentWrapper = wrapper.querySelector('[class*="DivCommentContentWrapper"]');
                            if (contentWrapper) {
                                // Get all paragraph/span elements except username
                                const textEls = contentWrapper.querySelectorAll('p, span');
                                const textParts = [];
                                textEls.forEach(el => {
                                    const t = el.textContent.trim();
                                    if (t === username) return;
                                    if (/^\\d+[hmdwsW]( ago)?$/.test(t)) return;
                                    if (/^\\d+[KkMm]?$/.test(t)) return;
                                    if (/^(Reply|Responder|View|Ver|Hide|Ocultar|Creator)/i.test(t)) return;
                                    if (t.length > 1 && !textParts.includes(t)) {
                                        textParts.push(t);
                                    }
                                });
                                text = textParts.slice(1).join(' '); // Skip first which is usually username
                            }
                        }

                        // Clean up text
                        text = text
                            .replace(/\\s+/g, ' ')
                            .replace(new RegExp('^' + username.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&') + '\\\\s*'), '')
                            .replace(/^[\\s·-]+|[\\s·-]+$/g, '')
                            .trim();

                        if (!text || text.length < 1) return;

                        // Get likes count
                        let likes = 0;
                        const likeEl = wrapper.querySelector('[data-e2e*="like-count"], [class*="LikeCount"]');
                        if (likeEl) {
                            const likeText = likeEl.textContent.trim();
                            if (/^\\d+[KkMm]?$/.test(likeText)) {
                                if (likeText.toUpperCase().includes('K')) {
                                    likes = parseFloat(likeText) * 1000;
                                } else if (likeText.toUpperCase().includes('M')) {
                                    likes = parseFloat(likeText) * 1000000;
                                } else {
                                    likes = parseInt(likeText) || 0;
                                }
                            }
                        }

                        // Get timestamp
                        let timestamp = '';
                        const timeMatch = wrapper.textContent.match(/(\\d+[hmdwsW])( ago)?/);
                        if (timeMatch) {
                            timestamp = timeMatch[1];
                        }

                        // Check if this is a reply (inside DivReplyContainer or DivReplyScrollBasis)
                        const isReply = wrapper.closest('[class*="DivReplyContainer"]') !== null ||
                                       wrapper.closest('[class*="DivReplyScrollBasis"]') !== null ||
                                       wrapper.closest('[class*="ReplyContainer"]') !== null;

                        comments.push({
                            username: username,
                            userId: userId,
                            text: text.substring(0, 1000),
                            likes: Math.floor(likes),
                            timestamp: timestamp,
                            isReply: isReply
                        });

                    } catch (e) {
                        // Skip this comment on error
                    }
                });

                return comments;
            }''')

            print(f"   🔍 Encontrados {len(raw_comments)} comentarios en DOM")

            for idx, raw in enumerate(raw_comments):
                if max_comments and idx >= max_comments:
                    break

                try:
                    user = self.create_user(
                        user_id=raw.get('userId', raw['username']),
                        username=raw['username'],
                        display_name=raw['username']
                    )

                    comment_obj = self.create_comment(
                        index=idx + 1,
                        comment_id=str(idx + 1),
                        text=raw['text'],
                        user=user,
                        likes=raw.get('likes', 0),
                        is_reply=raw.get('isReply', False),
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
