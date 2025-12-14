"""
Background tasks for EVE Wargames application.

This module contains Celery tasks for data collection, processing, and maintenance.
"""

from .data_collection import collect_faction_warfare_data

__all__ = ["collect_faction_warfare_data"]
