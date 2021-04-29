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
#                         documentation
#        :author: Damien Guenot
#                 Francois Gallard
#    OTHER AUTHORS   - MACROSCOPIC CHANGES

import os
import unittest

import pytest
from numpy import array, complex128, ndarray

from gemseo.caches.hdf5_cache import HDF5Cache
from gemseo.core.auto_py_discipline import AutoPyDiscipline
from gemseo.core.chain import MDOChain
from gemseo.core.data_processor import ComplexDataProcessor
from gemseo.core.discipline import MDODiscipline
from gemseo.core.grammar import InvalidDataException
from gemseo.problems.sobieski.core import SobieskiProblem
from gemseo.problems.sobieski.wrappers import (
    SobieskiAerodynamics,
    SobieskiMission,
    SobieskiPropulsion,
    SobieskiStructure,
)


@pytest.mark.usefixtures("tmp_wd")
class TestMDODiscipline(unittest.TestCase):
    def build_sobieski_chain(self):
        """"""
        chain = MDOChain(
            [
                SobieskiStructure(),
                SobieskiAerodynamics(),
                SobieskiPropulsion(),
                SobieskiMission(),
            ]
        )
        chain_inputs = chain.input_grammar.get_data_names()
        indata = SobieskiProblem().get_default_inputs(names=chain_inputs)
        return chain, indata

    def test_set_statuses(self):
        """"""
        chain = MDOChain(
            [
                SobieskiAerodynamics(),
                SobieskiPropulsion(),
                SobieskiStructure(),
                SobieskiMission(),
            ]
        )
        chain.set_disciplines_statuses("FAILED")
        self.assertEqual(chain.disciplines[0].status, "FAILED")

    def test_get_sub_disciplines(self):
        """"""
        chain = MDOChain([SobieskiAerodynamics()])
        self.assertEqual(len(chain.disciplines[0].get_sub_disciplines()), 0)

    def test_instantiate_grammars(self):
        """"""
        chain = MDOChain([SobieskiAerodynamics()])
        self.assertRaises(
            ValueError,
            lambda: chain.disciplines[0]._instantiate_grammars(
                None, None, grammar_type="None"
            ),
        )

    def test_execute_status_error(self):
        """"""
        chain, indata = self.build_sobieski_chain()
        chain.set_disciplines_statuses("FAILED")
        self.assertRaises(Exception, chain.execute, indata)

    def test_check_status_error(self):
        """"""
        chain, _ = self.build_sobieski_chain()
        self.assertRaises(Exception, chain._check_status, "None")

    def test_check_input_data_exception_chain(self):
        """"""
        chain, indata = self.build_sobieski_chain()
        del indata["x_1"]
        self.assertRaises(InvalidDataException, chain.check_input_data, indata)

    def test_check_input_data_exception(self):
        """"""
        struct = SobieskiStructure()
        struct_inputs = struct.input_grammar.get_data_names()
        indata = SobieskiProblem().get_default_inputs(names=struct_inputs)
        del indata["x_1"]
        self.assertRaises(InvalidDataException, struct.check_input_data, indata)

    def test_outputs(self):
        struct = SobieskiStructure()
        self.assertRaises(InvalidDataException, struct.check_output_data)
        indata = SobieskiProblem().get_default_inputs()
        struct.execute(indata)
        in_array = struct.get_inputs_asarray()
        assert len(in_array) == 10

    def test_get_outputs_by_name_exception(self):
        """"""
        chain, indata = self.build_sobieski_chain()
        chain.execute(indata)
        self.assertRaises(Exception, chain.get_outputs_by_name, "toto")

    def test_get_inputs_by_name_exception(self):
        """"""
        chain, _ = self.build_sobieski_chain()
        self.assertRaises(Exception, chain.get_inputs_by_name, "toto")

    def test_get_input_data(self):
        """"""
        chain, indata_ref = self.build_sobieski_chain()
        chain.execute(indata_ref)
        indata = chain.get_input_data()
        self.assertListEqual(sorted(indata.keys()), sorted(indata_ref.keys()))

    def test_get_local_data_by_name_exception(self):
        """"""
        chain, indata = self.build_sobieski_chain()
        chain.execute(indata)
        self.assertRaises(Exception, chain.get_local_data_by_name, "toto")

    def test_reset_statuses_for_run_error(self):
        """"""
        chain, _ = self.build_sobieski_chain()
        chain.set_disciplines_statuses("FAILED")
        chain.reset_statuses_for_run()

    def test_get_data_list_from_dict_error(self):
        """"""
        _, indata = self.build_sobieski_chain()
        self.assertRaises(TypeError, MDODiscipline.get_data_list_from_dict, 2, indata)

    def test_check_lin_error(self):
        """"""
        aero = SobieskiAerodynamics()
        problem = SobieskiProblem()
        indata = problem.get_default_inputs(names=aero.get_input_data_names())
        self.assertRaises(Exception, aero.check_jacobian, indata, derr_approx="bidon")

    def test_check_jac_fdapprox(self):
        """"""
        aero = SobieskiAerodynamics("complex128")
        inpts = aero.default_inputs
        aero.linearization_mode = aero.FINITE_DIFFERENCES
        aero.linearize(inpts, force_all=True)
        aero.check_jacobian(inpts)

        aero.linearization_mode = "auto"
        aero.check_jacobian(inpts)

    def test_check_jac_csapprox(self):
        """"""
        aero = SobieskiAerodynamics("complex128")
        aero.linearization_mode = aero.COMPLEX_STEP
        aero.linearize(force_all=True)
        aero.check_jacobian()

    def test_check_jac_approx_plot(self):
        """"""
        aero = SobieskiAerodynamics()
        aero.linearize(force_all=True)
        file_path = "gradients_validation.pdf"
        aero.check_jacobian(step=10.0, plot_result=True, file_path=file_path)
        assert os.path.exists(file_path)

    def test_check_lin_threshold(self):
        """"""
        aero = SobieskiAerodynamics()
        problem = SobieskiProblem()
        indata = problem.get_default_inputs(names=aero.get_input_data_names())
        aero.check_jacobian(indata, threshold=1e-50)

    def test_input_exist(self):
        """"""
        sr = SobieskiAerodynamics()
        problem = SobieskiProblem()
        indata = problem.get_default_inputs(names=sr.get_input_data_names())
        self.assertTrue(sr.is_input_existing(next(iter(indata.keys()))))
        self.assertFalse(sr.is_input_existing("bidon"))

    def test_get_all_inputs_outputs_name(self):
        """"""
        aero = SobieskiAerodynamics()
        problem = SobieskiProblem()
        indata = problem.get_default_inputs(names=aero.get_input_data_names())
        for data_name in indata:
            self.assertTrue(data_name in aero.get_input_data_names())

    def test_get_all_inputs_outputs(self):
        """"""
        aero = SobieskiAerodynamics()
        problem = SobieskiProblem()
        indata = problem.get_default_inputs(names=aero.get_input_data_names())
        aero.execute(indata)
        aero.get_all_inputs()
        aero.get_all_outputs()
        arr = aero.get_outputs_asarray()
        assert isinstance(arr, ndarray)
        assert len(arr) > 0
        arr = aero.get_inputs_asarray()
        assert isinstance(arr, ndarray)
        assert len(arr) > 0

    def test_serialize_deserialize(self):
        """"""
        aero = SobieskiAerodynamics()
        aero.data_processor = ComplexDataProcessor()
        out_file = "sellar1.o"
        input_data = SobieskiProblem().get_default_inputs()
        aero.execute(input_data)
        locd = aero.local_data
        aero.serialize(out_file)
        saero_u = MDODiscipline.deserialize(out_file)
        for k, v in locd.items():
            assert k in saero_u.local_data
            assert (v == saero_u.local_data[k]).all()

        def attr_list():
            return ["numpy_test"]

        aero.get_attributes_to_serialize = attr_list
        self.assertRaises(AttributeError, aero.serialize, out_file)

        saero_u_dict = saero_u.__dict__
        ok = True
        for k, _ in aero.__dict__.items():
            if k not in saero_u_dict and k != "get_attributes_to_serialize":
                ok = False

        assert ok

    def test_serialize_run_deserialize(self):
        """"""
        aero = SobieskiAerodynamics()
        out_file = "sellar1.o"
        input_data = SobieskiProblem().get_default_inputs()
        aero.serialize(out_file)
        saero_u = MDODiscipline.deserialize(out_file)
        saero_u.serialize(out_file)
        saero_u.execute(input_data)
        saero_u.serialize(out_file)
        saero_loc = MDODiscipline.deserialize(out_file)
        saero_loc.status = "PENDING"
        saero_loc.execute(input_data)

        for k, v in saero_loc.local_data.items():
            assert k in saero_u.local_data
            assert (v == saero_u.local_data[k]).all()

    def test_serialize_hdf_cache(self):
        """"""
        aero = SobieskiAerodynamics()
        cache_hdf_file = "aero_cache.h5"
        aero.set_cache_policy(aero.HDF5_CACHE, cache_hdf_file=cache_hdf_file)
        aero.execute()
        out_file = "sob_aero.pckl"
        aero.serialize(out_file)
        saero_u = MDODiscipline.deserialize(out_file)
        assert saero_u.cache.get_last_cached_outputs()["y_2"] is not None

    def test_data_processor(self):
        """"""
        aero = SobieskiAerodynamics()
        input_data = SobieskiProblem().get_default_inputs()
        aero.data_processor = ComplexDataProcessor()
        out_data = aero.execute(input_data)
        for v in out_data.values():
            assert isinstance(v, ndarray)
            assert v.dtype == complex128
        # Mix data processor and cache
        out_data2 = aero.execute(input_data)
        for k, v in out_data.items():
            assert (out_data2[k] == v).all()

    def test_diff_inputs_outputs(self):
        d = MDODiscipline()
        self.assertRaises(ValueError, d.add_differentiated_inputs, ["toto"])
        self.assertRaises(ValueError, d.add_differentiated_outputs, ["toto"])
        d.add_differentiated_inputs(None)

    def test_run(self):
        d = MDODiscipline()
        self.assertRaises(NotImplementedError, d._run)

    def testload_default_inputs(self):
        d = MDODiscipline()
        self.assertRaises(TypeError, d._filter_inputs, ["toto"])
        notfailed = True
        try:
            d.default_inputs = ["toto"]
        except TypeError:
            notfailed = False
        if notfailed:
            raise Exception()

    def test_linearize_errors(self):
        class LinDisc0(MDODiscipline):
            def __init__(self):
                super(LinDisc0, self).__init__()

        LinDisc0()._compute_jacobian()

        class LinDisc(MDODiscipline):
            def __init__(self):
                super(LinDisc, self).__init__()
                self.input_grammar.initialize_from_data_names(["x"])
                self.output_grammar.initialize_from_data_names(["y"])

            def _run(self):
                self.local_data["y"] = array([2.0])

            def _compute_jacobian(self, inputs=None, outputs=None):
                self._init_jacobian()
                self.jac = {"y": {"x": array([0.0])}}

        d2 = LinDisc()
        d2.execute({"x": array([1.0])})
        # Shape is not 2D
        self.assertRaises(ValueError, d2.linearize, {"x": 1}, force_all=True)

        self.assertRaises(ValueError, d2.__setattr__, "linearization_mode", "toto")
        d2.local_data["y"] = 1
        self.assertRaises(ValueError, d2._check_jacobian_shape, ["x"], ["y"])

        sm = SobieskiMission()

        def _compute_jacobian(inputs=None, outputs=None):
            SobieskiMission._compute_jacobian(sm, inputs=inputs, outputs=outputs)
            sm.jac["y_4"]["x_shared"] = sm.jac["y_4"]["x_shared"] + 3.0

        sm._compute_jacobian = _compute_jacobian

        success = sm.check_jacobian(inputs=["x_shared"], outputs=["y_4"])
        assert not success

    def test_check_jacobian_errors(self):

        sm = SobieskiMission()
        self.assertRaises(ValueError, sm._check_jacobian_shape, [], [])

        sm.execute()
        sm.linearize(force_all=True)
        sm._check_jacobian_shape(sm.get_input_data_names(), sm.get_output_data_names())
        sm.local_data.pop("x_shared")
        sm._check_jacobian_shape(sm.get_input_data_names(), sm.get_output_data_names())
        sm.local_data.pop("y_4")
        sm._check_jacobian_shape(sm.get_input_data_names(), sm.get_output_data_names())

    def test_check_jacobian(self):
        sm = SobieskiMission()
        sm.execute()
        sm._compute_jacobian()

        def _compute_jacobian(inputs=None, outputs=None):
            SobieskiMission._compute_jacobian(sm, inputs=inputs, outputs=outputs)
            del sm.jac["y_4"]

        sm._compute_jacobian = _compute_jacobian
        self.assertRaises(KeyError, sm.linearize, force_all=True)

        sm2 = SobieskiMission()

        def _compute_jacobian2(inputs=None, outputs=None):
            SobieskiMission._compute_jacobian(sm2, inputs=inputs, outputs=outputs)
            del sm2.jac["y_4"]["x_shared"]

        sm2._compute_jacobian = _compute_jacobian2
        self.assertRaises(KeyError, sm2.linearize, force_all=True)

    def test_check_jacobian_2(self):
        x = array([1.0, 2.0])

        class LinDisc(MDODiscipline):
            def __init__(self):
                super(LinDisc, self).__init__()
                self.input_grammar.initialize_from_data_names(["x"])
                self.output_grammar.initialize_from_data_names(["y"])
                self.default_inputs = {"x": x}
                self.jac_key = "x"
                self.jac_len = 2

            def _run(self):
                self.local_data["y"] = array([2.0])

            def _compute_jacobian(self, inputs=None, outputs=None):
                self._init_jacobian()
                self.jac = {"y": {self.jac_key: array([[0.0] * self.jac_len])}}

        #             def _check_jacobian_shape(self, inputs, outputs):
        #                 pass

        disc = LinDisc()
        # Test failed to build gradient
        disc.jac_key = "z"
        self.assertRaises(KeyError, disc.linearize, {"x": x}, force_all=True)
        disc.jac_key = "x"
        disc.jac_len = 3
        self.assertRaises(ValueError, disc.linearize, {"x": x}, force_all=True)
        #         # Test not multiple d/dX
        disc.jac = {"y": {"x": array([[0.0], [1.0], [3.0]])}}
        self.assertRaises(ValueError, disc.linearize, {"x": x}, force_all=True)
        #         # Test inconsistent output size for gradient
        #         # Test too small d/dX
        disc.jac = {"y": {"x": array([[0.0]])}}
        self.assertRaises(ValueError, disc.linearize, {"x": x}, force_all=True)

    @pytest.mark.skip_under_windows
    def test_check_jacobian_parallel_fd(self):
        sm = SobieskiMission()
        sm.check_jacobian(
            derr_approx=sm.FINITE_DIFFERENCES,
            step=1e-6,
            threshold=1e-6,
            parallel=True,
            use_threading=False,
            n_processes=6,
        )

    @pytest.mark.skip_under_windows
    def test_check_jacobian_parallel_cplx(self):
        sm = SobieskiMission()
        sm.check_jacobian(
            derr_approx=sm.COMPLEX_STEP,
            step=1e-30,
            threshold=1e-6,
            parallel=True,
            use_threading=False,
            n_processes=6,
        )

    def test_execute_rerun_errors(self):
        class MyDisc(MDODiscipline):
            def _run(self):
                pass

        d = MyDisc()
        d.input_grammar.initialize_from_data_names(["a"])
        d.execute({"a": [1]})
        d.status = d.STATUS_RUNNING
        self.assertRaises(ValueError, d.execute, {"a": [2]})
        self.assertRaises(Exception, d.reset_statuses_for_run)

        d.status = d.STATUS_DONE
        d.execute({"a": [1]})
        d.re_exec_policy = d.RE_EXECUTE_NEVER_POLICY
        d.execute({"a": [1]})
        self.assertRaises(ValueError, d.execute, {"a": [2]})

        d.re_exec_policy = "THIS is not a policy"
        self.assertRaises(ValueError, d.execute, {"a": [5]})

    def test_cache(self):
        sm = SobieskiMission(enable_delay=0.1)
        sm.cache_tol = 1e-6
        xs = sm.default_inputs["x_shared"]
        sm.execute({"x_shared": xs})
        t0 = sm.exec_time
        sm.execute({"x_shared": xs + 1e-12})
        t1 = sm.exec_time
        assert t0 == t1
        sm.execute({"x_shared": xs + 0.1})
        t2 = sm.exec_time
        assert t2 > t1

    def test_cache_h5(self):
        sm = SobieskiMission(enable_delay=0.1)
        hdf_file = sm.name + ".hdf5"
        sm.set_cache_policy(sm.HDF5_CACHE, cache_hdf_file=hdf_file)
        xs = sm.default_inputs["x_shared"]
        sm.execute({"x_shared": xs})
        t0 = sm.exec_time
        sm.execute({"x_shared": xs})
        assert t0 == sm.exec_time
        sm.cache_tol = 1e-6
        t0 = sm.exec_time
        sm.execute({"x_shared": xs + 1e-12})
        assert t0 == sm.exec_time
        sm.execute({"x_shared": xs + 1e12})
        assert t0 != sm.exec_time
        # Read again the hashes
        sm.cache = HDF5Cache(hdf_file, sm.name)

        self.assertRaises(ImportError, sm.set_cache_policy, cache_type="toto")

    def test_cache_h5_inpts(self):
        sm = SobieskiMission()
        hdf_file = sm.name + ".hdf5"
        sm.set_cache_policy(sm.HDF5_CACHE, cache_hdf_file=hdf_file)
        xs = sm.default_inputs["x_shared"]
        sm.execute({"x_shared": xs})
        out_ref = sm.local_data["y_4"]
        sm.execute({"x_shared": xs + 1.0})
        sm.execute({"x_shared": xs})
        assert (sm.local_data["x_shared"] == xs).all()
        assert (sm.local_data["y_4"] == out_ref).all()

    def test_cache_memory_inpts(self):
        sm = SobieskiMission()
        sm.set_cache_policy(sm.MEMORY_FULL_CACHE)
        xs = sm.default_inputs["x_shared"]
        sm.execute({"x_shared": xs})
        out_ref = sm.local_data["y_4"]
        sm.execute({"x_shared": xs + 1.0})
        sm.execute({"x_shared": xs})
        assert (sm.local_data["x_shared"] == xs).all()
        assert (sm.local_data["y_4"] == out_ref).all()

    def test_cache_h5_jac(self):
        sm = SobieskiMission()
        hdf_file = sm.name + ".hdf5"
        sm.set_cache_policy(sm.HDF5_CACHE, cache_hdf_file=hdf_file)
        xs = sm.default_inputs["x_shared"]
        input_data = {"x_shared": xs}
        jac_1 = sm.linearize(input_data, force_all=True, force_no_exec=False)
        sm.execute(input_data)
        jac_2 = sm.linearize(input_data, force_all=True, force_no_exec=False)
        assert self.check_jac_equals(jac_1, jac_2)

        input_data = {"x_shared": xs + 2.0}
        sm.execute(input_data)
        jac_1 = sm.linearize(input_data, force_all=True, force_no_exec=True)

        input_data = {"x_shared": xs + 3.0}
        jac_2 = sm.linearize(input_data, force_all=True, force_no_exec=False)
        assert not self.check_jac_equals(jac_1, jac_2)

        sm.execute(input_data)
        jac_3 = sm.linearize(input_data, force_all=True, force_no_exec=False)
        assert self.check_jac_equals(jac_3, jac_2)

        jac_4 = sm.linearize(input_data, force_all=True, force_no_exec=True)
        assert self.check_jac_equals(jac_3, jac_4)

        sm.cache = HDF5Cache(hdf_file, sm.name)

    def test_cache_run_and_linearize(self):
        """Check that the cache is filled with the Jacobian when the discipline is
        linearized during _run()"""
        sm = SobieskiMission()
        run_orig = sm._run

        def run_and_lin():
            run_orig()
            sm._compute_jacobian()
            sm._is_linearized = True

        sm._run = run_and_lin
        sm.set_cache_policy()
        sm.execute()
        assert (
            sm.cache.get_outputs(
                sm.default_inputs, next(iter(sm.default_inputs.keys()))
            )
            is not None
        )

        sm.linearize()
        # Cache must be loaded
        assert sm.n_calls_linearize == 0

    @staticmethod
    def check_jac_equals(jac_1, jac_2):
        if not sorted(jac_1.keys()) == sorted(jac_2.keys()):
            return False
        for out, jac_dict in jac_1.items():
            if not sorted(jac_dict.keys()) == sorted(jac_2[out].keys()):
                return False
            for inpt, jac_loc in jac_dict.items():
                if not (jac_loc == jac_2[out][inpt]).all():
                    return False

        return True

    @pytest.mark.skip_under_windows
    def test_jac_approx_mix_fd(self):
        sm = SobieskiMission()
        sm.set_jacobian_approximation(
            sm.COMPLEX_STEP, jax_approx_step=1e-30, jac_approx_n_processes=4
        )
        assert sm.check_jacobian(parallel=True, n_processes=4, threshold=1e-4)

    def test_jac_cache_trigger_shapecheck(self):
        # if cache is loaded and jacobian has already been computed for given i/o
        # and jacobian is called again but with new i/o
        # it will compute the jacobian with the new i/o
        aero = SobieskiAerodynamics("complex128")
        inpts = aero.default_inputs
        aero.linearization_mode = aero.FINITE_DIFFERENCES
        in_names = ["x_2", "y_12"]
        aero.add_differentiated_inputs(in_names)
        out_names = ["y_21"]
        aero.add_differentiated_outputs(out_names)
        aero.linearize(inpts)

        in_names = ["y_32", "x_shared"]
        out_names = ["g_2"]
        aero._cache_was_loaded = True
        aero.add_differentiated_inputs(in_names)
        aero.add_differentiated_outputs(out_names)
        aero.linearize(inpts, force_all=False, force_no_exec=True)

    def test_is_linearized(self):
        # Test at the jacobian is not computed if _is_linearized is
        # set to true by the discipline
        aero = SobieskiAerodynamics()
        aero.execute()
        aero.linearize(force_all=True)
        assert aero.n_calls == 1
        assert aero.n_calls_linearize == 1
        del aero

        aero2 = SobieskiAerodynamics()
        aero_run = aero2._run
        aero_cjac = aero2._compute_jacobian

        def _run_and_jac():
            out = aero_run()
            aero_cjac(aero2.get_input_data_names(), aero2.get_output_data_names())
            aero2._is_linearized = True
            return out

        aero2._run = _run_and_jac

        aero2.execute()
        aero2.linearize(force_all=True)
        assert aero2.n_calls == 1
        assert aero2.n_calls_linearize == 0

    def test_init_jacobian(self):
        def myfunc(x=1, y=2):
            z = x + y
            return z

        disc = AutoPyDiscipline(myfunc)
        disc.jac = {}
        disc.execute()
        disc._init_jacobian(outputs=["z"], fill_missing_keys=True)

    def test_repr_str(self):
        def myfunc(x=1, y=2):
            z = x + y
            return z

        disc = AutoPyDiscipline(myfunc)
        assert str(disc) == "myfunc"
        assert repr(disc) == "myfunc\n   Inputs: x, y\n   Outputs: z"
