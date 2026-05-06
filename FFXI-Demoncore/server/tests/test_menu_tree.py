"""Tests for menu_tree."""
from __future__ import annotations

from server.menu_tree import MenuTree


def _setup():
    t = MenuTree()
    t.define_root(job="BLM")
    t.add_node(
        job="BLM", parent_path=(),
        node_id="magic", label="Magic",
    )
    t.add_node(
        job="BLM", parent_path=("magic",),
        node_id="black_magic", label="Black Magic",
    )
    t.add_node(
        job="BLM", parent_path=("magic", "black_magic"),
        node_id="elemental", label="Elemental",
    )
    t.add_node(
        job="BLM",
        parent_path=("magic", "black_magic", "elemental"),
        node_id="fire_iii", label="Fire III",
        command_id="fire_iii",
    )
    return t


def test_define_root_happy():
    t = MenuTree()
    assert t.define_root(job="BLM") is True


def test_define_root_blank_blocked():
    t = MenuTree()
    assert t.define_root(job="") is False


def test_define_root_duplicate_blocked():
    t = MenuTree()
    t.define_root(job="BLM")
    assert t.define_root(job="BLM") is False


def test_add_node_happy():
    t = _setup()
    assert t.total_nodes(job="BLM") == 5   # root + 4


def test_add_node_blank_id_blocked():
    t = MenuTree()
    t.define_root(job="BLM")
    out = t.add_node(
        job="BLM", parent_path=(),
        node_id="", label="x",
    )
    assert out is False


def test_add_node_blank_label_blocked():
    t = MenuTree()
    t.define_root(job="BLM")
    out = t.add_node(
        job="BLM", parent_path=(),
        node_id="x", label="",
    )
    assert out is False


def test_add_node_unknown_parent_blocked():
    t = MenuTree()
    t.define_root(job="BLM")
    out = t.add_node(
        job="BLM", parent_path=("nope",),
        node_id="x", label="X",
    )
    assert out is False


def test_add_node_duplicate_child_blocked():
    t = _setup()
    out = t.add_node(
        job="BLM", parent_path=(),
        node_id="magic", label="Other Magic",
    )
    assert out is False


def test_children_at_root():
    t = _setup()
    kids = t.children(job="BLM", path=())
    labels = [k.label for k in kids]
    assert labels == ["Magic"]


def test_children_at_intermediate():
    t = _setup()
    kids = t.children(job="BLM", path=("magic",))
    labels = [k.label for k in kids]
    assert labels == ["Black Magic"]


def test_children_unknown_path_empty():
    t = _setup()
    kids = t.children(job="BLM", path=("ghost",))
    assert kids == []


def test_children_leaf_empty():
    t = _setup()
    kids = t.children(
        job="BLM",
        path=("magic", "black_magic", "elemental", "fire_iii"),
    )
    assert kids == []


def test_resolve_leaf():
    t = _setup()
    n = t.resolve(
        job="BLM",
        path=("magic", "black_magic", "elemental", "fire_iii"),
    )
    assert n is not None
    assert n.command_id == "fire_iii"


def test_resolve_unknown_returns_none():
    t = _setup()
    n = t.resolve(job="BLM", path=("ghost",))
    assert n is None


def test_resolve_root():
    t = _setup()
    n = t.resolve(job="BLM", path=())
    assert n is not None
    assert n.label == "root"


def test_breadcrumb_full_path():
    t = _setup()
    crumbs = t.breadcrumb(
        job="BLM",
        path=("magic", "black_magic", "elemental", "fire_iii"),
    )
    assert crumbs == [
        "root", "Magic", "Black Magic", "Elemental", "Fire III",
    ]


def test_breadcrumb_partial():
    t = _setup()
    crumbs = t.breadcrumb(
        job="BLM", path=("magic",),
    )
    assert crumbs == ["root", "Magic"]


def test_breadcrumb_root_only():
    t = _setup()
    crumbs = t.breadcrumb(job="BLM", path=())
    assert crumbs == ["root"]


def test_breadcrumb_unknown_path_empty():
    t = _setup()
    crumbs = t.breadcrumb(job="BLM", path=("ghost",))
    assert crumbs == []


def test_per_job_independence():
    t = MenuTree()
    t.define_root(job="WHM")
    t.define_root(job="BLM")
    t.add_node(
        job="WHM", parent_path=(),
        node_id="cure_menu", label="Cures",
    )
    # BLM should not have the WHM nodes
    assert t.children(job="BLM", path=()) == []


def test_total_nodes_per_job():
    t = _setup()
    t.define_root(job="WHM")
    assert t.total_nodes(job="BLM") == 5
    assert t.total_nodes(job="WHM") == 1
