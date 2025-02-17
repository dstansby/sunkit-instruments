import copy

import numpy as np
import pytest
from numpy.testing import assert_almost_equal, assert_array_equal
from pandas.testing import assert_frame_equal

import astropy.units as u
from astropy.tests.helper import assert_quantity_allclose
from astropy.time import Time
from astropy.units.quantity import Quantity
from sunpy import timeseries
from sunpy.time import TimeRange, is_time_equal, parse_time

from sunkit_instruments import goes_xrs as goes
from sunkit_instruments.data.test import get_test_filepath

# Define input variables to be used in test functions for
# _goes_chianti_tem.
LONGFLUX = Quantity([7e-6], unit="W/m**2")
SHORTFLUX = Quantity([7e-7], unit="W/m**2")
DATE = "2014-04-16"


@pytest.mark.remote_data
def test_goes_event_list():
    # Set a time range to search
    trange = TimeRange("2011-06-07 00:00", "2011-06-08 00:00")
    # Test case where GOES class filter is applied
    result = goes.get_goes_event_list(trange, goes_class_filter="M1")
    assert type(result) == list
    assert type(result[0]) == dict
    assert type(result[0]["event_date"]) == str
    assert type(result[0]["goes_location"]) == tuple
    assert isinstance(result[0]["peak_time"], Time)
    assert isinstance(result[0]["start_time"], Time)
    assert isinstance(result[0]["end_time"], Time)
    assert type(result[0]["goes_class"]) == str
    assert type(result[0]["noaa_active_region"]) == np.int64
    assert result[0]["event_date"] == "2011-06-07"
    assert result[0]["goes_location"] == (54, -21)
    # float errror
    assert is_time_equal(result[0]["start_time"], parse_time((2011, 6, 7, 6, 16)))
    assert is_time_equal(result[0]["peak_time"], parse_time((2011, 6, 7, 6, 41)))
    assert is_time_equal(result[0]["end_time"], parse_time((2011, 6, 7, 6, 59)))
    assert result[0]["goes_class"] == "M2.5"
    assert result[0]["noaa_active_region"] == 11226
    # Test case where GOES class filter not applied
    result = goes.get_goes_event_list(trange)
    assert type(result) == list
    assert type(result[0]) == dict
    assert type(result[0]["event_date"]) == str
    assert type(result[0]["goes_location"]) == tuple
    assert isinstance(result[0]["peak_time"], Time)
    assert isinstance(result[0]["start_time"], Time)
    assert isinstance(result[0]["end_time"], Time)
    assert type(result[0]["goes_class"]) == str
    assert type(result[0]["noaa_active_region"]) == np.int64
    assert result[0]["event_date"] == "2011-06-07"
    assert result[0]["goes_location"] == (54, -21)
    assert is_time_equal(result[0]["start_time"], parse_time((2011, 6, 7, 6, 16)))
    assert is_time_equal(result[0]["peak_time"], parse_time((2011, 6, 7, 6, 41)))
    assert is_time_equal(result[0]["end_time"], parse_time((2011, 6, 7, 6, 59)))
    assert result[0]["goes_class"] == "M2.5"
    assert result[0]["noaa_active_region"] == 11226


@pytest.fixture
def goeslc():
    return timeseries.TimeSeries(get_test_filepath("go1520110607.fits"))


@pytest.mark.remote_data
def test_calculate_temperature_em(goeslc):
    # Create XRSTimeSeries object, then create new one with
    # temperature & EM using with calculate_temperature_em().
    goeslc_new = goes.calculate_temperature_em(goeslc)
    # Test correct exception is raised if a XRSTimeSeries object is
    # not inputted.
    with pytest.raises(TypeError):
        goes.calculate_temperature_em([])
    # Find temperature and EM manually with _goes_chianti_tem()
    temp, em = goes._goes_chianti_tem(
        goeslc.quantity("xrsb"),
        goeslc.quantity("xrsa"),
        satellite=int(goeslc.meta.metas[0]["TELESCOP"].split()[1]),
        date="2014-01-01",
    )
    # Check that temperature and EM arrays from _goes_chianti_tem()
    # are same as those in new XRSTimeSeries object.
    assert goeslc_new.to_dataframe().temperature.all() == temp.value.all()
    assert goeslc_new.to_dataframe().em.all() == em.value.all()
    # Check rest of data frame of new XRSTimeSeries object is same
    # as that in original object.
    goeslc_revert = copy.deepcopy(goeslc_new)
    del goeslc_revert.to_dataframe()["temperature"]
    del goeslc_revert.to_dataframe()["em"]
    assert_frame_equal(goeslc_revert.to_dataframe(), goeslc.to_dataframe())


@pytest.mark.remote_data
def test_goes_chianti_tem_errors():
    # Define input variables.
    ratio = SHORTFLUX / LONGFLUX
    shortflux_toomany = Quantity(
        np.append(SHORTFLUX.value, SHORTFLUX.value[0]), unit="W/m**2"
    )
    shortflux_toosmall = copy.deepcopy(SHORTFLUX)
    shortflux_toosmall.value[0] = -1
    shortflux_toobig = copy.deepcopy(SHORTFLUX)
    shortflux_toobig.value[0] = 1
    temp_test = Quantity(np.zeros(len(LONGFLUX)) + 10, unit="MK")
    temp_test_toosmall = copy.deepcopy(temp_test)
    temp_test_toosmall.value[0] = -1
    temp_test_toobig = copy.deepcopy(temp_test)
    temp_test_toobig.value[0] = 101
    # First test correct exceptions are raised if incorrect inputs are
    # entered.
    with pytest.raises(ValueError):
        goes._goes_chianti_tem(LONGFLUX, SHORTFLUX, satellite=-1)
    with pytest.raises(ValueError):
        goes._goes_chianti_tem(LONGFLUX, shortflux_toomany)
    with pytest.raises(ValueError):
        goes._goes_get_chianti_temp(ratio, satellite=-1)
    with pytest.raises(ValueError):
        goes._goes_chianti_tem(LONGFLUX, SHORTFLUX, abundances="Neither")
    with pytest.raises(ValueError):
        goes._goes_get_chianti_temp(ratio, abundances="Neither")
    with pytest.raises(ValueError):
        goes._goes_chianti_tem(LONGFLUX, shortflux_toobig)
    with pytest.raises(ValueError):
        goes._goes_get_chianti_em(LONGFLUX, temp_test, satellite=-1)
    with pytest.raises(ValueError):
        goes._goes_get_chianti_em(LONGFLUX, temp_test, abundances="Neither")
    with pytest.raises(ValueError):
        goes._goes_get_chianti_em(LONGFLUX, temp_test, abundances="Neither")
    with pytest.raises(ValueError):
        goes._goes_get_chianti_em(LONGFLUX, temp_test_toosmall)
    with pytest.raises(ValueError):
        goes._goes_get_chianti_em(LONGFLUX, temp_test_toobig)


@pytest.mark.remote_data
def test_goes_chianti_tem_case1():
    # test case 1: satellite > 7, abundances = coronal
    temp1, em1 = goes._goes_chianti_tem(LONGFLUX, SHORTFLUX, satellite=15, date=DATE)
    np.testing.assert_allclose(temp1, Quantity([11.28], unit="MK"), rtol=0.01)
    assert all(em1 < Quantity([4.79e48], unit="1/cm**3")) and em1 > Quantity(
        [4.78e48], unit="1/cm**3"
    )


@pytest.mark.remote_data
def test_goes_chianti_tem_case2():
    # test case 2: satellite > 7, abundances = photospheric
    temp2, em2 = goes._goes_chianti_tem(
        LONGFLUX, SHORTFLUX, satellite=15, date=DATE, abundances="photospheric"
    )
    assert all(temp2 < Quantity([10.25], unit="MK")) and all(
        temp2 > Quantity([10.24], unit="MK")
    )
    assert all(em2 < Quantity([1.12e49], unit="1/cm**3")) and all(
        em2 > Quantity([1.11e49], unit="1/cm**3")
    )


@pytest.mark.remote_data
def test_goes_chianti_tem_case3():
    # test case 3: satellite < 8 and != 6, abundances = coronal
    temp3, em3 = goes._goes_chianti_tem(
        LONGFLUX, SHORTFLUX, satellite=5, date=DATE, abundances="coronal"
    )
    assert all(temp3 < Quantity([11.43], unit="MK")) and all(
        temp3 > Quantity([11.42], unit="MK")
    )
    assert all(em3 < Quantity([3.85e48], unit="1/cm**3")) and all(
        em3 > Quantity([3.84e48], unit="1/cm**3")
    )


@pytest.mark.remote_data
def test_goes_chianti_tem_case4():
    # test case 4: satellite < 8 and != 6, abundances = photospheric
    temp4, em4 = goes._goes_chianti_tem(
        LONGFLUX, SHORTFLUX, satellite=5, date=DATE, abundances="photospheric"
    )
    assert all(temp4 < Quantity([10.42], unit="MK")) and all(
        temp4 > Quantity([10.41], unit="MK")
    )
    assert all(em4 < Quantity(8.81e48, unit="1/cm**3")) and all(
        em4 > Quantity(8.80e48, unit="1/cm**3")
    )


@pytest.mark.remote_data
def test_goes_chianti_tem_case5():
    # test case 5: satellite = 6, date < 1983-06-28, abundances = coronal
    temp5, em5 = goes._goes_chianti_tem(
        LONGFLUX, SHORTFLUX, satellite=6, date="1983-06-27", abundances="coronal"
    )
    assert all(temp5 < Quantity(12.30, unit="MK")) and all(
        temp5 > Quantity(12.29, unit="MK")
    )
    assert all(em5 < Quantity(3.13e48, unit="1/cm**3")) and all(
        em5 > Quantity(3.12e48, unit="1/cm**3")
    )


@pytest.mark.remote_data
def test_goes_chianti_tem_case6():
    # test case 6: satellite = 6, date < 1983-06-28, abundances = photospheric
    temp6, em6 = goes._goes_chianti_tem(
        LONGFLUX, SHORTFLUX, satellite=6, date="1983-06-27", abundances="photospheric"
    )
    assert all(temp6 < Quantity(11.44, unit="MK")) and all(
        temp6 > Quantity(11.43, unit="MK")
    )
    assert all(em6 < Quantity(6.74e48, unit="1/cm**3")) and all(
        em6 > Quantity(6.73e48, unit="1/cm**3")
    )


@pytest.mark.remote_data
def test_goes_chianti_tem_case7():
    # test case 7: satellite = 6, date > 1983-06-28, abundances = coronal
    temp7, em7 = goes._goes_chianti_tem(
        LONGFLUX, SHORTFLUX, satellite=6, date=DATE, abundances="coronal"
    )
    assert all(temp7 < Quantity(11.34, unit="MK")) and all(
        temp7 > Quantity(11.33, unit="MK")
    )
    assert all(em7 < Quantity(4.08e48, unit="1/cm**3")) and all(
        em7 > Quantity(4.07e48, unit="1/cm**3")
    )


@pytest.mark.remote_data
def test_goes_chianti_tem_case8():
    # test case 8: satellite = 6, date > 1983-06-28, abundances = photospheric
    temp8, em8 = goes._goes_chianti_tem(
        LONGFLUX, SHORTFLUX, satellite=6, date=DATE, abundances="photospheric"
    )
    assert all(temp8 < Quantity(10.36, unit="MK")) and all(
        temp8 > Quantity(10.35, unit="MK")
    )
    assert all(em8 < Quantity(9.39e48, unit="1/cm**3")) and all(
        em8 > Quantity(9.38e48, unit="1/cm**3")
    )


@pytest.mark.remote_data
@pytest.mark.array_compare(file_format="text", reference_dir="./")
def test_calculate_radiative_loss_rate(goeslc):
    # Define input variables.
    not_goeslc = []
    goeslc_no_em = goes.calculate_temperature_em(goeslc)
    del goeslc_no_em.to_dataframe()["em"]

    # Check correct exceptions are raised to incorrect inputs
    with pytest.raises(TypeError):
        goes_test = goes.calculate_radiative_loss_rate(not_goeslc)

    # Check function gives correct results.
    # Test case 1: GOESTimeSeries object with only flux data
    goeslc_test = goes.calculate_radiative_loss_rate(goeslc)
    exp_data = np.array(
        [1.78100055e19, 1.66003113e19, 1.71993065e19, 1.60171768e19, 1.71993065e19]
    )
    np.testing.assert_allclose(goeslc_test.to_dataframe().rad_loss_rate[:5], exp_data)

    # Test case 2: GOESTimeSeries object with flux and temperature
    # data, but no EM data.
    goes_test = goes.calculate_radiative_loss_rate(goeslc_no_em)
    # we test that the column has been added
    assert "rad_loss_rate" in goes_test.columns
    # Compare every 50th value to save on filesize
    return np.array(goes_test.to_dataframe()[::50])


@pytest.mark.remote_data
def test_calc_rad_loss_errors():
    # Define input variables
    temp = 11.0 * Quantity(np.ones(6), unit="MK")
    em = 4.0e48 * Quantity(np.ones(6), unit="1/cm**3")
    obstime = np.array(
        [
            parse_time((2014, 1, 1, 0, 0, 0)),
            parse_time((2014, 1, 1, 0, 0, 2)),
            parse_time((2014, 1, 1, 0, 0, 4)),
            parse_time((2014, 1, 1, 0, 0, 6)),
            parse_time((2014, 1, 1, 0, 0, 8)),
            parse_time((2014, 1, 1, 0, 0, 10)),
        ],
        dtype=object,
    )
    temp_toolong = Quantity(np.append(temp.value, 0), unit="MK")
    obstime_toolong = np.array(
        [
            parse_time((2014, 1, 1, 0, 0, 0)),
            parse_time((2014, 1, 1, 0, 0, 2)),
            parse_time((2014, 1, 1, 0, 0, 4)),
            parse_time((2014, 1, 1, 0, 0, 6)),
            parse_time((2014, 1, 1, 0, 0, 8)),
            parse_time((2014, 1, 1, 0, 0, 10)),
            parse_time((2014, 1, 1, 0, 0, 12)),
        ],
        dtype=object,
    )
    obstime_nonchrono = copy.deepcopy(obstime)
    obstime_nonchrono[1] = obstime[-1]
    obstime_nonchrono[-1] = obstime[1]
    obstime_notdatetime = copy.deepcopy(obstime)
    obstime_notdatetime[0] = 1
    temp_outofrange = Quantity([101, 11.0, 11.0, 11.0, 11.0, 11.0], unit="MK")
    # Ensure correct exceptions are raised.
    with pytest.raises(ValueError):
        goes._calc_rad_loss(temp_toolong, em, obstime)
    with pytest.raises(ValueError):
        goes._calc_rad_loss(temp_outofrange, em, obstime)
    with pytest.raises(IOError):
        goes._calc_rad_loss(temp, em, obstime_toolong)
    with pytest.raises(ValueError):
        goes._calc_rad_loss(temp, em, obstime_notdatetime)
    with pytest.raises(ValueError):
        goes._calc_rad_loss(temp, em, obstime_nonchrono)


@pytest.mark.remote_data
def test_calc_rad_loss_nokwags():
    # Define input variables
    temp = Quantity([11.0, 11.0, 11.0, 11.0, 11.0, 11.0], unit="MK")
    em = Quantity([4.0e48, 4.0e48, 4.0e48, 4.0e48, 4.0e48, 4.0e48], unit="1/cm**3")
    # Test output is correct when no kwags are set.
    rad_loss_test = goes._calc_rad_loss(temp[:2], em[:2])
    rad_loss_expected = {
        "rad_loss_rate": 3.01851392e19 * Quantity(np.ones(2), unit="J/s")
    }
    assert sorted(rad_loss_test.keys()) == sorted(rad_loss_expected.keys())
    assert_quantity_allclose(
        rad_loss_test["rad_loss_rate"], rad_loss_expected["rad_loss_rate"], rtol=0.01
    )


@pytest.mark.remote_data
def test_calc_rad_loss_obstime():
    # Define input variables
    temp = Quantity([11.0, 11.0, 11.0, 11.0, 11.0, 11.0], unit="MK")
    em = Quantity([4.0e48, 4.0e48, 4.0e48, 4.0e48, 4.0e48, 4.0e48], unit="1/cm**3")
    obstime = np.array(
        [
            parse_time((2014, 1, 1, 0, 0, 0)),
            parse_time((2014, 1, 1, 0, 0, 2)),
            parse_time((2014, 1, 1, 0, 0, 4)),
            parse_time((2014, 1, 1, 0, 0, 6)),
            parse_time((2014, 1, 1, 0, 0, 8)),
            parse_time((2014, 1, 1, 0, 0, 10)),
        ],
        dtype=object,
    )
    # Test output is correct when obstime and cumulative kwargs are set.
    rad_loss_test = goes._calc_rad_loss(temp, em, obstime)
    rad_loss_expected = {
        "rad_loss_rate": 3.01851392e19 * Quantity(np.ones(6), unit="J/s"),
        "rad_loss_int": Quantity(3.01851392e20, unit="J"),
        "rad_loss_cumul": Quantity(
            [6.03702783e19, 1.20740557e20, 1.81110835e20, 2.41481113e20, 3.01851392e20],
            unit="J",
        ),
    }
    assert sorted(rad_loss_test.keys()) == sorted(rad_loss_expected.keys())
    assert_quantity_allclose(
        rad_loss_test["rad_loss_rate"], rad_loss_expected["rad_loss_rate"], rtol=0.0001
    )
    assert_quantity_allclose(
        rad_loss_test["rad_loss_int"], rad_loss_expected["rad_loss_int"], rtol=0.0001
    )
    assert_quantity_allclose(
        rad_loss_test["rad_loss_cumul"],
        rad_loss_expected["rad_loss_cumul"],
        rtol=0.0001,
    )


@pytest.mark.remote_data
def test_calculate_xray_luminosity(goeslc):
    # Check correct exceptions are raised to incorrect inputs
    not_goeslc = []
    with pytest.raises(TypeError):
        goes.calculate_xray_luminosity(not_goeslc)
    # Check function gives correct results.
    goeslc_test = goes.calculate_xray_luminosity(goeslc)
    exp_xrsa = u.Quantity(
        [2.8962085e14, 2.8962085e14, 2.8962085e14, 2.8962085e14, 2.8962085e14], "W"
    )
    exp_xrsb = u.Quantity(
        [5.4654352e16, 5.3133844e16, 5.3895547e16, 5.2375035e16, 5.3895547e16], "W"
    )
    assert_quantity_allclose(exp_xrsa, goeslc_test.quantity("luminosity_xrsa")[:5])
    assert_quantity_allclose(exp_xrsb, goeslc_test.quantity("luminosity_xrsb")[:5])


def test_goes_lx_errors():
    # Define input values of flux and time.
    longflux = 7e-6 * Quantity(np.ones(6), unit="W/m**2")
    shortflux = 7e-7 * Quantity(np.ones(6), unit="W/m**2")
    obstime = np.array(
        [
            parse_time((2014, 1, 1, 0, 0, 0)),
            parse_time((2014, 1, 1, 0, 0, 2)),
            parse_time((2014, 1, 1, 0, 0, 4)),
            parse_time((2014, 1, 1, 0, 0, 6)),
            parse_time((2014, 1, 1, 0, 0, 8)),
            parse_time((2014, 1, 1, 0, 0, 10)),
        ],
        dtype=object,
    )
    longflux_toolong = Quantity(np.append(longflux.value, 0), unit=longflux.unit)
    obstime_nonchrono = copy.deepcopy(obstime)
    obstime_nonchrono[1] = obstime[-1]
    obstime_notdatetime = copy.deepcopy(obstime)
    obstime_notdatetime[0] = 1
    # Ensure correct exceptions are raised.
    with pytest.raises(ValueError):
        goes._goes_lx(longflux_toolong, shortflux, obstime)
    with pytest.raises(ValueError):
        goes._goes_lx(longflux, shortflux, obstime_notdatetime)
    with pytest.raises(ValueError):
        goes._goes_lx(longflux, shortflux, obstime_nonchrono)


def test_goes_lx_nokwargs():
    # Define input values of flux and time.
    longflux = Quantity([7e-6, 7e-6, 7e-6, 7e-6, 7e-6, 7e-6], unit="W/m**2")
    shortflux = Quantity([7e-7, 7e-7, 7e-7, 7e-7, 7e-7, 7e-7], unit="W/m**2")
    # Test output when no kwargs are set.
    lx_test = goes._goes_lx(longflux[:2], shortflux[:2])
    lx_expected = {
        "longlum": Quantity([1.98649103e18, 1.98649103e18], unit="W"),
        "shortlum": Quantity([1.98649103e17, 1.98649103e17], unit="W"),
    }
    assert sorted(lx_test.keys()) == sorted(lx_expected.keys())
    assert_quantity_allclose(lx_test["longlum"], lx_expected["longlum"], rtol=0.1)
    assert_quantity_allclose(lx_test["shortlum"], lx_expected["shortlum"], rtol=0.1)


def test_goes_lx_date():
    # Define input values of flux and time.
    longflux = Quantity([7e-6, 7e-6, 7e-6, 7e-6, 7e-6, 7e-6], unit="W/m**2")
    shortflux = Quantity([7e-7, 7e-7, 7e-7, 7e-7, 7e-7, 7e-7], unit="W/m**2")
    # Test output when date kwarg is set.
    lx_test = goes._goes_lx(longflux[:2], shortflux[:2], date="2014-04-21")
    lx_expected = {
        "longlum": Quantity([1.98649103e18, 1.98649103e18], unit="W"),
        "shortlum": Quantity([1.98649103e17, 1.98649103e17], unit="W"),
    }
    assert sorted(lx_test.keys()) == sorted(lx_expected.keys())
    assert_quantity_allclose(lx_test["longlum"], lx_expected["longlum"], rtol=0.001)
    assert_quantity_allclose(lx_test["shortlum"], lx_expected["shortlum"], rtol=0.001)


def test_goes_lx_obstime():
    # Define input values of flux and time.
    longflux = Quantity([7e-6, 7e-6, 7e-6, 7e-6, 7e-6, 7e-6], unit="W/m**2")
    shortflux = Quantity([7e-7, 7e-7, 7e-7, 7e-7, 7e-7, 7e-7], unit="W/m**2")
    obstime = np.array(
        [
            parse_time((2014, 1, 1, 0, 0, 0)),
            parse_time((2014, 1, 1, 0, 0, 2)),
            parse_time((2014, 1, 1, 0, 0, 4)),
            parse_time((2014, 1, 1, 0, 0, 6)),
            parse_time((2014, 1, 1, 0, 0, 8)),
            parse_time((2014, 1, 1, 0, 0, 10)),
        ],
        dtype=object,
    )
    # Test output when obstime and cumulative kwargs are set.
    lx_test = goes._goes_lx(longflux, shortflux, obstime)
    lx_expected = {
        "longlum": 1.96860565e18 * Quantity(np.ones(6), unit="W"),
        "shortlum": 1.96860565e17 * Quantity(np.ones(6), unit="W"),
        "longlum_int": Quantity([1.96860565e19], unit="J"),
        "shortlum_int": Quantity([1.96860565e18], unit="J"),
        "longlum_cumul": Quantity(
            [3.93721131e18, 7.87442262e18, 1.18116339e19, 1.57488452e19, 1.96860565e19],
            unit="J",
        ),
        "shortlum_cumul": Quantity(
            [3.93721131e17, 7.87442262e17, 1.18116339e18, 1.57488452e18, 1.96860565e18],
            unit="J",
        ),
    }
    assert sorted(lx_test.keys()) == sorted(lx_expected.keys())
    assert_quantity_allclose(lx_test["longlum"], lx_expected["longlum"], rtol=0.1)
    assert_quantity_allclose(lx_test["shortlum"], lx_expected["shortlum"], rtol=0.1)
    assert_quantity_allclose(
        lx_test["longlum_int"], lx_expected["longlum_int"], rtol=0.1
    )
    assert_quantity_allclose(
        lx_test["shortlum_int"], lx_expected["shortlum_int"], rtol=0.1
    )
    assert_quantity_allclose(
        lx_test["longlum_cumul"], lx_expected["longlum_cumul"], rtol=0.1
    )
    assert_quantity_allclose(
        lx_test["shortlum_cumul"], lx_expected["shortlum_cumul"], rtol=0.1
    )


def test_flux_to_classletter():
    """
    Test converting fluxes into a class letter.
    """
    fluxes = Quantity(10 ** (-np.arange(9, 2.0, -1)), "W/m**2")
    classesletter = ["A", "A", "B", "C", "M", "X", "X"]
    calculated_classesletter = [goes.flux_to_flareclass(f)[0] for f in fluxes]
    calculated_classnumber = [float(goes.flux_to_flareclass(f)[1:]) for f in fluxes]
    assert_array_equal(classesletter, calculated_classesletter)
    assert_array_equal([0.1, 1, 1, 1, 1, 1, 10], calculated_classnumber)
    # now test the Examples
    assert goes.flux_to_flareclass(1e-08 * u.watt / u.m**2) == "A1"
    assert goes.flux_to_flareclass(0.00682 * u.watt / u.m**2) == "X68.2"
    assert goes.flux_to_flareclass(7.8e-09 * u.watt / u.m**2) == "A0.78"
    assert goes.flux_to_flareclass(0.00024 * u.watt / u.m**2) == "X2.4"
    assert goes.flux_to_flareclass(4.7e-06 * u.watt / u.m**2) == "C4.7"
    assert goes.flux_to_flareclass(6.9e-07 * u.watt / u.m**2) == "B6.9"
    assert goes.flux_to_flareclass(2.1e-05 * u.watt / u.m**2) == "M2.1"


def test_class_to_flux():
    classes = ["A3.49", "A0.23", "M1", "X2.3", "M5.8", "C2.3", "B3.45", "X20"]
    results = Quantity(
        [3.49e-8, 2.3e-9, 1e-5, 2.3e-4, 5.8e-5, 2.3e-6, 3.45e-7, 2e-3], "W/m2"
    )
    for c, r in zip(classes, results):
        assert_almost_equal(r.value, goes.flareclass_to_flux(c).value)


def test_joint_class_to_flux():
    classes = ["A3.49", "A0.23", "M1", "X2.3", "M5.8", "C2.3", "B3.45", "X20"]
    for c in classes:
        assert c == goes.flux_to_flareclass(goes.flareclass_to_flux(c))


# TODO add a test to check for raising error
