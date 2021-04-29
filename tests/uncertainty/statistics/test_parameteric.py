# -*- coding: utf-8 -*-
# Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License version 3 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Contributors:
#    INITIAL AUTHORS - API and implementation and/or documentation
#        :author: Matthias De Lozzo
#    OTHER AUTHORS   - MACROSCOPIC CHANGES

from __future__ import absolute_import, division, unicode_literals

import numbers

import pytest
from numpy import array, inf, vstack
from numpy.random import exponential, lognormal, normal, rand, seed, weibull

from gemseo.core.dataset import Dataset
from gemseo.uncertainty.statistics.parametric import ParametricStatistics


@pytest.fixture(scope="module")
def random_sample():
    """This fixture is a random sample of four random variables distributed according to
    the uniform, normal, weibull and exponential probability distributions."""
    seed(0)
    n_samples = 100
    uniform_rand = rand(n_samples)
    normal_rand = normal(size=n_samples)
    weibull_rand = weibull(1.5, size=n_samples)
    exponential_rand = exponential(size=n_samples)
    data = vstack((uniform_rand, normal_rand, weibull_rand, exponential_rand)).T
    dataset = Dataset()
    dataset.set_from_array(data, ["X_0", "X_1", "X_2", "X_3"])
    theoretical_distributions = {
        "X_0": "Uniform",
        "X_1": "Normal",
        "X_2": "WeibullMin",
        "X_3": "Exponential",
    }
    tested_distributions = ["Exponential", "Normal", "Uniform"]
    return dataset, tested_distributions, theoretical_distributions


def test_distfitstats_constructor(random_sample):
    """Test constructor."""
    dataset, tested_distributions, _ = random_sample
    ParametricStatistics(dataset, tested_distributions)
    with pytest.raises(ValueError):
        ParametricStatistics(dataset, tested_distributions, fitting_criterion="dummy")


def test_distfitstats_str(random_sample):
    """Test constructor."""
    dataset, tested_distributions, _ = random_sample
    stat = ParametricStatistics(dataset, tested_distributions)
    assert "ParametricStatistics" in str(stat)


def test_distfitstats_properties(random_sample):
    """Test standard properties."""
    dataset, tested_distributions, _ = random_sample
    stats = ParametricStatistics(dataset, tested_distributions)
    assert stats.n_samples == dataset.n_samples
    assert stats.n_variables == dataset.n_variables


def test_distfitstats_getcrit(random_sample):
    """Test methods relative to criteria."""
    dataset, tested_distributions, _ = random_sample
    stats = ParametricStatistics(dataset, tested_distributions)
    criteria, is_pvalue = stats.get_criteria("X_0")
    assert not is_pvalue
    for distribution, criterion in criteria.items():
        assert distribution in tested_distributions
        assert isinstance(criterion, numbers.Number)
    stats = ParametricStatistics(
        dataset, tested_distributions, fitting_criterion="Kolmogorov"
    )
    criteria, is_pvalue = stats.get_criteria("X_0")
    assert is_pvalue
    for distribution, criterion in criteria.items():
        assert distribution in tested_distributions
        assert isinstance(criterion, numbers.Number)
    with pytest.raises(ValueError):
        stats = ParametricStatistics(dataset, ["dummy"])
    stats = ParametricStatistics(dataset, ["Normal"], fitting_criterion="Kolmogorov")
    stats = ParametricStatistics(
        dataset, ["Normal"], fitting_criterion="Kolmogorov", selection_criterion="first"
    )


def test_distfitstats_statistics(random_sample):
    """Test standard statistics."""
    dataset, tested_distributions, _ = random_sample
    stats = ParametricStatistics(dataset, tested_distributions)
    stats.compute_maximum()
    stats.compute_mean()
    stats.compute_minimum()
    stats.compute_range()
    thresh = {name: array([0.0]) for name in ["X_0", "X_1", "X_2", "X_3"]}
    stats.compute_probability(thresh, greater=True)
    stats.compute_probability(thresh, greater=False)
    stats.compute_moment(1)
    stats.compute_variance()
    stats.compute_standard_deviation()
    stats.compute_quantile(0.5)
    stats.compute_mean_std(3.0)


def test_distfitstats_plot(random_sample, tmpdir):
    """Test plot methods."""
    array, tested_distributions, _ = random_sample
    directory = str(tmpdir.mkdir("plot"))
    stats = ParametricStatistics(array, tested_distributions)
    stats.plot_criteria("X_1", save=True, show=False, directory=directory)
    stats.plot_criteria(
        "X_1", title="title", save=True, show=False, directory=directory
    )
    with pytest.raises(ValueError):
        stats.plot_criteria("dummy", save=True, show=False, directory=directory)
    stats = ParametricStatistics(
        array, tested_distributions, fitting_criterion="Kolmogorov"
    )
    stats.plot_criteria("X_1", save=True, show=False, directory=directory)


def test_distfitstats_tolint(random_sample):
    """Test tolerance_interval() method."""
    dataset, tested_distributions, _ = random_sample
    stats = ParametricStatistics(dataset, tested_distributions)
    with pytest.raises(ValueError):
        stats.compute_tolerance_interval(1.5)
    with pytest.raises(ValueError):
        stats.compute_tolerance_interval(0.1, confidence=-1.6)
    with pytest.raises(ValueError):
        stats.compute_tolerance_interval(0.1, side="dummy")
    stats = ParametricStatistics(dataset, ["ChiSquare"])
    with pytest.raises(ValueError):
        stats.compute_tolerance_interval(0.1)
    for dist in ["Normal", "Uniform", "LogNormal", "WeibullMin", "Exponential"]:
        stats = ParametricStatistics(dataset, [dist])
        stats.compute_tolerance_interval(0.1)
        stats.compute_tolerance_interval(0.1, side="both")
        stats.compute_tolerance_interval(0.1, side="upper")
        stats.compute_tolerance_interval(0.1, side="lower")


def test_distfitstats_tolint_normal():
    """Test returned values by tolerance_interval() method for Normal distribution."""
    seed(0)
    n_samples = 100
    normal_rand = normal(size=n_samples).reshape((-1, 1))
    dataset = Dataset()
    dataset.set_from_array(normal_rand)
    stats = ParametricStatistics(dataset, ["Normal"])
    limits = stats.compute_tolerance_interval(0.1, side="both")
    assert limits["x_0"][0][0] <= limits["x_0"][1][0]
    limits = stats.compute_tolerance_interval(0.1, side="upper")
    assert limits["x_0"][0][0] <= limits["x_0"][1][0]
    limits = stats.compute_tolerance_interval(0.1, side="lower")
    assert limits["x_0"][0][0] <= limits["x_0"][1][0]
    assert limits["x_0"][1][0] == inf


def test_distfitstats_tolint_uniform():
    """Test returned values by tolerance_interval() method for Uniform distribution."""
    seed(0)
    n_samples = 100
    uniform_rand = rand(n_samples).reshape((-1, 1))
    dataset = Dataset()
    dataset.set_from_array(uniform_rand)
    stats = ParametricStatistics(dataset, ["Uniform"])
    limits = stats.compute_tolerance_interval(0.1, side="both")
    assert limits["x_0"][0][0] <= limits["x_0"][1][0]
    limits = stats.compute_tolerance_interval(0.1, side="upper")
    assert limits["x_0"][0][0] <= limits["x_0"][1][0]
    limits = stats.compute_tolerance_interval(0.1, side="lower")
    assert limits["x_0"][0][0] <= limits["x_0"][1][0]
    assert limits["x_0"][1][0] == inf


def test_distfitstats_tolint_lognormal():
    """Test returned values by tolerance_interval() method for Lognormal
    distribution."""
    seed(0)
    n_samples = 100
    lognormal_rand = lognormal(size=n_samples).reshape((-1, 1))
    dataset = Dataset()
    dataset.set_from_array(lognormal_rand)
    stats = ParametricStatistics(dataset, ["LogNormal"])
    limits = stats.compute_tolerance_interval(0.1, side="both")
    assert limits["x_0"][0][0] <= limits["x_0"][1][0]
    limits = stats.compute_tolerance_interval(0.1, side="upper")
    assert limits["x_0"][0][0] <= limits["x_0"][1][0]
    limits = stats.compute_tolerance_interval(0.1, side="lower")
    assert limits["x_0"][0][0] <= limits["x_0"][1][0]
    assert limits["x_0"][1][0] == inf


def test_distfitstats_tolint_weibull(random_sample):
    """Test returned values by tolerance_interval() method for Weibull distribution."""
    seed(0)
    n_samples = 100
    import openturns as ot

    weibull_rand = array(ot.WeibullMin().getSample(n_samples)).reshape((-1, 1))
    dataset = Dataset()
    dataset.set_from_array(weibull_rand)
    stats = ParametricStatistics(dataset, ["WeibullMin"])
    limits = stats.compute_tolerance_interval(0.3, side="both")
    assert limits["x_0"][0][0] <= limits["x_0"][1][0]
    limits = stats.compute_tolerance_interval(0.1, side="upper")
    assert limits["x_0"][0][0] <= limits["x_0"][1][0]
    limits = stats.compute_tolerance_interval(0.1, side="lower")
    assert limits["x_0"][0][0] <= limits["x_0"][1][0]
    assert limits["x_0"][1][0] == inf


def test_distfitstats_tolint_exponential(random_sample):
    """Test returned values by tolerance_interval() method for Exponential
    distribution."""
    seed(0)
    n_samples = 100
    exp_rand = exponential(size=n_samples).reshape((-1, 1))
    dataset = Dataset()
    dataset.set_from_array(exp_rand)
    stats = ParametricStatistics(dataset, ["Exponential"])
    limits = stats.compute_tolerance_interval(0.1, side="both")
    assert limits["x_0"][0][0] <= limits["x_0"][1][0]
    limits = stats.compute_tolerance_interval(0.1, side="upper")
    assert limits["x_0"][0][0] <= limits["x_0"][1][0]
    limits = stats.compute_tolerance_interval(0.1, side="lower")
    assert limits["x_0"][0][0] <= limits["x_0"][1][0]
    assert limits["x_0"][1][0] == inf


def test_distfitstats_abvalue_normal():
    """Test."""
    seed(0)
    n_samples = 100
    normal_rand = normal(size=n_samples).reshape((-1, 1))
    dataset = Dataset()
    dataset.set_from_array(normal_rand)
    stats = ParametricStatistics(dataset, ["Normal"])
    assert stats.compute_a_value()["x_0"][0] <= stats.compute_b_value()["x_0"][0]


def test_distfitstats_available(random_sample):
    dataset, tested_distributions, _ = random_sample
    stat = ParametricStatistics(dataset, tested_distributions)
    assert "Normal" in ParametricStatistics.AVAILABLE_DISTRIBUTIONS
    assert "BIC" in ParametricStatistics.AVAILABLE_CRITERIA
    assert "Kolmogorov" in ParametricStatistics.AVAILABLE_SIGNIFICANCE_TESTS
    assert "Normal" in stat.get_fitting_matrix()


def test_expression():
    assert (
        ParametricStatistics.compute_expression(
            "X", "tolerance_interval", coverage=0.9, tolerance=0.99, side="lower"
        )
        == "TI[X; 0.9, lower, 0.99]"
    )
    assert (
        ParametricStatistics.compute_expression(
            "X",
            "tolerance_interval",
            show_name=True,
            coverage=0.9,
            tolerance=0.99,
            side="lower",
        )
        == "TI[X; coverage=0.9, side=lower, tolerance=0.99]"
    )
    assert ParametricStatistics.compute_expression("X", "a_value") == "Aval[X]"
    assert ParametricStatistics.compute_expression("X", "b_value") == "Bval[X]"
    assert ParametricStatistics.compute_expression("X", "maximum") == "Max[X]"
    assert ParametricStatistics.compute_expression("X", "mean") == "E[X]"
    assert ParametricStatistics.compute_expression("X", "mean_std") == "E_StD[X]"
    assert ParametricStatistics.compute_expression("X", "minimum") == "Min[X]"
    assert ParametricStatistics.compute_expression("X", "median") == "Med[X]"
    assert (
        ParametricStatistics.compute_expression("X", "percentile", order=10)
        == "p[X; 10]"
    )
    assert (
        ParametricStatistics.compute_expression("X", "probability", value=1.0)
        == "P[X>=1.0]"
    )
    assert (
        ParametricStatistics.compute_expression(
            "X", "probability", greater=False, value=1.0
        )
        == "P[X<=1.0]"
    )
    assert ParametricStatistics.compute_expression("X", "quantile") == "Q[X]"
    assert (
        ParametricStatistics.compute_expression("X", "quartile", order=1) == "q[X; 1]"
    )
    assert ParametricStatistics.compute_expression("X", "range") == "R[X]"
    assert ParametricStatistics.compute_expression("X", "variance") == "V[X]"
    assert ParametricStatistics.compute_expression("X", "moment") == "M[X]"
