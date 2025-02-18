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
#    INITIAL AUTHORS - initial API and implementation and/or initial
#                         documentation
#        :author: Francois Gallard
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
from __future__ import annotations

from copy import deepcopy

from gemseo import create_discipline
from gemseo import create_scenario
from gemseo.core.discipline import MDODiscipline
from gemseo.disciplines.scenario_adapters.mdo_scenario_adapter import MDOScenarioAdapter
from gemseo.mda.jacobi import MDAJacobi
from gemseo.problems.sobieski.core.problem import SobieskiProblem
from gemseo.problems.sobieski.process.mda_jacobi import SobieskiMDAJacobi
from numpy import array
from numpy import isclose
from numpy import ones
from numpy import zeros

from .test_gauss_seidel import SelfCoupledDisc


def test_jacobi_sobieski():
    """Test the execution of Jacobi on Sobieski."""
    mda = SobieskiMDAJacobi()
    mda.execute()
    mda.default_inputs["x_shared"] += 0.02
    mda.warm_start = True
    mda.execute()
    assert mda.residual_history[-1] < 1e-4

    assert mda.local_data[mda.RESIDUALS_NORM][0] < 1e-4


def test_secant_acceleration(tmp_wd):
    tolerance = 1e-12
    mda = SobieskiMDAJacobi(tolerance=tolerance, max_mda_iter=30, acceleration=None)
    mda.execute()
    nit1 = len(mda.residual_history)

    mda = SobieskiMDAJacobi(
        tolerance=tolerance, max_mda_iter=30, acceleration=mda.SECANT_ACCELERATION
    )
    mda.execute()
    mda.plot_residual_history(filename="Jacobi_secant.pdf")
    nit2 = len(mda.residual_history)

    mda = SobieskiMDAJacobi(
        tolerance=tolerance, max_mda_iter=30, acceleration=mda.M2D_ACCELERATION
    )
    mda.execute()
    mda.plot_residual_history(filename="Jacobi_m2d.pdf")
    nit3 = len(mda.residual_history)
    assert nit2 < nit1
    assert nit3 < nit1
    assert nit3 < nit2


def test_m2d_acceleration_linalg_error():
    """Verify the linalg error handling."""
    mda = SobieskiMDAJacobi(acceleration="m2d")
    sol, ok = mda._minimize_2md(1.0, zeros(2), zeros(2))
    assert not ok
    assert (sol == zeros(2)).all()


def test_secant_acceleration_linalg_error():
    """Verify the nan handling."""
    mda = SobieskiMDAJacobi(acceleration="secant")
    sol = mda._compute_secant_acc(zeros(2), zeros(2), ones(2), zeros(2))
    assert (sol == ones(2)).all()


def test_mda_jacobi_parallel():
    """Comparison of Jacobi on Sobieski problem: 1 and 5 processes."""
    mda_seq = SobieskiMDAJacobi()
    sorted_c = ["y_12", "y_14", "y_21", "y_23", "y_24", "y_31", "y_32", "y_34"]
    assert mda_seq._input_couplings == sorted_c

    outdata_seq = mda_seq.execute()

    mda_parallel = SobieskiMDAJacobi(n_processes=4)
    mda_parallel.reset_statuses_for_run()
    outdata_parallel = mda_parallel.execute()

    for key, value in outdata_seq.items():
        assert array(outdata_parallel[key] == value).all()


def test_jacobi_sellar(sellar_disciplines):
    """Test the execution of Jacobi on Sobieski."""
    mda = MDAJacobi(sellar_disciplines)
    mda.execute()

    assert mda.residual_history[-1] < 1e-4
    assert mda.local_data[mda.RESIDUALS_NORM][0] < 1e-4


def test_expected_workflow():
    """Test MDAJacobi workflow should be list of one tuple of disciplines (meaning
    parallel execution)"""
    disc1 = MDODiscipline()
    disc2 = MDODiscipline()
    disc3 = MDODiscipline()
    disciplines = [disc1, disc2, disc3]

    mda = MDAJacobi(disciplines, n_processes=1)
    expected = (
        "{MDAJacobi(None), [MDODiscipline(None), MDODiscipline(None), "
        "MDODiscipline(None), ], }"
    )
    assert str(mda.get_expected_workflow()) == expected

    mda = MDAJacobi(disciplines, n_processes=2)
    expected = (
        "{MDAJacobi(None), (MDODiscipline(None), MDODiscipline(None), "
        "MDODiscipline(None), ), }"
    )
    assert str(mda.get_expected_workflow()) == expected


def test_expected_workflow_with_adapter():
    discs = create_discipline(
        [
            "SobieskiPropulsion",
            "SobieskiStructure",
            "SobieskiAerodynamics",
            "SobieskiMission",
        ]
    )
    design_space = SobieskiProblem().design_space
    scn_propu = create_scenario(
        discs,
        "DisciplinaryOpt",
        "y_4",
        design_space=deepcopy(design_space).filter("x_3"),
        name="PropulsionScenario",
    )
    adapter_propu = MDOScenarioAdapter(scn_propu, ["x_1", "x_2"], ["x_3"])
    scn_aero = create_scenario(
        discs,
        "DisciplinaryOpt",
        "y_4",
        design_space=deepcopy(design_space).filter("x_2"),
        name="AeroScenario",
    )
    adapter_aero = MDOScenarioAdapter(scn_aero, ["x_1", "x_3"], ["x_2"])
    scn_struct = create_scenario(
        discs,
        "DisciplinaryOpt",
        "y_4",
        design_space=deepcopy(design_space).filter("x_1"),
        name="StructureScenario",
    )
    adapter_struct = MDOScenarioAdapter(scn_struct, ["x_2", "x_3"], ["x_1"])
    adapters = [adapter_propu, adapter_aero, adapter_struct]

    mda = MDAJacobi(adapters)

    expected = (
        "{MDAJacobi(None), ("
        + "{PropulsionScenario(None), [SobieskiPropulsion(None), "
        + "SobieskiStructure(None), SobieskiAerodynamics(None), "
        + "SobieskiMission(None), ], }, "
        + "{AeroScenario(None), [SobieskiPropulsion(None), "
        + "SobieskiStructure(None), SobieskiAerodynamics(None), "
        + "SobieskiMission(None), ], }, "
        + "{StructureScenario(None), [SobieskiPropulsion(None), "
        + "SobieskiStructure(None), SobieskiAerodynamics(None), "
        + "SobieskiMission(None), ], }, "
        + "), }"
    )

    assert str(mda.get_expected_workflow()) == expected


def test_self_coupled():
    sc_disc = SelfCoupledDisc()
    mda = MDAJacobi([sc_disc], tolerance=1e-14, max_mda_iter=40)
    out = mda.execute()
    assert abs(out["y"] - 2.0 / 3.0) < 1e-6


def test_log_convergence(sellar_disciplines):
    """Check that the boolean log_convergence is correctly set."""
    mda = MDAJacobi(sellar_disciplines)
    assert not mda._log_convergence
    mda = MDAJacobi(sellar_disciplines, log_convergence=True)
    assert mda._log_convergence


def test_parallel_doe(generate_parallel_doe_data):
    """Test the execution of Jacobi in parallel.

    Args:
        generate_parallel_doe_data: Fixture that returns the optimum solution to
            a parallel DOE scenario for a particular `main_mda_name`
            and n_samples.
    """
    obj = generate_parallel_doe_data("MDAJacobi", 7)
    assert isclose(array([-obj]), array([608.175]), atol=1e-3)
