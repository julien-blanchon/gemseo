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
#    INITIAL AUTHORS - initial API and implementation and/or initial
#                           documentation
#        :author: Damien Guenot
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
#         Francois Gallard : refactoring for v1, May 2016
"""scipy.optimize optimization library wrapper."""
from __future__ import division, unicode_literals

import logging
from typing import Any, Optional

from numpy import isfinite, real
from scipy import optimize

from gemseo.algos.opt.opt_lib import OptimizationLibrary

LOGGER = logging.getLogger(__name__)


class ScipyOpt(OptimizationLibrary):
    """Scipy optimization library interface.

    See OptimizationLibrary.
    """

    LIB_COMPUTE_GRAD = True

    OPTIONS_MAP = {
        # Available only in the doc !
        OptimizationLibrary.LS_STEP_NB_MAX: "maxls",
        OptimizationLibrary.LS_STEP_SIZE_MAX: "stepmx",
        OptimizationLibrary.MAX_FUN_EVAL: "maxfun",
        OptimizationLibrary.PG_TOL: "gtol",
    }

    def __init__(self):
        """Constructor.

        Generate the library dict, contains the list
        of algorithms with their characteristics:

        - does it require gradient
        - does it handle equality constraints
        - does it handle inequality constraints
        """
        super(ScipyOpt, self).__init__()
        doc = "https://docs.scipy.org/doc/scipy/reference/"
        self.lib_dict = {
            "SLSQP": {
                self.INTERNAL_NAME: "SLSQP",
                self.REQUIRE_GRAD: True,
                self.POSITIVE_CONSTRAINTS: True,
                self.HANDLE_EQ_CONS: True,
                self.HANDLE_INEQ_CONS: True,
                self.DESCRIPTION: "Sequential Least-Squares Quadratic "
                "Programming (SLSQP) implemented in "
                "the SciPy library",
                self.WEBSITE: doc + "optimize.minimize-slsqp.html",
            },
            "L-BFGS-B": {
                self.INTERNAL_NAME: "L-BFGS-B",
                self.REQUIRE_GRAD: True,
                self.HANDLE_EQ_CONS: False,
                self.HANDLE_INEQ_CONS: False,
                self.DESCRIPTION: "Limited-memory BFGS algorithm "
                "implemented in SciPy library",
                self.WEBSITE: doc + "generated/scipy.optimize.fmin_l_bfgs_b.html",
            },
            "TNC": {
                self.INTERNAL_NAME: "TNC",
                self.REQUIRE_GRAD: True,
                self.HANDLE_EQ_CONS: False,
                self.HANDLE_INEQ_CONS: False,
                self.DESCRIPTION: "Truncated Newton (TNC) algorithm "
                "implemented in SciPy library",
                self.WEBSITE: doc + "optimize.minimize-tnc.html",
            },
        }

    def _get_options(
        self,
        max_iter=999,  # type: int
        ftol_rel=1e-9,  # type: float
        ftol_abs=1e-9,  # type: float
        xtol_rel=1e-9,  # type: float
        xtol_abs=1e-9,  # type: float
        max_ls_step_size=0.0,  # type: float
        max_ls_step_nb=20,  # type: int
        max_fun_eval=999,  # type: int
        max_time=0,  # type: float
        pg_tol=1e-5,  # type: float
        disp=0,  # type: int
        maxCGit=-1,  # type: int # noqa: N803
        eta=-1.0,  # type: float
        factr=1e7,  # type: float
        maxcor=20,  # type: int
        normalize_design_space=True,  # type: int
        eq_tolerance=1e-2,  # type: float
        ineq_tolerance=1e-4,  # type: float
        stepmx=0.0,  # type: float
        minfev=0.0,  # type: float
        scale=None,  # type: Optional[float]
        rescale=-1,  # type: float
        offset=None,  # type: Optional[float]
        **kwargs  # type: Any
    ):
        r"""Set the options default values.

        To get the best and up to date information about algorithms options,
        go to scipy.optimize documentation:
        https://docs.scipy.org/doc/scipy/reference/tutorial/optimize.html

        Args:
            max_iter: maximum number of iterations, ie unique calls to f(x)
            ftol_rel: stop criteria, relative tolerance on the
               objective function,
               if abs(f(xk)-f(xk+1))/abs(f(xk))<= ftol_rel: stop
               (Default value = 1e-9)
            ftol_abs: stop criteria, absolute tolerance on the objective
               function, if abs(f(xk)-f(xk+1))<= ftol_rel: stop
               (Default value = 1e-9)
            xtol_rel: stop criteria, relative tolerance on the
               design variables,
               if norm(xk-xk+1)/norm(xk)<= xtol_rel: stop
               (Default value = 1e-9)
            xtol_abs: stop criteria, absolute tolerance on the
               design variables,
               if norm(xk-xk+1)<= xtol_abs: stop
               (Default value = 1e-9)
            max_ls_step_size: Maximum step for the line search
               (Default value = 0.)
            max_ls_step_nb: Maximum number of line search steps
               per iteration. (Default value = 20)
            max_fun_eval: internal stop criteria on the
               number of algorithm outer iterations (Default value = 999)
            max_time: maximum runtime in seconds,
                disabled if 0 (Default value = 0)
            pg_tol: stop criteria on the projected gradient norm
               (Default value = 1e-5)
            disp: display information, (Default value = 0)
            maxCGit: Maximum Conjugate Gradient internal solver
                iterations (Default value = -1)
            eta: severity of the linesearch, specific to
                TNC algorithm (Default value = -1.)
            factr: stop criteria on the projected gradient norm,
                stop if max_i (grad_i)<eps_mach \* factr, where eps_mach is the
                machine precision ( Default value = 1e7)
            maxcor: maximum BFGS updates (Default value = 20)
            normalize_design_space: If True, scales variables in [0, 1]
            eq_tolerance: equality tolerance
            ineq_tolerance: inequality tolerance
            stepmx: Maximum step for the line search.
            minfev: Minimum function value estimate
            scale: Scaling factors to apply to each variable
            rescale: Scaling factor (in log10) used to trigger f value
                rescaling
            offset: Value to subtract from each variable.
            **kwargs: The other algorithm options.
        """
        nds = normalize_design_space
        popts = self._process_options(
            max_iter=max_iter,
            ftol_rel=ftol_rel,
            ftol_abs=ftol_abs,
            xtol_rel=xtol_rel,
            xtol_abs=xtol_abs,
            max_time=max_time,
            max_ls_step_size=max_ls_step_size,
            max_ls_step_nb=max_ls_step_nb,
            max_fun_eval=max_fun_eval,
            pg_tol=pg_tol,
            disp=disp,
            maxCGit=maxCGit,  # noqa: N803
            eta=eta,
            factr=factr,
            maxcor=maxcor,
            normalize_design_space=nds,
            ineq_tolerance=ineq_tolerance,
            eq_tolerance=eq_tolerance,
            stepmx=stepmx,
            minfev=minfev,
            scale=scale,
            rescale=rescale,
            offset=offset,
            **kwargs
        )
        return popts

    def _run(self, **options):
        """Runs the algorithm, to be overloaded by subclasses.

        :param options: the options dict for the algorithm
        """
        # remove normalization from options for algo
        normalize_ds = options.pop(self.NORMALIZE_DESIGN_SPACE_OPTION, True)
        # Get the normalized bounds:
        x_0, l_b, u_b = self.get_x0_and_bounds_vects(normalize_ds)
        # Replace infinite values with None:
        l_b = [val if isfinite(val) else None for val in l_b]
        u_b = [val if isfinite(val) else None for val in u_b]
        bounds = list(zip(l_b, u_b))

        def real_part_fun(x_vect):
            """Wraps the function and returns the real part."""
            return real(self.problem.objective.func(x_vect))

        fun = real_part_fun

        constraints = self.get_right_sign_constraints()
        cstr_scipy = []
        for cstr in constraints:
            c_scipy = {"type": cstr.f_type, "fun": cstr.func, "jac": cstr.jac}
            cstr_scipy.append(c_scipy)
        jac = self.problem.objective.jac

        # |g| is in charge of ensuring max iterations, and
        # xtol, ftol, since it may
        # have a different definition of iterations, such as for SLSQP
        # for instance which counts duplicate calls to x as a new iteration
        options["maxiter"] = 10000000

        # Deactivate scipy stop criteria to use |g|' ones
        options["ftol"] = 0.0
        options["xtol"] = 0.0
        options.pop(self.F_TOL_ABS)
        options.pop(self.X_TOL_ABS)
        options.pop(self.F_TOL_REL)
        options.pop(self.X_TOL_REL)
        options.pop(self.MAX_TIME)
        options.pop(self.MAX_ITER)
        if self.algo_name != "TNC":
            options.pop("xtol")

        opt_result = optimize.minimize(
            fun=fun,
            x0=x_0,
            method=self.internal_algo_name,
            jac=jac,
            bounds=bounds,
            constraints=cstr_scipy,
            tol=None,
            options=options,
        )

        return self.get_optimum_from_database(opt_result.message, opt_result.status)
