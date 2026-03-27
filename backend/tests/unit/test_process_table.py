"""Tests for ProcessInfo and ProcessTable."""

from __future__ import annotations

import pytest

from recursive_neon.models.process import ProcessInfo, ProcessTable


@pytest.mark.unit
class TestProcessInfo:
    def test_defaults(self):
        p = ProcessInfo(pid=1, name="init")
        assert p.user == "root"
        assert p.cpu == 0.0
        assert p.memory == 0.0
        assert p.status == "running"
        assert p.tags == []

    def test_custom_fields(self):
        p = ProcessInfo(
            pid=42,
            name="nginx",
            user="www",
            cpu=1.5,
            memory=3.2,
            status="sleeping",
            tags=["network"],
        )
        assert p.pid == 42
        assert p.name == "nginx"
        assert p.user == "www"
        assert p.status == "sleeping"
        assert "network" in p.tags


@pytest.mark.unit
class TestProcessTableBasic:
    def test_empty_table(self):
        table = ProcessTable()
        assert table.count == 0
        assert table.list_all() == []
        assert table.total_cpu() == 0.0
        assert table.total_memory() == 0.0

    def test_add_process(self):
        table = ProcessTable()
        proc = table.add("init", "root", 0.1, 0.2, "sleeping")
        assert proc.pid == 1
        assert proc.name == "init"
        assert table.count == 1

    def test_add_assigns_incrementing_pids(self):
        table = ProcessTable()
        p1 = table.add("a")
        p2 = table.add("b")
        p3 = table.add("c")
        assert p1.pid == 1
        assert p2.pid == 2
        assert p3.pid == 3

    def test_get_by_pid(self):
        table = ProcessTable()
        table.add("init")
        proc = table.get(1)
        assert proc is not None
        assert proc.name == "init"

    def test_get_missing_returns_none(self):
        table = ProcessTable()
        assert table.get(999) is None

    def test_remove_process(self):
        table = ProcessTable()
        table.add("init")
        assert table.remove(1) is True
        assert table.count == 0
        assert table.get(1) is None

    def test_remove_missing_returns_false(self):
        table = ProcessTable()
        assert table.remove(999) is False

    def test_list_sorted_by_pid(self):
        table = ProcessTable()
        table.add("c")
        table.add("a")
        table.add("b")
        names = [p.name for p in table.list_all()]
        assert names == ["c", "a", "b"]  # ordered by PID, not name


@pytest.mark.unit
class TestProcessTableQueries:
    def test_find_by_tag(self):
        table = ProcessTable()
        table.add("sshd", tags=["network"])
        table.add("nginx", tags=["network"])
        table.add("watchdog", tags=["security"])

        network = table.find_by_tag("network")
        assert len(network) == 2
        assert {p.name for p in network} == {"sshd", "nginx"}

    def test_find_by_tag_empty(self):
        table = ProcessTable()
        table.add("init")
        assert table.find_by_tag("security") == []

    def test_find_by_name(self):
        table = ProcessTable()
        table.add("postgres")
        table.add("postgres: worker")
        table.add("nginx")

        results = table.find_by_name("postgres")
        assert len(results) == 1
        assert results[0].name == "postgres"

    def test_total_cpu(self):
        table = ProcessTable()
        table.add("a", cpu=1.5)
        table.add("b", cpu=2.5)
        table.add("c", cpu=0.5)
        assert table.total_cpu() == pytest.approx(4.5)

    def test_total_memory(self):
        table = ProcessTable()
        table.add("a", memory=3.0)
        table.add("b", memory=7.0)
        assert table.total_memory() == pytest.approx(10.0)


@pytest.mark.unit
class TestProcessTableDefaults:
    def test_with_defaults_not_empty(self):
        table = ProcessTable.with_defaults()
        assert table.count > 0

    def test_with_defaults_has_security_processes(self):
        table = ProcessTable.with_defaults()
        security = table.find_by_tag("security")
        assert len(security) >= 2

    def test_with_defaults_has_expected_daemons(self):
        table = ProcessTable.with_defaults()
        names = {p.name for p in table.list_all()}
        assert "init" in names
        assert "sshd" in names
        assert "nginx" in names

    def test_with_defaults_pids_are_sequential(self):
        table = ProcessTable.with_defaults()
        pids = [p.pid for p in table.list_all()]
        assert pids == list(range(1, len(pids) + 1))
