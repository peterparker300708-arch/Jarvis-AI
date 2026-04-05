"""Tests for file manager module"""
import pytest
import tempfile
import os
from modules.file_manager import FileManager


@pytest.fixture
def fm():
    return FileManager()


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


def test_list_directory(fm, temp_dir):
    open(os.path.join(temp_dir, "test.txt"), 'w').close()
    result = fm.list_directory(temp_dir)
    assert isinstance(result, list)
    assert len(result) >= 1


def test_create_and_delete_file(fm, temp_dir):
    path = os.path.join(temp_dir, "newfile.txt")
    fm.create_file(path, "Hello World")
    assert os.path.exists(path)
    fm.delete(path, recycle=False)
    assert not os.path.exists(path)


def test_create_directory(fm, temp_dir):
    new_dir = os.path.join(temp_dir, "subdir")
    fm.create_directory(new_dir)
    assert os.path.isdir(new_dir)


def test_search_files(fm, temp_dir):
    open(os.path.join(temp_dir, "document.txt"), 'w').close()
    open(os.path.join(temp_dir, "image.png"), 'w').close()
    results = fm.search(temp_dir, "*.txt")
    assert len(results) >= 1
    assert any("document.txt" in r for r in results)


def test_get_file_info(fm, temp_dir):
    path = os.path.join(temp_dir, "info_test.txt")
    with open(path, 'w') as f:
        f.write("test content")
    info = fm.get_file_info(path)
    assert 'name' in info
    assert 'size' in info
