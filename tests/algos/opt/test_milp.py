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
from __future__ import annotations

import pytest
from gemseo.algos.design_space import DesignSpace
from gemseo.algos.opt.lib_scipy_milp import ScipyMILP
from gemseo.algos.opt.opt_factory import OptimizersFactory
from gemseo.algos.opt_problem import OptimizationProblem
from gemseo.core.mdofunctions.mdo_function import MDOFunction
from gemseo.core.mdofunctions.mdo_linear_function import MDOLinearFunction
from numpy import array


@pytest.fixture(params=[True, False])
def feasible_problem(request):
    return request.param


@pytest.fixture
def milp_problem(feasible_problem):
    """Milp problem fixture."""
    design_space = DesignSpace()
    design_space.add_variable("x", l_b=0.0, u_b=1.0, value=1.0)
    design_space.add_variable(
        "y", l_b=0.0, u_b=5.0, value=5, var_type=design_space.DesignVariableType.INTEGER
    )
    design_space.add_variable(
        "z", l_b=0.0, u_b=5.0, value=0, var_type=design_space.DesignVariableType.INTEGER
    )

    # Optimization functions
    args = ["x", "y", "z"]
    problem = OptimizationProblem(design_space, OptimizationProblem.ProblemType.LINEAR)
    problem.objective = MDOLinearFunction(
        array([1.0, 1.0, -1]), "f", MDOFunction.FunctionType.OBJ, args, -1.0
    )
    ineq_constraint = MDOLinearFunction(array([0, 0.5, -0.25]), "g", input_names=args)
    problem.add_constraint(
        ineq_constraint, 0.333, MDOFunction.ConstraintType.INEQ, positive=True
    )
    if not feasible_problem:
        problem.add_constraint(ineq_constraint, 0.0, MDOFunction.ConstraintType.INEQ)
    eq_constraint = MDOLinearFunction(array([-2.0, 1.0, 1.0]), "h", input_names=args)
    problem.add_constraint(eq_constraint, 0.0, MDOFunction.ConstraintType.EQ)
    return problem


def test_init():
    """Test solver is correctly initialized."""
    factory = OptimizersFactory()
    assert factory.is_available("ScipyMILP")
    assert isinstance(factory.create("ScipyMILP"), ScipyMILP)


@pytest.mark.parametrize(
    "algo_options",
    [
        {"node_limit": 1},
        {"presolve": False, "node_limit": 1},
        {"time_limit": 0, "node_limit": 1},
        {"mip_rel_gap": 100, "node_limit": 1},
        {"disp": True, "node_limit": 1},
        {"disp": True},
        {"eq_tolerance": 1e-6},
    ],
)
def test_solve_milp(milp_problem, feasible_problem, algo_options):
    """Test Scipy MILP solver."""
    optim_result = OptimizersFactory().execute(
        milp_problem, "Scipy_MILP", **algo_options
    )
    time_limit = algo_options.get("time_limit", 1)
    tolerance = algo_options.get("eq_tolerance", 1e-2)
    if feasible_problem and time_limit >= 1:
        assert pytest.approx(array([0.5, 1, 0.0]), abs=tolerance) == optim_result.x_opt
        assert pytest.approx(optim_result.f_opt, abs=tolerance) == 0.5
    else:
        assert pytest.approx(array([1.0, 5, 0]), abs=tolerance) == optim_result.x_opt
