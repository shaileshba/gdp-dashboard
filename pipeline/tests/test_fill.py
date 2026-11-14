import numpy as np
import pandas as pd
import pytest

from gdp_pipeline import fill


def test_interpolate_log_is_constant_growth_between_observations():
    wide = pd.DataFrame({"A": [100.0, np.nan, np.nan, 800.0]}, index=[2000, 2001, 2002, 2003])
    vals, flags = fill.interpolate_log(wide)
    assert vals["A"].tolist() == pytest.approx([100, 200, 400, 800])
    assert flags["A"].tolist() == ["observed", "interpolated", "interpolated", "observed"]


def test_interpolate_respects_uneven_year_spacing():
    wide = pd.DataFrame({"A": [100.0, np.nan, 400.0]}, index=[1500, 1600, 1700])
    vals, _ = fill.interpolate_log(wide)
    assert vals.loc[1600, "A"] == pytest.approx(200)


def test_interpolate_does_not_fill_outside_observed_span():
    wide = pd.DataFrame({"A": [np.nan, 100.0, np.nan]}, index=[1, 2, 3])
    vals, flags = fill.interpolate_log(wide)
    assert np.isnan(vals.loc[1, "A"]) and np.isnan(vals.loc[3, "A"])
    assert pd.isna(flags.loc[1, "A"])


def test_extend_backward_and_forward_follow_reference_growth():
    years = [1, 2, 3, 4, 5]
    v = pd.Series([np.nan, np.nan, 100.0, np.nan, np.nan], index=years)
    f = pd.Series([None, None, "observed", None, None], index=years, dtype=object)
    g = pd.Series(np.log(2.0), index=years)  # reference doubles every year
    out_v, out_f = fill.extend_with_growth(v, f, g, "regional")
    assert out_v.tolist() == pytest.approx([25, 50, 100, 200, 400])
    assert out_f.tolist() == ["regional", "regional", "observed", "regional", "regional"]


def test_extend_with_per_year_labels_and_unknown_growth_held_flat():
    years = [1, 2, 3]
    v = pd.Series([np.nan, np.nan, 100.0], index=years)
    f = pd.Series([None, None, "observed"], index=years, dtype=object)
    g = pd.Series([np.nan, np.nan, np.log(2.0)], index=years)
    labels = pd.Series(["regional", "regional", "parent"], index=years)
    out_v, out_f = fill.extend_with_growth(v, f, g, labels)
    assert out_v.tolist() == pytest.approx([50, 50, 100])  # year-2 growth unknown -> flat
    assert out_f.tolist() == ["regional", "parent", "observed"]


def test_group_median_growth():
    wide = pd.DataFrame({"A": [100.0, 110.0], "B": [100.0, 130.0], "C": [100.0, 200.0]}, index=[1, 2])
    groups = pd.Series({"A": "x", "B": "x", "C": "y"})
    med = fill.group_median_growth(wide, groups, min_countries=1)
    assert med.loc[2, "x"] == pytest.approx(np.median([np.log(1.1), np.log(1.3)]))
    assert med.loc[2, "y"] == pytest.approx(np.log(2.0))


def test_group_median_growth_needs_enough_countries():
    wide = pd.DataFrame({"A": [100.0, 110.0], "B": [100.0, 130.0], "C": [100.0, 200.0]}, index=[1, 2])
    groups = pd.Series({"A": "x", "B": "x", "C": "y"})
    med = fill.group_median_growth(wide, groups, min_countries=2)
    assert not np.isnan(med.loc[2, "x"])
    assert np.isnan(med.loc[2, "y"])  # only one country in group y


def test_calibrate_scales_only_estimates_and_fades_near_real_data():
    years = list(range(1900, 1911))
    # Country A observed throughout (fixed at 100). B estimated before 1910, observed in 1910.
    vals = pd.DataFrame({"A": 100.0, "B": 50.0}, index=years)
    flags = pd.DataFrame({"A": "observed", "B": "regional"}, index=years)
    flags.loc[1910, "B"] = "observed"
    target = pd.DataFrame({"R": [np.nan] * 11}, index=years)
    target.loc[1900, "R"] = 200.0  # B must double in 1900 to hit the total
    groups = pd.Series({"A": "R", "B": "R"})
    out, factors = fill.calibrate_to_totals(vals, flags, groups, target, fade_years=10)
    assert (out["A"] == 100).all()
    assert out.loc[1900, "B"] == pytest.approx(100)  # 10 years from real data: full factor
    assert out.loc[1905, "B"] == pytest.approx(50 * 2 ** 0.5)  # halfway: half the factor (in logs)
    assert out.loc[1910, "B"] == 50  # real data untouched
    assert factors.loc[1905, "R"] == pytest.approx(2.0)  # held flat beyond the benchmark


def test_worst_flag():
    a = pd.Series(["observed", "regional", "interpolated"])
    b = pd.Series(["parent", "observed", "interpolated"])
    assert fill.worst_flag(a, b).tolist() == ["parent", "regional", "interpolated"]
