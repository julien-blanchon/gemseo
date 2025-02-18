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
from __future__ import annotations

import pytest
from gemseo.algos.design_space import DesignSpace
from gemseo.core.doe_scenario import DOEScenario
from gemseo.core.parallel_execution.disc_parallel_execution import DiscParallelExecution
from gemseo.disciplines.analytic import AnalyticDiscipline
from gemseo.disciplines.surrogate import SurrogateDiscipline
from gemseo.mlearning.regression.linreg import LinearRegressor
from gemseo.utils.repr_html import REPR_HTML_WRAPPER
from numpy import allclose
from numpy import array
from numpy import concatenate

LEARNING_SIZE = 9


@pytest.fixture
def dataset():
    """Dataset from a R^2 -> R^2 function sampled over [0,1]^2."""
    discipline = AnalyticDiscipline(
        {"y_1": "1+2*x_1+3*x_2", "y_2": "-1-2*x_1-3*x_2"}, name="func"
    )
    discipline.set_cache_policy(discipline.CacheType.MEMORY_FULL)
    design_space = DesignSpace()
    design_space.add_variable("x_1", l_b=0.0, u_b=1.0)
    design_space.add_variable("x_2", l_b=0.0, u_b=1.0)
    scenario = DOEScenario([discipline], "DisciplinaryOpt", "y_1", design_space)
    scenario.execute({"algo": "fullfact", "n_samples": LEARNING_SIZE})
    data = discipline.cache.to_dataset()
    return data


def test_constructor(dataset):
    with pytest.raises(ValueError):
        SurrogateDiscipline("LinearRegressor")
    surr = SurrogateDiscipline("LinearRegressor", dataset)
    assert surr.linearization_mode == "auto"
    surr = SurrogateDiscipline("GaussianProcessRegressor", dataset)
    assert surr.linearization_mode == "finite_differences"
    assert {"x_1", "x_2"} == set(surr.get_input_data_names())
    assert {"y_1", "y_2"} == set(surr.get_output_data_names())


def test_constructor_from_algo(dataset):
    algo = LinearRegressor(dataset)
    algo.learn()
    surr = SurrogateDiscipline(algo)
    assert surr.linearization_mode == "auto"
    assert {"x_1", "x_2"} == set(surr.get_input_data_names())
    assert {"y_1", "y_2"} == set(surr.get_output_data_names())


def test_repr_str(dataset):
    """Check the __repr__ and __str__ of a surrogate discipline."""
    surrogate_discipline = SurrogateDiscipline("LinearRegressor", dataset)
    expected = """Surrogate discipline: LinReg_func
   Dataset name: func
   Dataset size: 9
   Surrogate model: LinearRegressor
   Inputs: x_1, x_2
   Outputs: y_1, y_2
   Linearization mode: auto"""
    assert repr(surrogate_discipline) == expected
    assert str(surrogate_discipline) == "LinReg_func"


def test_execute(dataset):
    surr = SurrogateDiscipline("LinearRegressor", dataset)
    out = surr.execute()
    assert "y_1" in out
    assert "y_2" in out
    assert allclose(out["y_1"][0], 3.5, atol=1e-3)
    assert allclose(out["y_2"][0], -3.5, atol=1e-3)


def test_linearize(dataset):
    surr = SurrogateDiscipline("LinearRegressor", dataset)
    out = surr.linearize()
    assert "y_1" in out
    assert "y_2" in out
    assert "x_1" in out["y_1"]
    assert "x_2" in out["y_1"]
    assert "x_1" in out["y_2"]
    assert "x_2" in out["y_2"]
    assert allclose(out["y_1"]["x_1"][0], 2.0)
    assert allclose(out["y_1"]["x_2"][0], 3.0)
    assert allclose(out["y_2"]["x_1"][0], -2.0)
    assert allclose(out["y_2"]["x_2"][0], -3.0)


def test_parallel_execute(dataset):
    """Test the execution of the surrogate discipline in parallel."""
    surr_1 = SurrogateDiscipline("LinearRegressor", dataset)
    surr_2 = SurrogateDiscipline("LinearRegressor", dataset)

    parallel_execution = DiscParallelExecution([surr_1, surr_2], n_processes=2)
    parallel_execution.execute(
        [
            {"x_1": array([0.5]), "x_2": array([0.5])},
            {"x_1": array([1.0]), "x_2": array([1.0])},
        ]
    )

    assert allclose(
        concatenate(list(surr_1.get_outputs_by_name(["y_1", "y_2"]))),
        array([3.5, -3.5]),
        atol=1e-3,
    )
    assert allclose(
        concatenate(list(surr_2.get_outputs_by_name(["y_1", "y_2"]))),
        array([6.0, -6.0]),
        atol=1e-3,
    )


def test_serialize(dataset, tmp_wd):
    """Check the serialization of a surrogate discipline."""
    file_path = "discipline.pkl"
    discipline = SurrogateDiscipline("LinearRegressor", dataset)
    discipline.to_pickle(file_path)

    loaded_discipline = SurrogateDiscipline.from_pickle(file_path)
    loaded_discipline.execute()

    for name in discipline.local_data:
        assert allclose(discipline.local_data[name], loaded_discipline.local_data[name])


def test_repr_html(dataset):
    """Check SurrogateDiscipline._repr_html_."""
    assert SurrogateDiscipline(
        "LinearRegressor", dataset
    )._repr_html_() == REPR_HTML_WRAPPER.format(
        "Surrogate discipline: LinReg_func<br/>"
        "<ul>"
        "<li>Dataset name: func</li>"
        "<li>Dataset size: 9</li>"
        "<li>Surrogate model: LinearRegressor</li>"
        "<li>Inputs: x_1, x_2</li>"
        "<li>Outputs: y_1, y_2</li>"
        "<li>Linearization mode: auto</li>"
        "</ul>"
    )
