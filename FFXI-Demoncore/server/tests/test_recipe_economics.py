"""Tests for recipe_economics."""
from __future__ import annotations

from server.recipe_economics import RecipeEconomics


def test_seed_publish_cost_happy():
    e = RecipeEconomics()
    out = e.seed_publish_cost(
        recipe_id="rec_1",
        mat_costs=[("dough", 100), ("cheese", 200)],
        output_value=500, snap_at=1000,
    )
    assert out is True


def test_seed_blank_recipe_blocked():
    e = RecipeEconomics()
    assert e.seed_publish_cost(
        recipe_id="",
        mat_costs=[("dough", 100)],
        output_value=500, snap_at=1000,
    ) is False


def test_seed_negative_cost_blocked():
    e = RecipeEconomics()
    assert e.seed_publish_cost(
        recipe_id="rec_1",
        mat_costs=[("dough", -1)],
        output_value=500, snap_at=1000,
    ) is False


def test_seed_negative_output_blocked():
    e = RecipeEconomics()
    assert e.seed_publish_cost(
        recipe_id="rec_1",
        mat_costs=[("dough", 100)],
        output_value=-10, snap_at=1000,
    ) is False


def test_seed_idempotent_first_wins():
    e = RecipeEconomics()
    e.seed_publish_cost(
        recipe_id="rec_1",
        mat_costs=[("dough", 100)],
        output_value=500, snap_at=1000,
    )
    out = e.seed_publish_cost(
        recipe_id="rec_1",
        mat_costs=[("dough", 9999)],
        output_value=99999, snap_at=2000,
    )
    assert out is False


def test_record_mat_price_happy():
    e = RecipeEconomics()
    out = e.record_mat_price(
        item_id="dough", gil=120, sampled_at=2000,
    )
    assert out is True
    assert e.latest_mat_price(item_id="dough") == 120


def test_record_mat_price_blank_blocked():
    e = RecipeEconomics()
    assert e.record_mat_price(
        item_id="", gil=120, sampled_at=2000,
    ) is False


def test_record_mat_price_negative_blocked():
    e = RecipeEconomics()
    assert e.record_mat_price(
        item_id="dough", gil=-1, sampled_at=2000,
    ) is False


def test_record_mat_price_older_sample_rejected():
    e = RecipeEconomics()
    e.record_mat_price(
        item_id="dough", gil=120, sampled_at=2000,
    )
    out = e.record_mat_price(
        item_id="dough", gil=110, sampled_at=1000,
    )
    assert out is False
    assert e.latest_mat_price(item_id="dough") == 120


def test_latest_mat_price_unknown_zero():
    e = RecipeEconomics()
    assert e.latest_mat_price(item_id="ghost") == 0


def test_record_output_price_overwrites_with_newer():
    e = RecipeEconomics()
    e.record_output_price(
        recipe_id="rec_1", gil=500, sampled_at=2000,
    )
    out = e.record_output_price(
        recipe_id="rec_1", gil=600, sampled_at=3000,
    )
    assert out is True


def test_record_output_price_older_blocked():
    e = RecipeEconomics()
    e.record_output_price(
        recipe_id="rec_1", gil=500, sampled_at=2000,
    )
    out = e.record_output_price(
        recipe_id="rec_1", gil=400, sampled_at=1000,
    )
    assert out is False


def test_report_unknown_recipe_zero():
    e = RecipeEconomics()
    r = e.report(recipe_id="ghost", materials=["dough"])
    assert r.publish_cost == 0
    assert r.has_full_cost_data is False


def test_report_full_data():
    e = RecipeEconomics()
    e.seed_publish_cost(
        recipe_id="rec_1",
        mat_costs=[("dough", 100), ("cheese", 200)],
        output_value=500, snap_at=1000,
    )
    e.record_mat_price(
        item_id="dough", gil=150, sampled_at=2000,
    )
    e.record_mat_price(
        item_id="cheese", gil=250, sampled_at=2000,
    )
    e.record_output_price(
        recipe_id="rec_1", gil=600, sampled_at=2000,
    )
    r = e.report(
        recipe_id="rec_1",
        materials=["dough", "cheese"],
    )
    assert r.publish_cost == 300
    assert r.current_cost == 400
    assert r.current_output_value == 600
    assert r.profit_margin == 200
    assert r.has_full_cost_data is True


def test_report_drift_pct():
    e = RecipeEconomics()
    e.seed_publish_cost(
        recipe_id="rec_1",
        mat_costs=[("dough", 100)],
        output_value=500, snap_at=1000,
    )
    e.record_mat_price(
        item_id="dough", gil=200, sampled_at=2000,
    )
    r = e.report(recipe_id="rec_1", materials=["dough"])
    # cost doubled — drift is +1.0 (+100%)
    assert r.drift_pct == 1.0


def test_report_partial_data_flag_false():
    e = RecipeEconomics()
    e.seed_publish_cost(
        recipe_id="rec_1",
        mat_costs=[("dough", 100), ("cheese", 200)],
        output_value=500, snap_at=1000,
    )
    e.record_mat_price(
        item_id="dough", gil=150, sampled_at=2000,
    )
    r = e.report(
        recipe_id="rec_1",
        materials=["dough", "cheese"],
    )
    assert r.has_full_cost_data is False
    # cheese unsampled; current_cost only counts dough
    assert r.current_cost == 150


def test_report_uses_publish_output_when_no_sample():
    e = RecipeEconomics()
    e.seed_publish_cost(
        recipe_id="rec_1",
        mat_costs=[("dough", 100)],
        output_value=500, snap_at=1000,
    )
    e.record_mat_price(
        item_id="dough", gil=100, sampled_at=2000,
    )
    r = e.report(recipe_id="rec_1", materials=["dough"])
    # No output sample → falls back to publish snapshot value
    assert r.current_output_value == 500


def test_report_zero_publish_cost_drift_zero():
    e = RecipeEconomics()
    e.seed_publish_cost(
        recipe_id="rec_1",
        mat_costs=[],   # empty (someone got it free)
        output_value=500, snap_at=1000,
    )
    r = e.report(recipe_id="rec_1", materials=[])
    assert r.drift_pct == 0.0


def test_total_recipes():
    e = RecipeEconomics()
    e.seed_publish_cost(
        recipe_id="rec_1",
        mat_costs=[], output_value=0, snap_at=1000,
    )
    e.seed_publish_cost(
        recipe_id="rec_2",
        mat_costs=[], output_value=0, snap_at=2000,
    )
    assert e.total_recipes() == 2
