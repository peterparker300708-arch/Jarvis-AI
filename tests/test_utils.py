"""Tests for utility functions"""
import pytest
from utils.helpers import format_bytes, format_duration, sanitize_filename, get_platform


def test_format_bytes():
    result_zero = format_bytes(0)
    assert "B" in result_zero
    assert "KB" in format_bytes(1024)
    assert "MB" in format_bytes(1024 * 1024)
    assert "GB" in format_bytes(1024 ** 3)


def test_format_duration():
    result_sec = format_duration(1)
    result_min = format_duration(60)
    result_hr = format_duration(3600)
    # Accept short forms (1s) or long forms (1 second)
    assert any(s in result_sec for s in ("s", "second"))
    assert any(s in result_min for s in ("m", "min", "minute"))
    assert any(s in result_hr for s in ("h", "hr", "hour"))


def test_sanitize_filename():
    assert "/" not in sanitize_filename("file/name")
    assert "\\" not in sanitize_filename("file\\name")
    assert sanitize_filename("normal_file.txt") == "normal_file.txt"


def test_get_platform():
    platform = get_platform()
    assert platform in ('windows', 'linux', 'mac')
