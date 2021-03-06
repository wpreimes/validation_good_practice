
import os

import numpy as np
import pandas as pd

from netCDF4 import Dataset

from validation_good_practice.ancillary.paths import Paths

def reshuffle_smos():

    paths = Paths()

    # Collect all nc files
    path = paths.smos / 'raw' / 'MIR_SMUDP2_nc'
    nc_files = sorted(path.glob('**/*.nc'))

    # Get time stamp as the mean of start-of-orbit and end-of-orbit
    sdate = pd.to_datetime([str(f)[-44:-29] for f in nc_files])
    edate = pd.to_datetime([str(f)[-28:-13] for f in nc_files])
    dates = (sdate + (edate - sdate) / 2.).round('min')

    # get a list of all CONUS gpis
    gpi_lut = pd.read_csv(paths.lut, index_col=0)['smos_gpi']
    ease_gpis = gpi_lut.index.values

    # Array with ALL possible dates and ALL CONUS gpis
    res_arr = np.full((len(dates),len(ease_gpis)), np.nan)

    # Fill in result array from orbit files
    for i, f in enumerate(nc_files):
        print("%i / %i" % (i, len(nc_files)))

        ds = Dataset(f)
        smos_gpis = ds.variables['Grid_Point_ID'][:]

        # Check for valid data within orbit files
        for res_ind, ease_gpi in enumerate(ease_gpis):
            smos_ind = np.where(smos_gpis == gpi_lut.loc[ease_gpi])[0]
            if len(smos_ind) > 0:

                sm = float(ds.variables['Soil_Moisture'][smos_ind])
                if np.isnan(sm) | (sm < 0.):
                    continue

                rfi = float(ds.variables['RFI_Prob'][smos_ind])
                chi_2_p = float(ds.variables['Chi_2_P'][smos_ind])
                valid = (rfi < 0.1) & (chi_2_p > 0.05)

                # cf = float(ds.variables['Confidence_Flags'][smos_ind])
                # if np.isnan(cf):
                #     continue
                # cf = int(cf)
                # sf = long(ds.variables['Science_Flags'][smos_ind])
                #
                # valid = ((cf & 1 << 1) | (cf & 1 << 2) | (cf & 1 << 4) | (cf & 1 << 5) | (cf & 1 << 6) |
                #         (sf & 1 << 5) | (sf & 1 << 16) | (sf & 1 << 18) | (sf & 1 << 19) | (sf & 1 << 26) == 0) & \
                #         (rfi < 0.1)

                if valid:
                    res_arr[i, res_ind] = sm

        ds.close()

    # Write out valid time series of all CONIS GPIS into separate .csv files
    dir_out = paths.smos / 'timeseries'
    for i, gpi in enumerate(ease_gpis):
        Ser = pd.Series(res_arr[:,i],index=dates).dropna()
        if len(Ser) > 0:
            Ser = Ser.groupby(Ser.index).last()
            fname = dir_out / ('%i.csv' % gpi)
            Ser.to_csv(fname,float_format='%.4f')

if __name__=='__main__':
    reshuffle_smos()

