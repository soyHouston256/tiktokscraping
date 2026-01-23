"""
Common module for scrapers.
Contains base classes and data models for unified scraping across platforms.
"""

from .models import User, Comment, Post, ScrapeResult
from .base_scraper import BaseScraper

__all__ = ['User', 'Comment', 'Post', 'ScrapeResult', 'BaseScraper']
