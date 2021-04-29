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
#       :author: Francois Gallard
#    OTHER AUTHORS   - MACROSCOPIC CHANGES

from __future__ import absolute_import, division, print_function, unicode_literals

from os.path import dirname, join

import numpy as np
import pytest
from numpy import array, multiply, outer
from numpy.linalg import LinAlgError, norm
from scipy.optimize import rosen_hess

from gemseo.algos.opt.opt_factory import OptimizersFactory
from gemseo.algos.opt_problem import OptimizationProblem
from gemseo.post.core.hessians import (
    BFGSApprox,
    HessianApproximation,
    LSTSQApprox,
    SR1Approx,
)
from gemseo.problems.analytical.rosenbrock import Rosenbrock

MDF_HIST = join(dirname(__file__), "mdf_history.h5")


def build_history(n, l_b=-2, u_b=2.0):
    problem = Rosenbrock(n, l_b=l_b, u_b=u_b)
    result = OptimizersFactory().execute(problem, "SLSQP", max_iter=400)
    x_opt = result.x_opt
    assert np.linalg.norm(x_opt - np.ones(n)) < 0.01
    h_ref = rosen_hess(x_opt)
    return h_ref, result, problem


def compare_approximations(h_ref, approx_class, problem, ermax=0.7, **kwargs):
    """

    :param approx_class: param ermax:  (Default value = 0.7)
    :param ermax:  (Default value = 0.7)
    :param **kwargs:

    """
    database = problem.database
    n = problem.dimension
    approx = approx_class(database)
    h_approx, _, _, _ = approx.build_approximation(
        funcname=problem.objective.name, **kwargs
    )
    assert h_approx.shape == (n, n)
    error = compute_error(h_ref, h_approx)
    assert error <= ermax


def test_scaling():

    _, result, problem = build_history(
        2, l_b=array([-2.0, -1.0]), u_b=array([2.0, 1.0])
    )
    database = problem.database
    approx = HessianApproximation(database)
    design_space = problem.design_space
    _, _, _, _ = approx.build_approximation(
        funcname=problem.objective.name,
        scaling=True,
        design_space=design_space,
        normalize_design_space=False,
    )

    approx = SR1Approx(database)
    design_space = problem.design_space
    h_approx_unscaled, _, _, _ = approx.build_approximation(
        funcname=problem.objective.name,
        scaling=True,
        design_space=design_space,
        normalize_design_space=False,
    )

    h_approx_scaled, _, _, _ = approx.build_approximation(
        funcname=problem.objective.name,
        scaling=True,
        design_space=design_space,
        normalize_design_space=True,
    )

    h_exact = rosen_hess(result.x_opt)

    v = design_space._norm_factor
    scale_fact = outer(v, v.T)

    h_exact_scaled = multiply(h_exact, scale_fact)
    h_approx_unscaled_scaled = multiply(h_approx_unscaled, scale_fact)
    assert norm(h_exact_scaled - h_approx_unscaled_scaled) / norm(h_exact_scaled) < 1e-2
    assert norm(h_exact_scaled - h_approx_scaled) / norm(h_exact_scaled) < 1e-2


def compute_error(h_ref, h_approx):
    return (norm(h_approx - h_ref) / norm(h_ref)) * 100


def test_baseclass_methods():
    """"""
    _, _, problem = build_history(2)
    database = problem.database
    apprx = HessianApproximation(database)
    # 73 items in database
    at_most_niter = 2
    x_hist, x_grad_hist, n_iter, _ = apprx.get_x_grad_history(
        problem.objective.name, at_most_niter=at_most_niter
    )
    assert n_iter == at_most_niter
    assert x_hist.shape[0] == at_most_niter
    assert x_grad_hist.shape[0] == at_most_niter

    _, _, n_iter_ref, nparam = apprx.get_x_grad_history(
        problem.objective.name, at_most_niter=-1
    )

    _, _, n_iter_2, _ = apprx.get_x_grad_history(
        problem.objective.name, last_iter=n_iter_ref
    )

    assert n_iter_ref == n_iter_2
    _, _, n_iter_3, _ = apprx.get_x_grad_history(problem.objective.name, first_iter=10)

    assert n_iter_ref == n_iter_3 + 10

    apprx.build_approximation(
        problem.objective.name, b_mat0=np.eye(nparam), save_matrix=True
    )

    assert len(apprx.b_mat_history) > 1

    with (pytest.raises(ValueError)):
        apprx.get_x_grad_history(problem.objective.name, at_most_niter=1)
    database.clear()

    with (pytest.raises(ValueError)):
        apprx.get_x_grad_history(problem.objective.name, at_most_niter=at_most_niter)

    with (pytest.raises(ValueError)):
        apprx.get_x_grad_history(
            problem.objective.name,
            at_most_niter=at_most_niter,
            normalize_design_space=True,
        )


def test_get_x_grad_history_on_sobieski():
    opt_pb = OptimizationProblem.import_hdf(MDF_HIST)
    apprx = HessianApproximation(opt_pb.database)
    with (pytest.raises(ValueError)):
        apprx.get_x_grad_history("g_1")
    x_hist, x_grad_hist, n_iter, nparam = apprx.get_x_grad_history("g_1", func_index=1)

    assert len(x_hist) == 4
    assert n_iter == 4
    assert nparam == 10
    for x in x_hist:
        assert x.shape == (nparam,)

    assert len(x_hist) == len(x_grad_hist)
    for grad in x_grad_hist:
        assert grad.shape == (nparam,)

    with pytest.raises(ValueError):
        apprx.get_s_k_y_k(x_hist, x_grad_hist, 5)

    with (pytest.raises(ValueError)):
        apprx.get_x_grad_history("g_1", func_index=7)

    # Create inconsistent optimization history by restricting g_2 gradient
    # size
    x_0 = next(iter(opt_pb.database.keys()))
    val_0 = opt_pb.database[x_0]
    val_0["@g_2"] = val_0["@g_2"][1:]
    with pytest.raises(ValueError):
        apprx.get_x_grad_history("g_2")


def test_n_2():
    """"""
    h_ref, _, problem = build_history(2)
    compare_approximations(h_ref, BFGSApprox, problem, first_iter=8, ermax=3.0)
    compare_approximations(h_ref, LSTSQApprox, problem, first_iter=13, ermax=20.0)
    compare_approximations(h_ref, SR1Approx, problem, first_iter=7, ermax=30.0)
    compare_approximations(
        h_ref, HessianApproximation, problem, first_iter=8, ermax=30.0
    )


def test_n_5():
    """"""
    h_ref, _, problem = build_history(5)
    compare_approximations(h_ref, BFGSApprox, problem, first_iter=5, ermax=30.0)
    compare_approximations(h_ref, LSTSQApprox, problem, first_iter=19, ermax=40.0)
    compare_approximations(h_ref, SR1Approx, problem, first_iter=5, ermax=30.0)
    compare_approximations(
        h_ref, HessianApproximation, problem, first_iter=5, ermax=30.0
    )


def test_n_35():
    """"""
    h_ref, _, problem = build_history(35)
    compare_approximations(h_ref, SR1Approx, problem, first_iter=5, ermax=40.0)
    compare_approximations(h_ref, LSTSQApprox, problem, first_iter=165, ermax=110.0)
    compare_approximations(h_ref, SR1Approx, problem, first_iter=30, ermax=42.0)
    compare_approximations(
        h_ref, HessianApproximation, problem, first_iter=60, ermax=40.0
    )


def test_build_inverse_approximation():
    _, _, problem = build_history(2, l_b=array([-2.0, -1.0]), u_b=array([2.0, 1.0]))
    database = problem.database
    approx = HessianApproximation(database)
    funcname = problem.objective.name
    approx.build_inverse_approximation(funcname=funcname, h_mat0=[], factorize=True)
    with pytest.raises(LinAlgError):
        approx.build_inverse_approximation(funcname=funcname, h_mat0=array([1.0, 2.0]))
    with pytest.raises(LinAlgError):
        approx.build_inverse_approximation(
            funcname=funcname,
            h_mat0=array([[0.0, 1.0], [-1.0, 0.0]]),
            factorize=True,
        )
    approx.build_inverse_approximation(
        funcname=funcname, h_mat0=array([[1.0, 0.0], [0.0, 1.0]]), factorize=True
    )
    approx.build_inverse_approximation(funcname=funcname, return_x_grad=True)
    x_hist, x_grad_hist, _, _ = approx.get_x_grad_history(problem.objective.name)
    x_corr, grad_corr = approx.compute_corrections(x_hist, x_grad_hist)
    approx.rebuild_history(x_corr, x_hist[0], grad_corr, x_grad_hist[0])
