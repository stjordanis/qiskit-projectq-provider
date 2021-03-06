# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""
Shared functionality and helpers for the unit tests.
Note: see Issue #4 - this file is temporary;
      common.py in qiskit-core will move to a location which is included in the pip package.
"""

from enum import Enum
import functools
import inspect
import logging
import os
import unittest
from unittest.util import safe_repr

from qiskit_addon_projectq import __path__ as main_path


class Path(Enum):
    """Helper with paths commonly used during the tests."""
    # Main path:    qiskit-addon-projectq
    MAIN = main_path[0]
    # test path: qiskit-addon-projectq/test
    TEST = os.path.dirname(__file__)
    # Examples path:    examples/
    EXAMPLES = os.path.join(MAIN, '../examples')


class QiskitProjectQTestCase(unittest.TestCase):
    """Helper class that contains common functionality."""

    @classmethod
    def setUpClass(cls):
        cls.moduleName = os.path.splitext(inspect.getfile(cls))[0]
        cls.log = logging.getLogger(cls.__name__)

        # Set logging to file and stdout if the LOG_LEVEL environment variable
        # is set.
        if os.getenv('LOG_LEVEL'):
            # Set up formatter.
            log_fmt = ('{}.%(funcName)s:%(levelname)s:%(asctime)s:'
                       ' %(message)s'.format(cls.__name__))
            formatter = logging.Formatter(log_fmt)

            # Set up the file handler.
            log_file_name = '%s.log' % cls.moduleName
            file_handler = logging.FileHandler(log_file_name)
            file_handler.setFormatter(formatter)
            cls.log.addHandler(file_handler)

            # Set the logging level from the environment variable, defaulting
            # to INFO if it is not a valid level.
            level = logging._nameToLevel.get(os.getenv('LOG_LEVEL'),
                                             logging.INFO)
            cls.log.setLevel(level)

    @staticmethod
    def _get_resource_path(filename, path=Path.TEST):
        """ Get the absolute path to a resource.

        Args:
            filename (string): filename or relative path to the resource.
            path (Path): path used as relative to the filename.
        Returns:
            str: the absolute path to the resource.
        """
        return os.path.normpath(os.path.join(path.value, filename))

    def assertDictAlmostEqual(self, dict1, dict2, delta=None, msg=None,
                              places=None, default_value=0):
        """
        Assert two dictionaries with numeric values are almost equal.

        Fail if the two dictionaries are unequal as determined by
        comparing that the difference between values with the same key are
        not greater than delta (default 1e-8), or that difference rounded
        to the given number of decimal places is not zero. If a key in one
        dictionary is not in the other the default_value keyword argument
        will be used for the missing value (default 0). If the two objects
        compare equal then they will automatically compare almost equal.

        Args:
            dict1 (dict): a dictionary.
            dict2 (dict): a dictionary.
            delta (number): threshold for comparison (defaults to 1e-8).
            msg (str): return a custom message on failure.
            places (int): number of decimal places for comparison.
            default_value (number): default value for missing keys.

        Raises:
            TypeError: raises TestCase failureException if the test fails.
        """
        # pylint: disable=invalid-name
        if dict1 == dict2:
            # Shortcut
            return
        if delta is not None and places is not None:
            raise TypeError("specify delta or places not both")

        if places is not None:
            success = True
            standard_msg = ''
            # check value for keys in target
            keys1 = set(dict1.keys())
            for key in keys1:
                val1 = dict1.get(key, default_value)
                val2 = dict2.get(key, default_value)
                if round(abs(val1 - val2), places) != 0:
                    success = False
                    standard_msg += '(%s: %s != %s), ' % (safe_repr(key),
                                                          safe_repr(val1),
                                                          safe_repr(val2))
            # check values for keys in counts, not in target
            keys2 = set(dict2.keys()) - keys1
            for key in keys2:
                val1 = dict1.get(key, default_value)
                val2 = dict2.get(key, default_value)
                if round(abs(val1 - val2), places) != 0:
                    success = False
                    standard_msg += '(%s: %s != %s), ' % (safe_repr(key),
                                                          safe_repr(val1),
                                                          safe_repr(val2))
            if success is True:
                return
            standard_msg = standard_msg[:-2] + ' within %s places' % places

        else:
            if delta is None:
                delta = 1e-8  # default delta value
            success = True
            standard_msg = ''
            # check value for keys in target
            keys1 = set(dict1.keys())
            for key in keys1:
                val1 = dict1.get(key, default_value)
                val2 = dict2.get(key, default_value)
                if abs(val1 - val2) > delta:
                    success = False
                    standard_msg += '(%s: %s != %s), ' % (safe_repr(key),
                                                          safe_repr(val1),
                                                          safe_repr(val2))
            # check values for keys in counts, not in target
            keys2 = set(dict2.keys()) - keys1
            for key in keys2:
                val1 = dict1.get(key, default_value)
                val2 = dict2.get(key, default_value)
                if abs(val1 - val2) > delta:
                    success = False
                    standard_msg += '(%s: %s != %s), ' % (safe_repr(key),
                                                          safe_repr(val1),
                                                          safe_repr(val2))
            if success is True:
                return
            standard_msg = standard_msg[:-2] + ' within %s delta' % delta

        msg = self._formatMessage(msg, standard_msg)
        raise self.failureException(msg)


def slow_test(func):
    """
    Decorator that signals that the test takes minutes to run.

    Args:
        func (callable): test function to be decorated.

    Returns:
        callable: the decorated function.
    """

    @functools.wraps(func)
    def _(*args, **kwargs):
        if SKIP_SLOW_TESTS:
            raise unittest.SkipTest('Skipping slow tests')
        return func(*args, **kwargs)

    return _


def requires_qe_access(func):
    """
    Decorator that signals that the test uses the online API:
        * determines if the test should be skipped by checking environment
            variables.
        * if the test is not skipped, it reads `QE_TOKEN` and `QE_URL` from
            `Qconfig.py` or from environment variables.
        * if the test is not skipped, it appends `QE_TOKEN` and `QE_URL` as
            arguments to the test function.
    Args:
        func (callable): test function to be decorated.

    Returns:
        callable: the decorated function.
    """

    @functools.wraps(func)
    def _(*args, **kwargs):
        # pylint: disable=invalid-name
        if SKIP_ONLINE_TESTS:
            raise unittest.SkipTest('Skipping online tests')

        # Try to read the variables from Qconfig.
        try:
            import Qconfig
            QE_TOKEN = Qconfig.APItoken
            QE_URL = Qconfig.config['url']
            QE_HUB = Qconfig.config.get('hub')
            QE_GROUP = Qconfig.config.get('group')
            QE_PROJECT = Qconfig.config.get('project')
        except ImportError:
            # Try to read them from environment variables (ie. Travis).
            QE_TOKEN = os.getenv('QE_TOKEN')
            QE_URL = os.getenv('QE_URL')
            QE_HUB = os.getenv('QE_HUB')
            QE_GROUP = os.getenv('QE_GROUP')
            QE_PROJECT = os.getenv('QE_PROJECT')
        if not QE_TOKEN or not QE_URL:
            raise Exception(
                'Could not locate a valid "Qconfig.py" file nor read the QE '
                'values from the environment')

        kwargs['QE_TOKEN'] = QE_TOKEN
        kwargs['QE_URL'] = QE_URL
        kwargs['hub'] = QE_HUB
        kwargs['group'] = QE_GROUP
        kwargs['project'] = QE_PROJECT
        return func(*args, **kwargs)

    return _


def _is_ci_fork_pull_request():
    """
    Check if the tests are being run in a CI environment and if it is a pull
    request.

    Returns:
        bool: True if the tests are executed inside a CI tool, and the changes
            are not against the "master" branch.
    """
    if os.getenv('TRAVIS'):
        # Using Travis CI.
        if os.getenv('TRAVIS_PULL_REQUEST_BRANCH'):
            return True
    elif os.getenv('APPVEYOR'):
        # Using AppVeyor CI.
        if os.getenv('APPVEYOR_PULL_REQUEST_NUMBER'):
            return True
    return False


SKIP_ONLINE_TESTS = os.getenv('SKIP_ONLINE_TESTS', _is_ci_fork_pull_request())
SKIP_SLOW_TESTS = os.getenv('SKIP_SLOW_TESTS', True) not in ['false', 'False', '-1']
