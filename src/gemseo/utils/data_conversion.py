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
#        :author: Charlie Vanaret
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
"""Conversion from a NumPy array to a dictionary of NumPy arrays and vice versa."""
from __future__ import division, unicode_literals

from copy import deepcopy
from functools import reduce as f_reduce
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Set,
    TYPE_CHECKING,
    Union,
)

from numpy import array, hstack, ndarray, vstack, zeros

if TYPE_CHECKING:
    from gemseo.core.discipline import MDODiscipline


class DataConversion(object):
    """Methods to juggle NumPy arrays and dictionaries of Numpy arrays."""

    FLAT_JAC_SEP = "!d$_$d!"

    @staticmethod
    def dict_to_array(
        data_dict,  # type: Mapping[str,ndarray]
        data_names,  # type: Iterable[str]
    ):  # type: (...) -> ndarray
        """Concatenate some values of a mapping associating values to names.

        This allows to convert:

        .. code-block:: python

            {'x': array([1.])}, 'y': array([2., 3.])}

        to:

        .. code-block:: python

            array([1., 2., 3.])

        Args:
            data_dict: The mapping to be converted;
                it associates values to names.
            data_names: The names to be used for the concatenation.

        Returns:
            The concatenation of the values for the provided names.
        """
        if not data_names:
            return array([])

        return hstack([data_dict[name] for name in data_names])

    @staticmethod
    def list_of_dict_to_array(
        data_list,  # type: Iterable[Mapping[str,Union[ndarray,Mapping[str,ndarray]]]]
        data_names,  # type: Iterable[str]
        group=None,  # type: Optional[str]
    ):  # type: (...) -> ndarray
        """Concatenate some values of mappings associating values to names.

        The names can be either grouped:

        .. code-block:: python

            [
                {'group1':
                    {'x': array([3.])},
                 'group2':
                    {'y': array([1., 1.])}
                },
                {'group1':
                    {'x': array([6.])},
                 'group2':
                    {'y': array([2., 2.])}
                }
            ]

        or ungrouped:

        .. code-block:: python

            [
                {'x': array([3.]), 'y': array([1., 1.])},
                {'x': array([6.]), 'y': array([2., 2.])}
            ]

        For both cases,
        if ``data_names=["y", "x"]``,
        the returned object will be

        .. code-block:: python

            array([[1., 1., 3.],
                   [2., 2., 6.]])

        Args:
            data_list: The mappings to be converted;
                it associates values to names, possibly classified by groups.
            data_names: The names to be used for the concatenation.
            group: The name of the group to be considered.
                If None, the data is assumed to have no group.

        Returns:
            The concatenation of the values of the passed names.
        """
        dict_to_array = DataConversion.dict_to_array
        if group is None:
            return array([dict_to_array(data, data_names) for data in data_list])

        return vstack([dict_to_array(data[group], data_names) for data in data_list])

    @staticmethod
    def array_to_dict(
        data_array,  # type: ndarray
        data_names,  # type: Iterable[str]
        data_sizes,  # type: Mapping[str,int]
    ):  # type: (...) -> Dict[str,ndarray]
        """Convert an NumPy array into a dictionary of NumPy arrays indexed by names.

        This allows to convert:

        .. code-block:: python

            array([1., 2., 3.])

        to:

        .. code-block:: python

            {'x': array([1.])}, 'y': array([2., 3.])}

        Args:
            data_array: The data array to be converted.
            data_names: The names to be used as keys of the dictionary.
                The data array must contain the values of these names in the same order,
                e.g. ``data_array=array([1.,2.])`` and ``data_names=["x","y"]``
                implies that ``x=array([1.])`` and ``x=array([2.])``.
            data_sizes: The sizes of the variables
                e.g. ``data_array=array([1.,2.,3.])``, ``data_names=["x","y"]``
                and ``data_sizes={"x":2,"y":1}`` implies that
                ``x=array([1.,2.])`` and ``x=array([3.])``.

        Returns:
            The data mapped to the names.

        Raises:
            ValueError: If the number of dimensions of the data array is greater than 2.
        """
        if data_array.ndim > 2:
            raise ValueError("Invalid data dimension >2 !")

        current_position = 0
        array_dict = {}
        for data_name in data_names:
            array_dict[data_name] = data_array[
                ..., current_position : current_position + data_sizes[data_name]
            ]
            current_position += data_sizes[data_name]

        return array_dict

    @staticmethod
    def jac_2dmat_to_dict(
        flat_jac,  # type: ndarray
        outputs,  # type: Iterable[str]
        inputs,  # type: Iterable[str]
        data_sizes,  # type: Mapping[str,int]
    ):  # type: (...) -> Dict[str,Dict[str,ndarray]]
        """Convert a full Jacobian matrix into elementary Jacobian matrices.

        The full Jacobian matrix is passed as a two-dimensional NumPy array.
        Its first dimension represents the outputs
        and its second one represents the inputs.

        Args:
            flat_jac: The full Jacobian matrix.
            inputs: The names of the inputs.
            outputs: The names of the outputs.
            data_sizes: The sizes of the inputs and outputs.

        Returns:
            The Jacobian matrices indexed by the names of the inputs and outputs.
            Precisely,
            ``jac[output][input]`` is a two-dimensional NumPy array
            representing the Jacobian matrix
            for the input ``input`` and output ``output``,
            with the output components in the first dimension
            and the output components in the second one.
        """
        output_index = 0
        jacobian = {}
        for output_name in outputs:
            jacobian[output_name] = {}
            output_jacobian = jacobian[output_name]
            output_size = data_sizes[output_name]
            input_index = 0
            for input_name in inputs:
                input_size = data_sizes[input_name]
                output_jacobian[input_name] = flat_jac[
                    output_index : output_index + output_size,
                    input_index : input_index + input_size,
                ]
                input_index += input_size

            output_index += output_size

        return jacobian

    @staticmethod
    def jac_3dmat_to_dict(
        jac,  # type: ndarray
        outputs,  # type: Iterable[str]
        inputs,  # type: Iterable[str]
        data_sizes,  # type: Mapping[str,int]
    ):  # type: (...) -> Dict[str,Dict[str,ndarray]]
        """Convert several full Jacobian matrices into elementary Jacobian matrices.

        The full Jacobian matrices are passed as a three-dimensional NumPy array.
        Its first dimension represents the different full Jacobian matrices,
        its second dimension represents the outputs
        and its third one represents the inputs.

        Args:
            jac: The full Jacobian matrices.
            inputs: The names of the inputs.
            outputs: The names of the outputs.
            data_sizes: The sizes of the inputs and outputs.

        Returns:
            The Jacobian matrices indexed by the names of the inputs and outputs.
            Precisely,
            ``jac[output][input]`` is a three-dimensional NumPy array
            where ``jac[output][input][i]`` represents the ``i``-th Jacobian matrix
            for the input ``input`` and output ``output``,
            with the output components in the first dimension
            and the output components in the second one.
        """
        output_index = 0
        jacobian = {}
        for output_name in outputs:
            jacobian[output_name] = {}
            output_size = data_sizes[output_name]
            input_index = 0
            for input_name in inputs:
                input_size = data_sizes[input_name]
                jacobian[output_name][input_name] = jac[
                    :,
                    output_index : output_index + output_size,
                    input_index : input_index + input_size,
                ]
                input_index += input_size

            output_index += output_size

        return jacobian

    @staticmethod
    def dict_jac_to_2dmat(
        jac_dict,  # type: Mapping[str,Mapping[str,ndarray]]
        outputs,  # type: Iterable[str]
        inputs,  # type: Iterable[str]
        data_sizes,  # type: Mapping[str,int]
    ):  # type: (...) -> ndarray
        """Convert elementary Jacobian matrices into a full Jacobian matrix.

        Args:
            jac_dict: The elementary Jacobian matrices
                indexed by the names of the inputs and outputs.
            inputs: The names of the inputs.
            outputs: The names of the outputs.
            data_sizes: The sizes of the inputs and outputs.

        Returns:
            The full Jacobian matrix
            whose first dimension represents the outputs
            and the second one represents the inputs,
            both preserving the order of variables passed as arguments.
        """
        n_outputs = sum((data_sizes[output_name] for output_name in outputs))
        n_inputs = sum((data_sizes[input_name] for input_name in inputs))
        flat_jac = zeros((n_outputs, n_inputs))
        output_index = 0
        for output_name in outputs:
            output_size = data_sizes[output_name]
            input_index = 0
            for input_name in inputs:
                input_size = data_sizes[input_name]
                flat_jac[
                    output_index : output_index + output_size,
                    input_index : input_index + input_size,
                ] = jac_dict[output_name][input_name]
                input_index += input_size

            output_index += output_size

        return flat_jac

    @staticmethod
    def dict_jac_to_dict(
        jac_dict,  # type: Mapping[str,Mapping[str,ndarray]]
    ):  # type: (...) -> Dict[str,ndarray]
        """Reindex a mapping of elementary Jacobian matrices by Jacobian names.

        A Jacobian name is built with the method :meth:`.flat_jac_name`
        from the input and output names.

        Args:
            jac_dict: The elementary Jacobian matrices
                indexed by input and output names.

        Returns:
            The elementary Jacobian matrices index by Jacobian names.
        """

        jacobian = {}
        for output_name, jac_dict_loc in jac_dict.items():
            for input_name, jac_value in jac_dict_loc.items():
                jac_name = DataConversion.flat_jac_name(output_name, input_name)
                jacobian[jac_name] = jac_value

        return jacobian

    @staticmethod
    def split_flat_jac_name(
        name,  # type: str
    ):  # type: (...) -> List[str]
        """Split the name of a flat Jacobian structure into input and output names.

        Args:
            name: The name to be splitted into input and output names.

        Returns:
            The name of the input, then the name of the output.
        """
        return name.split(DataConversion.FLAT_JAC_SEP)

    @staticmethod
    def flat_jac_name(
        out_name,  # type: str
        inpt_name,  # type: str
    ):  # type: (...) -> str
        """Concatenate the name of the output and input, with a separator.

        Args:
            out_name: The name of the output.
            inpt_name: The name of the input.

        Returns:
            The name of the output concatenated with the name of the input.
        """
        return out_name + DataConversion.FLAT_JAC_SEP + inpt_name

    @staticmethod
    def dict_to_jac_dict(
        flat_jac_dict,  # type:Mapping[str,ndarray]
    ):  # type: (...) -> Mapping[str,Mapping[str,ndarray]]
        """Reindex a mapping of elementary Jacobian matrices by input and output names.

        Args:
            flat_jac_dict: The elementary Jacobian matrices index by Jacobian names.
                A Jacobian name is built with the method :meth:`.flat_jac_name`
                from the input and output names.

        Returns:
            The elementary Jacobian matrices index by input and output names.
        """

        jac_names = [
            DataConversion.split_flat_jac_name(jac_name) for jac_name in flat_jac_dict
        ]
        output_names = set((jac_name[0]) for jac_name in jac_names)
        input_names = set((jac_name[1]) for jac_name in jac_names)

        jacobian = {}
        for output_name in output_names:
            jacobian[output_name] = {}
            for input_name in input_names:
                jac_name = DataConversion.flat_jac_name(output_name, input_name)
                jacobian[output_name][input_name] = flat_jac_dict[jac_name]

        return jacobian

    @staticmethod
    def update_dict_from_array(
        reference_input_data,  # type: Dict[str,ndarray]
        data_names,  # type: Iterable[str]
        values_array,  # type: ndarray
    ):  # type: (...) -> Dict[str,ndarray]
        """Update a data mapping from data array and names..

        The order of the data in the array follows the order of the data names.

        Args:
            reference_input_data: The reference data to be updated.
            data_names: The names for which to update the data.
            values_array: The data with which to update the reference one.

        Returns:
            The updated data mapping.

        Raises:
            TypeError: If the data with which to update the reference one
                is not a NumPy array.
            ValueError:
                * If a name for which to update the data is missing
                  from the reference data.
                * If the size of the data with which to update the reference one
                  is inconsistent with the reference data.
        """
        if not isinstance(values_array, ndarray):
            raise TypeError(
                "Values array must be a numpy.ndarray, "
                "got instead: {}.".format(type(values_array))
            )

        data = deepcopy(reference_input_data)

        if not data_names:
            return data

        i_min = i_max = 0
        for data_name in data_names:

            data_value = reference_input_data.get(data_name)
            if data_value is None:
                raise ValueError(
                    "Reference data has no item named: {}.".format(data_name)
                )

            i_max = i_min + data_value.size
            if len(values_array) < i_max:
                raise ValueError(
                    "Inconsistent input array size of values array {} "
                    "with reference data shape {} "
                    "for data named: {}.".format(
                        values_array, data_value.shape, data_name
                    )
                )

            data[data_name] = values_array[i_min:i_max].reshape(data_value.shape)
            i_min = i_max

        if i_max != values_array.size:
            raise ValueError(
                "Inconsistent data shapes:\n"
                "could not use the whole data array of shape {} "
                "(only reached max index = {}),\n"
                "while updating data dictionary keys {}\n"
                " of shapes : {}.".format(
                    values_array.shape,
                    i_max,
                    data_names,
                    [
                        (data_name, reference_input_data[data_name].shape)
                        for data_name in data_names
                    ],
                )
            )

        return data

    @staticmethod
    def deepcopy_datadict(
        data_dict,  # type: Mapping[str,ndarray]
        keys=None,  # type:Optional[Iterable[str]]
    ):
        """Perform a deep copy of a data mapping.

        This treats the NumPy arrays specially
        using ``array.copy()`` instead of ``deepcopy``.

        Args:
            data_dict: The data mapping to be copied.
            keys: The keys of the mapping to be considered.
                If None, consider all the mapping keys.

        Returns:
            A deep copy of the data mapping.
        """
        deep_copy = {}
        if keys is None:
            for key, value in data_dict.items():
                if isinstance(value, ndarray):
                    deep_copy[key] = value.copy()

                else:
                    deep_copy[key] = deepcopy(value)

        else:
            common_keys = set(keys) & set(data_dict.keys())
            for key in common_keys:
                value = data_dict[key]
                if isinstance(value, ndarray):
                    deep_copy[key] = value.copy()

                else:
                    deep_copy[key] = deepcopy(value)

        return deep_copy

    @staticmethod
    def __set_reduce(
        set_1,  # type: Iterable[Any],
        set_2,  # type: Iterable[Any]
    ):  # type: (...) -> Set[Any]
        """Return a set of unique elements of two merged sets.

        Args:
            set_1: The first set.
            set_2: The second set.

        Returns:
            The unique elements of the two merged sets.
        """
        return set(set_1) | set(set_2)

    @staticmethod
    def __get_names(
        disciplines,  # type: Iterable[MDODiscipline]
        inputs,  # type: bool
        recursive,  # type: bool
    ):  # type: (...) -> List[str]
        """Return all the input or outputs of the disciplines.

        Args:
            disciplines: The disciplines.
            inputs: Whether to return input names or output names.
            recursive: If True,
                search for the inputs of the sub-disciplines,
                when some disciplines are scenarios.

        Returns:
            The names of the variables.
        """

        main_disciplines = [
            discipline for discipline in disciplines if not discipline.is_scenario()
        ]
        if recursive:
            scenarios = [
                discipline for discipline in disciplines if discipline.is_scenario()
            ]
            sub_disciplines = list(
                f_reduce(
                    DataConversion.__set_reduce,
                    (scenario.disciplines for scenario in scenarios),
                )
            )
            return DataConversion.__get_names(
                sub_disciplines + main_disciplines, inputs, recursive=False
            )

        def get_data_names(
            discipline,  # type: MDODiscipline
        ):  # type: (...) -> List[str]
            """Return either the input names or output names of a discipline.

            Args:
                discipline: The discipline.

            Returns:
                The names of the disciplinary inputs or outputs.
            """
            if inputs:
                return discipline.get_input_data_names()
            else:
                return discipline.get_output_data_names()

        return list(
            f_reduce(
                DataConversion.__set_reduce,
                (get_data_names(discipline) for discipline in main_disciplines),
            )
        )

    @staticmethod
    def get_all_inputs(
        disciplines,  # type: Iterable[MDODiscipline]
        recursive=False,  # type: bool
    ):  # type: (...) -> List[str]
        """Return all the input names of the disciplines.

        Args:
            disciplines: The disciplines.
            recursive: If True,
                search for the inputs of the sub-disciplines,
                when some disciplines are scenarios.

        Returns:
            The names of the inputs.
        """
        return DataConversion.__get_names(disciplines, True, recursive=recursive)

    @staticmethod
    def get_all_outputs(
        disciplines,  # type: Iterable[MDODiscipline]
        recursive=False,  # type: bool
    ):  # type: (...) -> List[str]
        """Return all the output names of the disciplines.

        Args:
            disciplines: The disciplines.
            recursive: If True,
                search for the outputs of the sub-disciplines,
                when some disciplines are scenarios.

        Returns:
            The names of the outputs.
        """
        return DataConversion.__get_names(disciplines, False, recursive=recursive)
