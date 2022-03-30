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
#        :author: Francois Gallard, Matthias De Lozzo
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
"""Caching module to store all the entries in memory."""
from __future__ import division, unicode_literals

import logging
from typing import Any, Optional, Union

from gemseo.core.cache import AbstractFullCache, Data, JacobianData, OutputData
from gemseo.utils.data_conversion import nest_flat_bilevel_dict
from gemseo.utils.locks import synchronized
from gemseo.utils.multi_processing import RLock

LOGGER = logging.getLogger(__name__)


class MemoryFullCache(AbstractFullCache):
    """Cache using memory to cache all the data."""

    def __init__(
        self,
        tolerance=0.0,  # type: float
        name=None,  # type: Optional[str]
        is_memory_shared=True,  # type: bool
    ):  # type: (...) -> None
        """
        Args:
            is_memory_shared : If ``True``,
                a shared memory dictionary is used to store the data,
                which makes the cache compatible with multiprocessing.

        Warnings:
            If ``is_memory_shared`` is ``False``
            and multiple disciplines point to the same cache
            or the process is multi-processed,
            there may be duplicate computations
            because the cache will not be shared among the processes.
        """
        super(MemoryFullCache, self).__init__(tolerance, name)
        self.__is_memory_shared = is_memory_shared
        self.__initialize_data()

    def __initialize_data(self):  # type: (...) -> None
        """Initialize the dictionary storing the data."""
        if self.__is_memory_shared:
            self.__data = self._manager.dict()
        else:
            self.__data = {}

    def _copy_empty_cache(self):  # type: (...) -> MemoryFullCache
        return MemoryFullCache(self.tolerance, self.name, self.__is_memory_shared)

    def _initialize_entry(
        self,
        index,  # type: int
    ):  # type: (...) -> None
        self.__data[index] = {}

    def _set_lock(self):  # type: (...) -> RLock
        return RLock()

    def _has_group(
        self,
        index,  # type: int
        group,  # type: str
    ):  # type: (...) -> bool
        return group in self.__data.get(index)

    @synchronized
    def clear(self):  # type: (...) -> None
        super(MemoryFullCache, self).clear()
        self.__initialize_data()

    def _read_data(
        self,
        index,  # type: int
        group,  # type: str
        **options  # type: Any
    ):  # type: (...) -> Union[OutputData,JacobianData]
        data = self.__data[index].get(group)
        if group == self._JACOBIAN_GROUP and data is not None:
            return nest_flat_bilevel_dict(data, separator=self._JACOBIAN_SEPARATOR)

        return data

    def _write_data(
        self,
        values,  # type: Data
        group,  # type: str
        index,  # type: int
    ):  # type: (...) -> None
        data = self.__data[index]
        data[group] = values.copy()
        self.__data[index] = data

    @property
    def copy(self):  # type: (...) -> MemoryFullCache
        """Copy the current cache.

        Returns:
            A copy of the current cache.
        """
        cache = self._copy_empty_cache()
        cache.update(self)
        return cache
