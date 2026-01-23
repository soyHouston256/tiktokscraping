"""
Data models for unified scraping structure across platforms.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List
from datetime import datetime


@dataclass
class User:
    """Unified user model for all platforms."""
    id: str = ""
    username: str = ""
    display_name: str = ""
    profile_url: str = ""
    verified: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Comment:
    """Unified comment model for all platforms."""
    index: int
    comment_id: str
    text: str
    likes: int = 0
    reply_count: int = 0
    is_reply: bool = False
    created_at: int = 0  # Unix timestamp in seconds
    user: User = field(default_factory=User)
    parent_comment_id: Optional[str] = None  # For replies

    def to_dict(self) -> dict:
        data = asdict(self)
        data['user'] = self.user.to_dict()
        return data


@dataclass
class PostAuthor:
    """Author information for posts."""
    id: str = ""
    name: str = ""
    username: str = ""
    profile_url: str = ""
    profile_picture: str = ""
    verified: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Attachment:
    """Media attachment model."""
    type: str  # "photo", "video"
    url: str
    id: str = ""
    thumbnail_url: str = ""
    caption: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Post:
    """Unified post/video model for all platforms."""
    post_id: str
    text: str = ""
    author: PostAuthor = field(default_factory=PostAuthor)
    likes: int = 0
    comments_total: int = 0
    shares: int = 0
    views: int = 0
    created_at: int = 0  # Unix timestamp
    attachments: List[Attachment] = field(default_factory=list)
    # Platform-specific metrics
    extra_metrics: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        data = asdict(self)
        data['author'] = self.author.to_dict()
        data['attachments'] = [a.to_dict() for a in self.attachments]
        return data


@dataclass
class ScrapeResult:
    """Unified result structure for all scrapers."""
    platform: str  # "tiktok", "facebook", "instagram", etc.
    source_url: str
    extracted_at: str = ""  # ISO format
    post: Post = field(default_factory=lambda: Post(post_id=""))
    comments: List[Comment] = field(default_factory=list)
    # Scrape metadata
    scrape_duration_seconds: float = 0
    error: Optional[str] = None

    def __post_init__(self):
        if not self.extracted_at:
            self.extracted_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "platform": self.platform,
            "source_url": self.source_url,
            "extracted_at": self.extracted_at,
            "post": self.post.to_dict(),
            "comments": [c.to_dict() for c in self.comments],
            "comments_count": len(self.comments),
            "scrape_duration_seconds": self.scrape_duration_seconds,
            "error": self.error
        }

    def to_json(self, indent: int = 2) -> str:
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def save(self, filepath: str):
        """Save result to JSON file."""
        from pathlib import Path
        Path(filepath).write_text(self.to_json(), encoding='utf-8')
