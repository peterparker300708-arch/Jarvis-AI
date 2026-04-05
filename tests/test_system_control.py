"""Tests for system control module"""
import pytest
from core.system_control import SystemControl


@pytest.fixture
def sys_ctrl():
    return SystemControl()


def test_get_system_info(sys_ctrl):
    info = sys_ctrl.get_system_info()
    assert 'cpu_percent' in info
    assert 'memory_percent' in info
    assert 'disk_percent' in info
    assert isinstance(info['cpu_percent'], (int, float))


def test_execute_command(sys_ctrl):
    stdout, stderr, code = sys_ctrl.execute_command("echo hello")
    assert code == 0
    assert "hello" in stdout


def test_get_running_processes(sys_ctrl):
    processes = sys_ctrl.get_running_processes()
    assert isinstance(processes, list)
    assert len(processes) > 0


def test_get_memory_info(sys_ctrl):
    mem = sys_ctrl.get_memory_info()
    assert 'total' in mem
    assert 'used' in mem
    assert 'percent' in mem


def test_get_disk_info(sys_ctrl):
    disk = sys_ctrl.get_disk_info()
    assert isinstance(disk, (list, dict))
