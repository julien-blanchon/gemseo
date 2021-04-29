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
#        :author: Francois Gallard
#    OTHER AUTHORS   - MACROSCOPIC CHANGES

from __future__ import absolute_import, division, print_function, unicode_literals

import unittest
from copy import deepcopy

from numpy import all as np_all
from numpy import allclose, array, matmul, ones, zeros, zeros_like

from gemseo.core.chain import MDOChain
from gemseo.core.function import MDOFunction, MDOFunctionGenerator
from gemseo.core.mdo_scenario import (
    MDOObjScenarioAdapter,
    MDOScenario,
    MDOScenarioAdapter,
)
from gemseo.problems.sobieski.core import SobieskiProblem
from gemseo.problems.sobieski.wrappers import (
    SobieskiAerodynamics,
    SobieskiMission,
    SobieskiPropulsion,
    SobieskiStructure,
)
from gemseo.utils.derivatives_approx import DisciplineJacApprox


class TestMDOScenarioAdapter(unittest.TestCase):
    """"""

    def create_design_space(self):
        """"""
        return SobieskiProblem().read_design_space()

    def get_sobieski_scenario(self):
        """"""
        disciplines = [
            SobieskiPropulsion(),
            SobieskiAerodynamics(),
            SobieskiMission(),
            SobieskiStructure(),
        ]
        design_space = self.create_design_space()
        design_space.filter(["x_1", "x_2", "x_3"])
        scenario = MDOScenario(
            disciplines,
            formulation="MDF",
            objective_name="y_4",
            design_space=design_space,
            maximize_objective=True,
        )
        scenario.default_inputs = {"max_iter": 35, "algo": "L-BFGS-B"}

        return scenario

    def test_adapter(self):
        """"""
        inputs = ["x_shared"]
        outputs = ["y_4"]
        scenario = self.get_sobieski_scenario()
        adapter = MDOScenarioAdapter(scenario, inputs, outputs)
        gen = MDOFunctionGenerator(adapter)
        func = gen.get_function(inputs, outputs)
        x_shared = array([0.06000319728113519, 60000, 1.4, 2.5, 70, 1500])
        f_x1 = func(x_shared)
        f_x2 = func(x_shared)
        assert f_x1 == f_x2
        x_shared = array([0.09, 60000, 1.4, 2.5, 70, 1500])

        f_x3 = func(x_shared)
        assert f_x3 > 4947.0

    def test_adapter_miss_dvs(self):
        inputs = ["x_shared"]
        outputs = ["y_4", "missing_dv"]
        scenario = self.get_sobieski_scenario()
        scenario.design_space.add_variable("missing_dv")
        MDOScenarioAdapter(scenario, inputs, outputs)

    def test_adapter_resetx0(self):
        """"""
        inputs = ["x_shared"]
        outputs = ["y_4"]
        scenario = self.get_sobieski_scenario()
        adapter = MDOScenarioAdapter(
            scenario, inputs, outputs, reset_x0_before_opt=True
        )
        x0_dict = adapter.scenario.design_space.get_current_x_dict()
        x0_list = adapter.scenario.design_space.dict_to_array(x0_dict)
        adapter.execute()
        x_shared = array([0.06000319728113519, 60000, 1.4, 2.5, 70, 1500])
        adapter.default_inputs["x_shared"] = x_shared
        adapter.execute()
        x_list = adapter.scenario.formulation.opt_problem.database.get_x_by_iter(0)
        assert np_all(x_list == x0_list)

        scenario = self.get_sobieski_scenario()
        adapter = MDOScenarioAdapter(
            scenario, inputs, outputs, reset_x0_before_opt=False
        )
        adapter.execute()
        x1_dict = adapter.scenario.design_space.get_current_x_dict()
        x1_list = adapter.scenario.design_space.dict_to_array(x1_dict)
        adapter.default_inputs["x_shared"] = x_shared
        adapter.execute()
        x_list = adapter.scenario.formulation.opt_problem.database.get_x_by_iter(0)
        # compare current initial point to current_x after last optim
        assert np_all(x_list == x1_list)

    def test_adapter_set_bounds(self):

        scenario = self.get_sobieski_scenario()
        inputs = ["x_shared"]
        outputs = ["y_4"]
        adapter = MDOScenarioAdapter(
            scenario, inputs, outputs, set_bounds_before_opt=True
        )

        # Execute the adapter with default bounds
        adapter.execute()
        ds = scenario.design_space
        assert np_all(ds.get_lower_bounds() == [0.1, 0.75, 0.75, 0.1])
        assert np_all(ds.get_upper_bounds() == [0.4, 1.25, 1.25, 1.0])

        # Execute the adapter with passed bounds
        input_data = dict()
        lower_bounds = ds.array_to_dict(zeros(4))
        lower_suffix = MDOScenarioAdapter.LOWER_BND_SUFFIX
        upper_bounds = ds.array_to_dict(ones(4))
        upper_suffix = MDOScenarioAdapter.UPPER_BND_SUFFIX
        for bounds, suffix in [
            (lower_bounds, lower_suffix),
            (upper_bounds, upper_suffix),
        ]:
            bounds = {name + suffix: val for name, val in bounds.items()}
            input_data.update(bounds)
        adapter.execute(input_data)
        assert np_all(ds.get_lower_bounds() == zeros(4))
        assert np_all(ds.get_upper_bounds() == ones(4))

    def test_chain(self):
        """"""

        scenario = self.get_sobieski_scenario()
        mda = scenario.formulation.mda
        inputs = (
            list(mda.get_input_data_names()) + scenario.design_space.variables_names
        )
        outputs = ["x_1", "x_2", "x_3"]
        adapter = MDOScenarioAdapter(scenario, inputs, outputs)

        # Allow re exec when DONE for the chain execution
        mda.re_exec_policy = mda.RE_EXECUTE_DONE_POLICY
        chain = MDOChain([mda, adapter, mda])

        # Sobieski Z opt
        x_shared = array([0.06000319728113519, 60000, 1.4, 2.5, 70, 1500])
        chain.execute({"x_shared": x_shared})

        y_4 = chain.local_data["y_4"]
        assert y_4 > 2908.0

    def test_jacobian_inputs(self):

        scenario = self.get_sobieski_scenario()
        adapter = MDOScenarioAdapter(scenario, ["x_shared"], ["y_4"])

        # Pass invalid inputs
        self.assertRaises(ValueError, adapter._compute_jacobian, inputs=["toto"])

        # Pass invalid outputs
        self.assertRaises(ValueError, adapter._compute_jacobian, outputs=["toto"])
        scenario.add_constraint(["g_1"])
        adapter = MDOScenarioAdapter(scenario, ["x_shared"], ["y_4", "g_1"])
        self.assertRaises(ValueError, adapter._compute_jacobian, outputs=["g_1"])

        # Pass a multi-named objective
        scenario.formulation.opt_problem.objective.outvars = ["y_4"] * 2
        self.assertRaises(ValueError, adapter._compute_jacobian)

    def build_struct_scenario(self):

        ds = SobieskiProblem().read_design_space()
        sc_str = MDOScenario(
            disciplines=[SobieskiStructure()],
            formulation="DisciplinaryOpt",
            objective_name="y_11",
            design_space=deepcopy(ds).filter("x_1"),
            name="StructureScenario",
            maximize_objective=True,
        )
        sc_str.add_constraint("g_1", constraint_type="ineq")
        sc_str.default_inputs = {"max_iter": 20, "algo": "NLOPT_SLSQP"}

        return sc_str

    def build_prop_scenario(self):

        ds = SobieskiProblem().read_design_space()
        sc_prop = MDOScenario(
            disciplines=[SobieskiPropulsion()],
            formulation="DisciplinaryOpt",
            objective_name="y_34",
            design_space=deepcopy(ds).filter("x_3"),
            name="PropulsionScenario",
        )
        sc_prop.add_constraint("g_3", constraint_type="ineq")
        sc_prop.default_inputs = {"max_iter": 20, "algo": "NLOPT_SLSQP"}

        return sc_prop

    def check_adapter_jacobian(
        self, adapter, inputs, objective_threshold, lagrangian_threshold
    ):

        opt_problem = adapter.scenario.formulation.opt_problem
        outvars = opt_problem.objective.outvars
        constraints = opt_problem.get_constraints_names()

        # Test the Jacobian accuracy as objective Jacobian
        assert adapter.check_jacobian(
            inputs=inputs, outputs=outvars, threshold=objective_threshold
        )

        # Test the Jacobian accuracy as Lagrangian Jacobian (should be better)
        disc_jac_approx = DisciplineJacApprox(adapter)
        outputs = outvars + constraints
        func_approx_jac = disc_jac_approx.compute_approx_jac(outputs, inputs)
        post_opt_analysis = adapter.post_optimal_analysis
        lagr_jac = post_opt_analysis.compute_lagrangian_jac(func_approx_jac, inputs)
        assert disc_jac_approx.check_jacobian(
            lagr_jac, outvars, inputs, adapter, threshold=lagrangian_threshold
        )

    def test_adapter_jacobian(self):

        # Maximization scenario
        struct_scenario = self.build_struct_scenario()
        struct_adapter = MDOScenarioAdapter(
            struct_scenario, ["x_shared"], ["y_11", "g_1"], reset_x0_before_opt=True
        )
        self.check_adapter_jacobian(
            struct_adapter,
            ["x_shared"],
            objective_threshold=5e-2,
            lagrangian_threshold=5e-2,
        )

        # Minimization scenario
        prop_scenario = self.build_prop_scenario()
        prop_adapter = MDOScenarioAdapter(
            prop_scenario, ["x_shared"], ["y_34", "g_3"], reset_x0_before_opt=True
        )
        self.check_adapter_jacobian(
            prop_adapter,
            ["x_shared"],
            objective_threshold=1e-5,
            lagrangian_threshold=1e-5,
        )

    def test_add_outputs(self):

        # Maximization scenario
        struct_scenario = self.build_struct_scenario()
        struct_adapter = MDOScenarioAdapter(
            struct_scenario, ["x_shared"], ["y_11"], reset_x0_before_opt=True
        )
        struct_adapter.add_outputs(["g_1"])
        self.check_adapter_jacobian(
            struct_adapter,
            ["x_shared"],
            objective_threshold=5e-2,
            lagrangian_threshold=5e-2,
        )

    def check_obj_scenario_adapter(
        self, scenario, outputs, minimize, objective_threshold, lagrangian_threshold
    ):
        dim = scenario.design_space.dimension
        problem = scenario.formulation.opt_problem
        objective = problem.objective
        outvars = objective.outvars
        problem.objective = MDOFunction(
            lambda _: 123.456,
            objective.name,
            MDOFunction.TYPE_OBJ,
            lambda _: zeros(dim),
            "123.456",
            objective.args,
            objective.dim,
            outvars,
        )
        adapter = MDOObjScenarioAdapter(scenario, ["x_shared"], outputs)

        adapter.execute()
        local_value = adapter.local_data[outvars[0]]
        assert (
            minimize
            and allclose(local_value, array(123.456))
            or allclose(local_value, array(-123.456))
        )

        self.check_adapter_jacobian(
            adapter, ["x_shared"], objective_threshold, lagrangian_threshold
        )

    def test_obj_scenario_adapter(self):

        # Maximization scenario
        struct_scenario = self.build_struct_scenario()
        self.check_obj_scenario_adapter(
            struct_scenario,
            ["y_11", "g_1"],
            minimize=False,
            objective_threshold=1e-5,
            lagrangian_threshold=1e-5,
        )

        # Minimization scenario
        prop_scenario = self.build_prop_scenario()
        self.check_obj_scenario_adapter(
            prop_scenario,
            ["y_34", "g_3"],
            minimize=True,
            objective_threshold=1e-5,
            lagrangian_threshold=1e-5,
        )

    def test_lagrange_multipliers_outputs(self):
        """Test the output of Lagrange multipliers."""
        struct_scenario = self.build_struct_scenario()
        x1_low_mult_name = MDOScenarioAdapter.get_bnd_mult_name("x_1", False)
        x1_upp_mult_name = MDOScenarioAdapter.get_bnd_mult_name("x_1", True)
        g1_mult_name = MDOScenarioAdapter.get_cstr_mult_name("g_1")
        mult_names = [x1_low_mult_name, x1_upp_mult_name, g1_mult_name]
        # Check the absence of multipliers when not required
        adapter = MDOScenarioAdapter(struct_scenario, ["x_shared"], ["y_11", "g_1"])
        assert not adapter.is_all_outputs_existing(mult_names)
        # Check the multipliers when required
        adapter = MDOScenarioAdapter(
            struct_scenario, ["x_shared"], ["y_11", "g_1"], output_multipliers=True
        )
        assert adapter.is_all_outputs_existing(mult_names)
        adapter.execute()
        problem = struct_scenario.formulation.opt_problem
        x_opt = problem.solution.x_opt
        obj_grad = problem.nonproc_objective.jac(x_opt)
        g1_jac = problem.nonproc_constraints[0].jac(x_opt)
        x1_low_mult, x1_upp_mult, g1_mult = adapter.get_outputs_by_name(mult_names)
        lagr_grad = obj_grad + matmul(g1_mult.T, g1_jac) - x1_low_mult + x1_upp_mult
        assert allclose(lagr_grad, zeros_like(lagr_grad))
