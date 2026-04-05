"""Tests for utility functions"""
import pytest
from utils.helpers import format_bytes, format_duration, sanitize_filename, get_platform


def test_format_bytes():
    assert format_bytes(0) == "0 B"
    assert "KB" in format_bytes(1024)
    assert "MB" in format_bytes(1024 * 1024)
    assert "GB" in format_bytes(1024 ** 3)


def test_format_duration():
    assert "second" in format_duration(1)
    assert "minute" in format_duration(60)
    assert "hour" in format_duration(3600)


def test_sanitize_filename():
    assert "/" not in sanitize_filename("file/name")
    assert "\\" not in sanitize_filename("file\\name")
    assert sanitize_filename("normal_file.txt") == "normal_file.txt"


def test_get_platform():
    platform = get_platform()
    assert platform in ('windows', 'linux', 'mac')
