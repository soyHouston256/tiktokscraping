"""
Base scraper class that all platform scrapers should extend.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime
from typing import List, Optional
import time
import re

from .models import ScrapeResult, Post, Comment, User


class BaseScraper(ABC):
    """
    Abstract base class for all platform scrapers.

    Subclasses must implement:
    - platform_name: Property returning the platform identifier
    - scrape(): Main scraping method
    - _extract_post_data(): Extract post/video metadata
    - _extract_comments(): Extract comments from the page
    """

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize the scraper.

        Args:
            output_dir: Directory to save results. If None, uses default.
        """
        self.script_dir = Path(__file__).resolve().parent.parent
        self.project_root = self.script_dir.parent

        if output_dir:
            self.output_dir = output_dir
        else:
            self.output_dir = self.project_root / "data" / f"scrapes_{self.platform_name}"

        self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the platform identifier (e.g., 'tiktok', 'facebook')."""
        pass

    @abstractmethod
    async def scrape(self, url: str, **kwargs) -> ScrapeResult:
        """
        Main scraping method.

        Args:
            url: URL of the post/video to scrape
            **kwargs: Platform-specific options

        Returns:
            ScrapeResult with all extracted data
        """
        pass

    @abstractmethod
    async def _extract_post_data(self, **kwargs) -> Post:
        """Extract post/video metadata."""
        pass

    @abstractmethod
    async def _extract_comments(self, **kwargs) -> List[Comment]:
        """Extract comments from the content."""
        pass

    # =========================================================================
    # Utility methods for all scrapers
    # =========================================================================

    def create_result(self, url: str) -> ScrapeResult:
        """Create a new ScrapeResult with basic info."""
        return ScrapeResult(
            platform=self.platform_name,
            source_url=url,
            extracted_at=datetime.now().isoformat()
        )

    def create_user(
        self,
        user_id: str = "",
        username: str = "",
        display_name: str = "",
        profile_url: str = "",
        verified: bool = False
    ) -> User:
        """Create a User object with the given data."""
        return User(
            id=user_id or username,
            username=username,
            display_name=display_name or username,
            profile_url=profile_url,
            verified=verified
        )

    def create_comment(
        self,
        index: int,
        comment_id: str,
        text: str,
        user: User,
        likes: int = 0,
        reply_count: int = 0,
        is_reply: bool = False,
        created_at: int = 0,
        parent_comment_id: Optional[str] = None
    ) -> Comment:
        """Create a Comment object with the given data."""
        return Comment(
            index=index,
            comment_id=comment_id,
            text=text,
            user=user,
            likes=likes,
            reply_count=reply_count,
            is_reply=is_reply,
            created_at=created_at or int(time.time()),
            parent_comment_id=parent_comment_id
        )

    def generate_filename(self, prefix: str = "scrape") -> str:
        """Generate a timestamped filename."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}.json"

    def save_result(self, result: ScrapeResult, filename: Optional[str] = None) -> Path:
        """
        Save scrape result to JSON file.

        Args:
            result: ScrapeResult to save
            filename: Optional custom filename

        Returns:
            Path to saved file
        """
        if not filename:
            filename = self.generate_filename(self.platform_name)

        filepath = self.output_dir / filename
        result.save(str(filepath))
        print(f"💾 Guardado en: {filepath}")
        return filepath

    # =========================================================================
    # Common parsing utilities
    # =========================================================================

    @staticmethod
    def parse_relative_time(time_str: str) -> int:
        """
        Convert relative time string to Unix timestamp.
        Handles formats like: "5 m", "2 h", "1 d", "3 sem", etc.

        Args:
            time_str: Relative time string

        Returns:
            Unix timestamp in seconds
        """
        from datetime import timedelta

        now = datetime.now()
        time_str = time_str.lower().strip()

        patterns = [
            (r'(\d+)\s*(s|seg|second)', 'seconds'),
            (r'(\d+)\s*(m|min|minute|minuto)', 'minutes'),
            (r'(\d+)\s*(h|hr|hour|hora)', 'hours'),
            (r'(\d+)\s*(d|day|día|dia)', 'days'),
            (r'(\d+)\s*(w|week|sem|semana)', 'weeks'),
            (r'(\d+)\s*(mo|month|mes)', 'months'),
            (r'(\d+)\s*(y|year|año)', 'years'),
            (r'(ayer|yesterday)', 'yesterday'),
            (r'(hoy|today)', 'today'),
            (r'(ahora|now|just)', 'now'),
        ]

        for pattern, unit in patterns:
            match = re.search(pattern, time_str)
            if match:
                if unit == 'yesterday':
                    return int((now - timedelta(days=1)).timestamp())
                elif unit == 'today' or unit == 'now':
                    return int(now.timestamp())
                else:
                    num = int(match.group(1))
                    if unit == 'seconds':
                        delta = timedelta(seconds=num)
                    elif unit == 'minutes':
                        delta = timedelta(minutes=num)
                    elif unit == 'hours':
                        delta = timedelta(hours=num)
                    elif unit == 'days':
                        delta = timedelta(days=num)
                    elif unit == 'weeks':
                        delta = timedelta(weeks=num)
                    elif unit == 'months':
                        delta = timedelta(days=num * 30)
                    elif unit == 'years':
                        delta = timedelta(days=num * 365)
                    else:
                        delta = timedelta()

                    return int((now - delta).timestamp())

        # If no pattern matches, return current timestamp
        return int(now.timestamp())

    @staticmethod
    def extract_id_from_url(url: str, patterns: List[str]) -> str:
        """
        Extract an ID from URL using multiple regex patterns.

        Args:
            url: URL to parse
            patterns: List of regex patterns with capture groups

        Returns:
            Extracted ID or empty string
        """
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return ""

    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove common UI elements
        text = re.sub(r'\s*(Ver más|See more|Ver menos|See less)\s*$', '', text, flags=re.IGNORECASE)
        return text.strip()

    def print_summary(self, result: ScrapeResult):
        """Print a summary of the scrape result."""
        print("\n" + "=" * 60)
        print(f"📊 RESUMEN - {result.platform.upper()}")
        print("=" * 60)
        print(f"   URL: {result.source_url}")
        print(f"   Post ID: {result.post.post_id}")
        print(f"   Autor: {result.post.author.name or result.post.author.username}")
        print(f"   Likes: {result.post.likes:,}")
        print(f"   Comentarios extraídos: {len(result.comments)}")

        if result.comments:
            replies = sum(1 for c in result.comments if c.is_reply)
            print(f"   - Comentarios principales: {len(result.comments) - replies}")
            print(f"   - Respuestas: {replies}")

            # Top comments by likes
            top = sorted(result.comments, key=lambda x: x.likes, reverse=True)[:3]
            if top and top[0].likes > 0:
                print(f"\n   🔥 Top comentarios:")
                for c in top:
                    text_preview = c.text[:50] + "..." if len(c.text) > 50 else c.text
                    print(f"      ({c.likes} likes) @{c.user.username}: {text_preview}")

        if result.error:
            print(f"\n   ⚠️ Error: {result.error}")

        print(f"\n   ⏱️ Duración: {result.scrape_duration_seconds:.1f}s")
        print("=" * 60)
