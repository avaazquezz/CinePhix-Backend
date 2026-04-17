"""Shared enum for media types across models."""

import enum


class MediaType(str, enum.Enum):
    """Type of media item."""

    MOVIE = "movie"
    TV = "tv"