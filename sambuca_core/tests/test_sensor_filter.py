# -*- coding: utf-8 -*-
# Ensure compatibility of Python 2 with Python 3 constructs
from __future__ import absolute_import, division, print_function, unicode_literals

import numpy as np
import spectral.io.envi as envi
from scipy.io import loadmat, readsav
from pkg_resources import resource_filename

import sambuca_core as sbc


class TestSensorFilter(object):

    """ Sensor filter tests. """

    def __load_qb_data(self):
        # sensor filter
        sensor_filter = envi.open(
            resource_filename(
                sbc.__name__, "tests/data/sensor_filters/qbtest_filter_350_900nm.hdr"
            ),
            resource_filename(
                sbc.__name__, "tests/data/sensor_filters/qbtest_filter_350_900nm.lib"
            ),
        ).spectra

        # input spectra
        input_spectra = envi.open(
            resource_filename(sbc.__name__, "tests/data/qbtest_input_spectra.hdr"),
            resource_filename(sbc.__name__, "tests/data/qbtest_input_spectra.lib"),
        ).spectra[0]

        # output spectra
        output_spectra = envi.open(
            resource_filename(sbc.__name__, "tests/data/qbtest_output_spectra.hdr"),
            resource_filename(sbc.__name__, "tests/data/qbtest_output_spectra.lib"),
        ).spectra[0]

        return sensor_filter, input_spectra, output_spectra

    def __load_casi04_data(self, sensor_filter_file=None):
        filename = resource_filename(
            sbc.__name__, "./tests/data/sensor_filter_test_data.sav"
        )
        data = readsav(filename)

        if sensor_filter_file:
            hdr = resource_filename(
                sbc.__name__,
                "./tests/data/sensor_filters/{0}.hdr".format(sensor_filter_file),
            )
            lib = resource_filename(
                sbc.__name__,
                "./tests/data/sensor_filters/{0}.lib".format(sensor_filter_file),
            )
            filt = envi.open(hdr, lib)
            return filt.spectra, data.input_spectra, data.output_spectra[:, 0]
        else:
            return data.filter, data.input_spectra, data.output_spectra[:, 0]

    def test_quickbird_spectral_library(self):
        """ Tests the sensor filter against the Quickbird sensor filter and
        test data saved in ENVI spectral libraries, generated by Matlab code.
        """

        sensor_filter, input_spectra, expected_output = self.__load_qb_data()
        actual_output = sbc.apply_sensor_filter(input_spectra, sensor_filter)
        assert np.allclose(actual_output, expected_output, rtol=1.0e-6, atol=1.0e-20)

    def test_casi04_filter_IDL_parsed_filter(self):
        """ Tests against data generated by the reference IDL code for the
        CASI04 sensor, using rrs spectra.

        This version of the test uses the sensor filter matrix as saved directly
        from IDL memory, as opposed to loading the sensor filter directly from
        the spectral library.

        The logic is that this test confirms that the sensor filter function
        gives the same output given the same inputs
        (filter matrix, input spectra) as the IDL code.
        """

        sensor_filter, input_spectra, expected_output = self.__load_casi04_data()
        actual_output = sbc.apply_sensor_filter(input_spectra, sensor_filter)
        assert expected_output.shape == actual_output.shape
        assert sensor_filter.shape[1] == len(input_spectra)
        assert sensor_filter.shape[0] == len(actual_output)
        assert sensor_filter.shape == (28, 551)
        assert np.allclose(actual_output, expected_output, rtol=1.0e-6, atol=1.0e-20)

    def test_casi04_filter_spectral_library_filter(self):
        """ Tests against data generated by the reference IDL code for the
        CASI04 sensor, using rrs spectra.

        This version of the test uses the sensor filter matrix as loaded
        directly from the spectral library file.

        This test is due to some suspicious lines in the IDL code that appear
        to modify the sensor filter matrix after loading.

        So here we have:
            expected_output: as calculated by IDL
            input_spectra: as used in the IDL code
            sensor_filter: directly from spectral library
        """

        sensor_filter, input_spectra, expected_output = self.__load_casi04_data(
            "CASI04_350_900_1nm"
        )

        # There is an unexplained issue with the Moreton Bay test data, where
        # the observations have 28 bands while the CASI04 sensor filter has
        # 30 bands. This has apparently been encounted before, as the IDL code
        # slices the sensor filter matrix to match the observation band count.
        # Until we have a sensible approach to this issue, I am simply replicating
        # the filter slice here in this test.
        sensor_filter = sensor_filter[
            0 : len(expected_output),
        ]

        actual_output = sbc.apply_sensor_filter(input_spectra, sensor_filter)
        assert sensor_filter.shape[1] == len(input_spectra)
        assert sensor_filter.shape[0] == len(actual_output)
        assert expected_output.shape == actual_output.shape
        assert np.allclose(actual_output, expected_output, rtol=1.0e-6, atol=1.0e-20)

    def test_synthetic_matlab_data(self):
        # load the test values generated from the Matlab code
        filename = resource_filename(sbc.__name__, "tests/data/test_resample.mat")
        self.__data = loadmat(filename, squeeze_me=True)

        src_spectra = self.__data["modelled_spectra"]
        expected_spectra = self.__data["resampled_spectra"]

        # the matlab sensor filter is transposed relative to layout that the
        # Sambuca code expects
        sensor_filter = self.__data["filt"].transpose()

        assert sensor_filter.shape[0] == 36
        assert sensor_filter.shape[1] == 551

        # resample
        resampled_spectra = sbc.apply_sensor_filter(src_spectra, sensor_filter)

        # test
        assert expected_spectra.shape == resampled_spectra.shape
        assert np.allclose(expected_spectra, resampled_spectra)
