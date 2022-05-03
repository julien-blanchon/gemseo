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
#        :author: Francois Gallard
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
import numpy as np
import pytest
from gemseo.algos.design_space import DesignSpace
from gemseo.core.mdo_scenario import MDOScenario
from gemseo.core.mdofunctions.consistency_constraint import ConsistencyCstr
from gemseo.disciplines.analytic import AnalyticDiscipline
from gemseo.formulations.idf import IDF
from gemseo.problems.sobieski.core.problem import SobieskiProblem
from gemseo.problems.sobieski.disciplines import SobieskiAerodynamics
from gemseo.problems.sobieski.disciplines import SobieskiMission
from gemseo.problems.sobieski.disciplines import SobieskiPropulsion
from gemseo.problems.sobieski.disciplines import SobieskiStructure

from .formulations_basetest import FakeDiscipline


def build_and_run_idf_scenario_with_constraints(
    algo,
    linearize=False,
    dtype="complex128",
    normalize_cstr=True,
    eq_tolerance=1e-4,
    ineq_tolerance=1e-3,
    remove_coupl_from_ds=False,
    parallel_exec=True,
    use_threading=True,
):
    """
    :param algo: param linearize:  (Default value = False)
    :param dtype: Default value = "complex128")
    :param linearize:  (Default value = False)
    """
    disciplines = [
        SobieskiStructure(dtype),
        SobieskiPropulsion(dtype),
        SobieskiAerodynamics(dtype),
        SobieskiMission(dtype),
    ]
    design_space = SobieskiProblem().design_space
    if dtype == "complex128":
        design_space.to_complex()
    if remove_coupl_from_ds:
        for var in design_space.variables_names:
            if var.startswith("y_"):
                design_space.remove_variable(var)

    scenario = MDOScenario(
        disciplines,
        "IDF",
        "y_4",
        design_space=design_space,
        normalize_constraints=normalize_cstr,
        parallel_exec=parallel_exec,
        use_threading=use_threading,
        maximize_objective=True,
        start_at_equilibrium=True,
    )
    if linearize:
        scenario.set_differentiation_method("user")
    else:
        scenario.set_differentiation_method("complex_step", 1e-30)
    # Set the design constraints
    for c_name in ["g_1", "g_2", "g_3"]:
        scenario.add_constraint(c_name, "ineq")

    run_inputs = {
        "max_iter": 50,
        "algo": algo,
        "algo_options": {
            "eq_tolerance": eq_tolerance,
            "ineq_tolerance": ineq_tolerance,
        },
    }
    opt_pb = scenario.formulation.opt_problem

    scenario.iteration = 0
    scenario.stores = 0

    def callback_iter(x_vect=None):
        scenario.iteration += 1

    def callback_store(x_vect=None):
        scenario.stores += 1

    opt_pb.add_callback(callback_iter)
    opt_pb.add_callback(callback_store, each_new_iter=False, each_store=True)

    scenario.execute(run_inputs)
    assert (
        scenario.iteration == len(opt_pb.database)
        or scenario.iteration == len(opt_pb.database) + 1
    )
    assert scenario.stores > len(opt_pb.database)

    obj_opt = scenario.optimization_result.f_opt
    is_feasible = scenario.optimization_result.is_feasible
    return -obj_opt, is_feasible


def test_build_func_from_disc():
    """"""
    pb = SobieskiProblem("complex128")
    disciplines = [
        SobieskiMission("complex128"),
        SobieskiAerodynamics("complex128"),
        SobieskiPropulsion("complex128"),
        SobieskiStructure("complex128"),
    ]
    idf = IDF(disciplines, "y_4", pb.design_space)
    x_names = idf.get_optim_variables_names()
    x_dict = pb.get_default_inputs(x_names)
    x_vect = np.concatenate([x_dict[k] for k in x_names])

    for c_name in ["g_1", "g_2", "g_3"]:
        idf.add_constraint(c_name, constraint_type="ineq")
    opt = idf.opt_problem
    opt.objective.check_grad(x_vect, "ComplexStep", 1e-30, error_max=1e-4)
    for cst in opt.constraints:
        cst.check_grad(x_vect, "ComplexStep", 1e-30, error_max=1e-4)

    for func_name in list(pb.get_default_inputs().keys()):
        if func_name.startswith("Y"):
            func = idf._build_func_from_outputs([func_name])
            func.check_grad(x_vect, "ComplexStep", 1e-30, error_max=1e-4)

    for coupl in idf.coupling_structure.strong_couplings():
        func = ConsistencyCstr([coupl], idf)
        func.check_grad(x_vect, "ComplexStep", 1e-30, error_max=1e-4)


def test_exec_idf_cstr_complex_step():
    """"""
    from gemseo.api import configure_logger

    configure_logger()
    obj_opt, is_feasible = build_and_run_idf_scenario_with_constraints(
        "SLSQP",
        linearize=False,
        dtype="complex128",
        normalize_cstr=True,
        eq_tolerance=1e-4,
        ineq_tolerance=1e-4,
    )

    assert 3962.0 < obj_opt < 3966.0
    assert is_feasible


def test_exec_idf_scipy_slsqp_cstr():
    """"""
    obj_opt, _ = build_and_run_idf_scenario_with_constraints(
        "SLSQP",
        linearize=True,
        dtype="float64",
        normalize_cstr=False,
    )

    assert 3962.0 < obj_opt
    assert obj_opt < 3965.0


def test_exec_idf_scipy_slsqp_norm_cstr():
    obj_opt, is_feasible = build_and_run_idf_scenario_with_constraints(
        "SLSQP", linearize=True, dtype="float64", normalize_cstr=True
    )

    assert 3962.0 < obj_opt
    assert obj_opt < 3965.0
    assert is_feasible


def test_exec_idf_scipy_slsqp_norm_cstr_par_thread():
    obj_opt, is_feasible = build_and_run_idf_scenario_with_constraints(
        "SLSQP",
        linearize=True,
        dtype="float64",
        normalize_cstr=True,
        parallel_exec=True,
        use_threading=True,
    )

    assert 3962.0 < obj_opt
    assert obj_opt < 3965.0
    assert is_feasible


@pytest.mark.skip_under_windows
def test_exec_idf_scipy_slsqp_norm_cstr_par_process():
    obj_opt, is_feasible = build_and_run_idf_scenario_with_constraints(
        "SLSQP",
        linearize=True,
        dtype="float64",
        normalize_cstr=True,
        parallel_exec=True,
        use_threading=False,
    )

    assert 3962.0 < obj_opt
    assert obj_opt < 3965.0
    assert is_feasible


def test_fail_idf_no_coupl():
    """"""
    with pytest.raises(Exception):
        build_and_run_idf_scenario_with_constraints(
            "SLSQP",
            linearize=False,
            dtype="float64",
            normalize_cstr=True,
            remove_coupl_from_ds=True,
        )


def test_expected_workflow():
    """"""
    disc1 = FakeDiscipline("d1")
    disc2 = FakeDiscipline("d2")
    disc3 = FakeDiscipline("d3")
    idf = IDF([disc1, disc2, disc3], "d3_y", DesignSpace())
    expected = "(d1(None), d2(None), d3(None), )"
    assert str(idf.get_expected_workflow()) == expected


def test_expected_dataflow():
    """"""
    disc1 = FakeDiscipline("d1")
    disc2 = FakeDiscipline("d2")
    disc3 = FakeDiscipline("d3")
    idf = IDF([disc1, disc2, disc3], "d3_y", DesignSpace())
    assert idf.get_expected_dataflow() == []


def test_idf_start_equilibrium():
    """Initial value of coupling variables set at equilibrium."""
    disciplines = [
        SobieskiStructure(),
        SobieskiPropulsion(),
        SobieskiAerodynamics(),
        SobieskiMission(),
    ]
    design_space = SobieskiProblem().design_space
    idf = IDF(disciplines, "y_4", design_space, start_at_equilibrium=True)
    coupling_names = [
        "y_12",
        "y_14",
        "y_21",
        "y_23",
        "y_24",
        "y_31",
        "y_32",
        "y_34",
    ]
    current_couplings = idf.design_space.get_current_x_dict()
    ref_couplings = SobieskiProblem().get_default_inputs_equilibrium()
    for coupling_name in coupling_names:
        residual = np.linalg.norm(
            current_couplings[coupling_name] - ref_couplings[coupling_name]
        ) / np.linalg.norm(ref_couplings[coupling_name])
        assert residual < 1e-3


def test_grammar_type():
    """Check that the grammar type is correctly used."""
    discipline = AnalyticDiscipline({"y": "x"})
    design_space = DesignSpace()
    design_space.add_variable("x")
    grammar_type = discipline.SIMPLE_GRAMMAR_TYPE
    formulation = IDF(
        [discipline], "y", design_space, grammar_type=grammar_type, parallel_exec=True
    )
    assert formulation._parallel_exec.grammar_type == grammar_type
