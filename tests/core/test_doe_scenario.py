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
#      :author: Francois Gallard, Gilberto Ruiz
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
from __future__ import annotations

import pickle

import pytest
from gemseo import create_discipline
from gemseo import create_scenario
from gemseo import MDODiscipline
from gemseo.algos.design_space import DesignSpace
from gemseo.core.doe_scenario import DOEScenario
from gemseo.core.grammars.errors import InvalidDataError
from gemseo.disciplines.analytic import AnalyticDiscipline
from gemseo.problems.sellar.sellar_design_space import SellarDesignSpace
from gemseo.problems.sobieski._disciplines_sg import SobieskiAerodynamicsSG
from gemseo.problems.sobieski._disciplines_sg import SobieskiMissionSG
from gemseo.problems.sobieski._disciplines_sg import SobieskiPropulsionSG
from gemseo.problems.sobieski._disciplines_sg import SobieskiStructureSG
from gemseo.problems.sobieski.core.problem import SobieskiProblem
from gemseo.problems.sobieski.disciplines import SobieskiAerodynamics
from gemseo.problems.sobieski.disciplines import SobieskiMission
from gemseo.problems.sobieski.disciplines import SobieskiPropulsion
from gemseo.problems.sobieski.disciplines import SobieskiStructure
from numpy import array
from numpy import ndarray


def build_mdo_scenario(
    formulation: str,
    grammar_type: MDODiscipline.GrammarType = DOEScenario.GrammarType.JSON,
) -> DOEScenario:
    """Build the DOE scenario for SSBJ.

    Args:
        formulation: The name of the DOE scenario formulation.
        grammar_type: The grammar type.

    Returns:
        The DOE scenario.
    """
    if grammar_type == DOEScenario.GrammarType.JSON:
        disciplines = [
            SobieskiPropulsion(),
            SobieskiAerodynamics(),
            SobieskiMission(),
            SobieskiStructure(),
        ]
    elif grammar_type == DOEScenario.GrammarType.SIMPLE:
        disciplines = [
            SobieskiPropulsionSG(),
            SobieskiAerodynamicsSG(),
            SobieskiMissionSG(),
            SobieskiStructureSG(),
        ]

    design_space = SobieskiProblem().design_space
    scenario = DOEScenario(
        disciplines,
        formulation=formulation,
        objective_name="y_4",
        design_space=design_space,
        grammar_type=grammar_type,
        maximize_objective=True,
    )
    return scenario


@pytest.fixture()
def mdf_variable_grammar_doe_scenario(request):
    """Return a DOEScenario with MDF formulation and custom grammar.

    Args:
        request: An auxiliary variable to retrieve the grammar type with
            pytest.mark.parametrize and the option `indirect=True`.
    """
    return build_mdo_scenario("MDF", request.param)


@pytest.mark.usefixtures("tmp_wd")
@pytest.mark.skip_under_windows
def test_parallel_doe_hdf_cache(caplog):
    disciplines = create_discipline(
        [
            "SobieskiStructure",
            "SobieskiPropulsion",
            "SobieskiAerodynamics",
            "SobieskiMission",
        ]
    )
    path = "cache.h5"
    for disc in disciplines:
        disc.set_cache_policy(disc.CacheType.HDF5, cache_hdf_file=path)

    scenario = create_scenario(
        disciplines,
        "DisciplinaryOpt",
        "y_4",
        SobieskiProblem().design_space,
        maximize_objective=True,
        scenario_type="DOE",
    )

    n_samples = 10
    input_data = {
        "n_samples": n_samples,
        "algo": "lhs",
        "algo_options": {"n_processes": 2},
    }
    scenario.execute(input_data)
    scenario.print_execution_metrics()
    assert len(scenario.formulation.opt_problem.database) == n_samples
    for disc in disciplines:
        assert len(disc.cache) == n_samples

    input_data = {
        "n_samples": n_samples,
        "algo": "lhs",
        "algo_options": {"n_processes": 2, "n_samples": n_samples},
    }
    scenario.execute(input_data)
    expected_log = "Double definition of algorithm option n_samples, keeping value: {}."
    assert expected_log.format(n_samples) in caplog.text


@pytest.mark.parametrize(
    "mdf_variable_grammar_doe_scenario",
    [DOEScenario.GrammarType.SIMPLE, DOEScenario.GrammarType.JSON],
    indirect=True,
)
def test_doe_scenario(mdf_variable_grammar_doe_scenario):
    """Test the execution of a DOEScenario with different grammars.

    Args:
        mdf_variable_grammar_doe_scenario: The DOEScenario.
    """
    n_samples = 10
    input_data = {
        "n_samples": n_samples,
        "algo": "lhs",
        "algo_options": {"n_processes": 1},
    }
    mdf_variable_grammar_doe_scenario.execute(input_data)
    mdf_variable_grammar_doe_scenario.print_execution_metrics()
    assert (
        len(mdf_variable_grammar_doe_scenario.formulation.opt_problem.database)
        == n_samples
    )


@pytest.fixture(scope="module")
def unit_design_space():
    """A unit design space with x as variable."""
    design_space = DesignSpace()
    design_space.add_variable("x", l_b=0.0, u_b=1.0, value=0.5)
    return design_space


@pytest.fixture(scope="module")
def double_discipline():
    """An analytic discipline that doubles its input."""
    return AnalyticDiscipline({"y": "2*x"}, name="func")


@pytest.fixture
def doe_scenario(unit_design_space, double_discipline) -> DOEScenario:
    """A simple DOE scenario not yet executed.

    Args:
        unit_design_space: A unit design space with x as a variable.
        double_discipline: An analytic discipline that doubles its input.

    Minimize y=func(x)=2x over [0,1].
    """
    return DOEScenario(
        [double_discipline],
        "DisciplinaryOpt",
        "y",
        unit_design_space,
    )


def test_warning_when_missing_option(caplog, doe_scenario):
    """Check that a warning is correctly logged when an option is unknown.

    Args:
        doe_scenario: A simple DOE scenario.
    """
    doe_scenario.execute(
        {
            "algo": "CustomDOE",
            "algo_options": {"samples": array([[1.0]]), "unknown_option": 1},
        }
    )
    expected_log = "Driver CustomDOE has no option {}, option is ignored."
    assert expected_log.format("n_samples") not in caplog.text
    assert expected_log.format("unknown_option") in caplog.text


def f_sellar_1(x_local: float, y_2: float, x_shared: ndarray) -> float:
    """Function for discipline 1."""
    if x_local == 0.0:
        raise ValueError("Undefined")

    y_1 = (x_shared[0] ** 2 + x_shared[1] + x_local - 0.2 * y_2) ** 0.5
    return y_1


@pytest.mark.parametrize("use_threading", [True, False])
def test_exception_mda_jacobi(caplog, use_threading):
    """Check that a DOE scenario does not crash with a ValueError and MDAJacobi.

    Args:
        caplog: Fixture to access and control log capturing.
        use_threading: Whether to use threading in the MDAJacobi.
    """
    sellar1 = create_discipline("AutoPyDiscipline", py_func=f_sellar_1)
    sellar2 = create_discipline("Sellar2")
    sellarsystem = create_discipline("SellarSystem")
    disciplines = [sellar1, sellar2, sellarsystem]

    scenario = DOEScenario(
        disciplines,
        "MDF",
        "obj",
        main_mda_name="MDAChain",
        inner_mda_name="MDAJacobi",
        use_threading=use_threading,
        n_processes=2,
        design_space=SellarDesignSpace("float64"),
    )
    scenario.execute(
        {
            "algo": "CustomDOE",
            "algo_options": {"samples": array([[0.0, -10.0, 0.0]])},
        }
    )

    assert sellarsystem.n_calls == 0
    assert "Undefined" in caplog.text


def test_other_exceptions_caught(caplog):
    """Check that exceptions that are not ValueErrors are not re-raised.

    Args:
        caplog: Fixture to access and control log capturing.
    """
    discipline = AnalyticDiscipline({"y": "1/x"}, name="func")
    design_space = DesignSpace()
    design_space.add_variable("x", l_b=0.0, u_b=1.0)
    scenario = DOEScenario(
        [discipline], "MDF", "y", design_space, main_mda_name="MDAJacobi"
    )
    with pytest.raises(InvalidDataError):
        scenario.execute(
            {
                "algo": "CustomDOE",
                "algo_options": {
                    "samples": array([[0.0]]),
                },
            }
        )
    assert "0.0 cannot be raised to a negative power" in caplog.text


def test_export_to_dataset_with_repeated_inputs():
    """Check the export of the database with repeated inputs."""
    discipline = AnalyticDiscipline({"obj": "2*dv"}, "f")
    design_space = DesignSpace()
    design_space.add_variable("dv")
    scenario = DOEScenario([discipline], "DisciplinaryOpt", "obj", design_space)
    samples = array([[1.0], [2.0], [1.0]])
    scenario.execute({"algo": "CustomDOE", "algo_options": {"samples": samples}})
    dataset = scenario.to_dataset()
    assert (dataset.get_view(variable_names="dv").to_numpy() == samples).all()
    assert (dataset.get_view(variable_names="obj").to_numpy() == samples * 2).all()


def test_export_to_dataset_normalized_integers():
    """Check the export of the database with normalized integers."""
    discipline = AnalyticDiscipline({"obj": "2*dv"}, "f")
    design_space = DesignSpace()
    design_space.add_variable("dv", var_type="integer", l_b=1, u_b=10)
    scenario = DOEScenario([discipline], "DisciplinaryOpt", "obj", design_space)
    samples = array([[1], [2], [10]])
    scenario.execute({"algo": "CustomDOE", "algo_options": {"samples": samples}})
    dataset = scenario.to_dataset()
    assert (dataset.get_view(variable_names="dv").to_numpy() == samples).all()
    assert (dataset.get_view(variable_names="obj").to_numpy() == samples * 2).all()


def test_lib_serialization(tmp_wd, doe_scenario):
    """Test the serialization of a DOEScenario with an instantiated DOELibrary.

    Args:
        tmp_wd: Fixture to move into a temporary work directory.
        doe_scenario: A simple DOE scenario.
    """
    doe_scenario.execute(
        {
            "algo": "CustomDOE",
            "algo_options": {"samples": array([[1.0]])},
        }
    )

    doe_scenario.formulation.opt_problem.reset(database=False, design_space=False)

    with open("doe.pkl", "wb") as file:
        pickle.dump(doe_scenario, file)

    with open("doe.pkl", "rb") as file:
        pickled_scenario = pickle.load(file)

    assert pickled_scenario._lib is None

    pickled_scenario.execute(
        {
            "algo": "CustomDOE",
            "algo_options": {"samples": array([[0.5]])},
        }
    )

    assert pickled_scenario._lib.internal_algo_name == "CustomDOE"
    assert pickled_scenario.formulation.opt_problem.database.get_function_value(
        "y", array([0.5])
    ) == array([1.0])
    assert pickled_scenario.formulation.opt_problem.database.get_function_value(
        "y", array([1.0])
    ) == array([2.0])


other_doe_scenario = doe_scenario


@pytest.mark.parametrize(
    "samples_1,samples_2,reset_iteration_counters,expected",
    [
        (array([[0.5]]), array([[0.25], [0.75]]), True, 3),
        (array([[0.5]]), array([[0.25], [0.75]]), False, 2),
        (array([[0.5]]), array([[0.25]]), True, 2),
        (array([[0.5]]), array([[0.25]]), False, 1),
        (array([[0.5], [0.75]]), array([[0.25]]), True, 3),
        (array([[0.5], [0.75]]), array([[0.25]]), False, 2),
    ],
)
def test_partial_execution_from_backup(
    tmp_wd,
    doe_scenario,
    other_doe_scenario,
    samples_1,
    samples_2,
    reset_iteration_counters,
    expected,
):
    """Test the execution of a DOEScenario from a backup.

    Args:
        doe_scenario: A simple DOE scenario.
        other_doe_scenario: A different instance of a simple DOE scenario.
        samples_1: The samples for the first execution.
        samples_2: The samples for the second execution.
        reset_iteration_counters: Whether to reset the iteration counters from the
            previous execution of the scenario to 0 before executing it again.
        expected: The expected database length.
    """
    doe_scenario.set_optimization_history_backup("backup.h5")
    doe_scenario.execute({"algo": "CustomDOE", "algo_options": {"samples": samples_1}})
    other_doe_scenario.set_optimization_history_backup("backup.h5", pre_load=True)
    other_doe_scenario.execute(
        {
            "algo": "CustomDOE",
            "algo_options": {
                "samples": samples_2,
                "reset_iteration_counters": reset_iteration_counters,
            },
        }
    )
    assert len(other_doe_scenario.formulation.opt_problem.database) == expected


def test_scenario_without_initial_design_value():
    """Check that a DOEScenario can work without initial design value."""
    design_space = DesignSpace()
    design_space.add_variable("x", l_b=0.0, u_b=1.0)
    discipline = AnalyticDiscipline({"y": "x"})
    discipline.default_inputs = {}
    scenario = DOEScenario([discipline], "MDF", "y", design_space)
    scenario.execute({"algo": "lhs", "n_samples": 3})
    assert len(scenario.formulation.opt_problem.database) == 3
