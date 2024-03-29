#!/usr/bin/env python3
# Contact: Josh Port (joshua_port@uri.edu) (MODIFICATIONS FOR HBL)
# Requirements: python3, numpy, netCDF4, scipy
#
# Converts HBL wind & OWI pressure data and grid to OWI-NWS13 format
# Based on the COAMPS-TC to OWI converter by Zach Cobell
#
class WindGrid:
    def __init__(self, lon, lat):
        import numpy
        self.__n_longitude = len(lon)
        self.__n_latitude = len(lat)
        self.__d_longitude = round(lon[1] - lon[0], 2)
        self.__d_latitude = round(lat[1] - lat[0], 2)
        self.__lon = numpy.empty([self.__n_latitude, self.__n_longitude], dtype=numpy.float64)
        self.__lat = numpy.empty([self.__n_latitude, self.__n_longitude], dtype=numpy.float64)
        lon = numpy.array(lon)
        lat = numpy.array(lat)
        lon = numpy.where(lon > 180, lon - 360, lon)
        self.__xll = min(lon)
        self.__yll = min(lat)
        self.__xur = max(lon)
        self.__yur = max(lat)
        self.__lon,self.__lat = numpy.meshgrid(lon,lat) #sparse=True is an avenue to explore for saving memory
        self.__lon1d = numpy.array(lon)
        self.__lat1d = numpy.array(lat)

    def lon(self):
        return self.__lon

    def lat(self):
        return self.__lat

    def lon1d(self):
        return self.__lon1d

    def lat1d(self):
        return self.__lat1d

    def d_longitude(self):
        return self.__d_longitude

    def d_latitude(self):
        return self.__d_latitude

    def n_longitude(self):
        return self.__n_longitude

    def n_latitude(self):
        return self.__n_latitude

    def xll(self):
        return self.__xll

    def yll(self):
        return self.__yll

    def xur(self):
        return self.__xur

    def yur(self):
        return self.__yur

    @staticmethod
    def generate_equidistant_grid(grid=None,xll=None,yll=None,xur=None,yur=None,dx=None,dy=None):
        if grid:
            return WindGrid.__generate_equidistant_grid_from_grid(grid)
        if xll and yll and xur and yur and dx and dy:
            return WindGrid.__generate_equidistant_grid_from_corners(xll,yll,xur,yur,dx,dy)
        raise RuntimeError("No valid function call provided")

    @staticmethod
    def __generate_equidistant_grid_from_grid(grid):
        import numpy as np
        x = np.arange(grid.xll(), grid.xur(), grid.d_longitude())
        y = np.arange(grid.yll(), grid.yur(), grid.d_latitude())
        return WindGrid(x,y)

    @staticmethod
    def __generate_equidistant_grid_from_corners(x1,y1,x2,y2,dx,dy):
        import numpy as np
        x = np.arange(x1,x2,dx)
        y = np.arange(y1,y2,dy)
        return WindGrid(x,y)

    @staticmethod
    def interpolate_to_grid(original_grid, original_data, new_grid):
        from scipy import interpolate
        func = interpolate.interp2d(original_grid.lon1d(),original_grid.lat1d(),original_data,kind='linear')
        return func(new_grid.lon1d(),new_grid.lat1d())


class WindData:
    def __init__(self, date, wind_grid, pressure, u_velocity, v_velocity):
        import numpy
        self.__pressure = pressure
        self.__u_velocity = numpy.array(u_velocity)
        self.__v_velocity = numpy.array(v_velocity)
        self.__date = date
        self.__wind_grid = wind_grid

    def date(self):
        return self.__date

    def wind_grid(self):
        return self.__wind_grid
    
    def pressure(self):
        return self.__pressure      

    def u_velocity(self):
        return self.__u_velocity

    def v_velocity(self):
        return self.__v_velocity


class OwiNetcdf:
    def __init__(self, filename, wind_grid, bounds):
        import netCDF4
        from datetime import datetime
        self.__filename = filename
        self.__wind_grid = wind_grid
        self.__bounds = bounds
        self.__nc = netCDF4.Dataset(self.__filename + ".nc", "w")
        self.__nc.group_order = "Main"
        self.__conventions = "OWI-NWS13"
        self.__nc.source = "HBL Wind & OWI Pressure to OWI Netcdf converter"
        self.__nc.author = "Josh Port"
        self.__nc.contact = "joshua_port@uri.edu"
            
        if self.__bounds:
            self.__equidistant_wind_grid = WindGrid.generate_equidistant_grid(
                                        xll=self.__bounds[0],yll=self.__bounds[1],
                                        xur=self.__bounds[2],yur=self.__bounds[3],
                                        dx=self.__bounds[4],dy=self.__bounds[5])

        # Create main group
        self.__group_main = self.__nc.createGroup("Main")
        self.__group_main.rank = 1

        # Create dimensions
        self.__group_main_dim_time = self.__group_main.createDimension("time", None)
        if self.__bounds:
            self.__group_main_dim_longitude = self.__group_main.createDimension("longitude", self.__equidistant_wind_grid.n_longitude())
            self.__group_main_dim_latitude = self.__group_main.createDimension("latitude", self.__equidistant_wind_grid.n_latitude())
        else:
            self.__group_main_dim_longitude = self.__group_main.createDimension("longitude", self.__wind_grid.n_longitude())
            self.__group_main_dim_latitude = self.__group_main.createDimension("latitude", self.__wind_grid.n_latitude())

        # Create variables (with compression)
        self.__group_main_var_time = self.__group_main.createVariable("time", "i4", "time", zlib=True, complevel=2,
                                                                      fill_value=netCDF4.default_fillvals["i4"])
        self.__group_main_var_lon = self.__group_main.createVariable("lon", "f8", ("latitude", "longitude"), zlib=True, complevel=2,
                                                                     fill_value=netCDF4.default_fillvals["f8"])
        self.__group_main_var_lat = self.__group_main.createVariable("lat", "f8", ("latitude", "longitude"), zlib=True, complevel=2,
                                                                     fill_value=netCDF4.default_fillvals["f8"])
        self.__group_main_var_psfc = self.__group_main.createVariable("PSFC", "f4", ("time", "latitude", "longitude"), zlib=True,
                                                                      complevel=2,
                                                                      fill_value=netCDF4.default_fillvals["f4"]) #This will be NaN throughout. Keeping to meet OWI-NWS13 format.
        self.__group_main_var_u10 = self.__group_main.createVariable("U10", "f4", ("time", "latitude", "longitude"), zlib=True,
                                                                     complevel=2,
                                                                     fill_value=netCDF4.default_fillvals["f4"])
        self.__group_main_var_v10 = self.__group_main.createVariable("V10", "f4", ("time", "latitude", "longitude"), zlib=True,
                                                                     complevel=2,
                                                                     fill_value=netCDF4.default_fillvals["f4"])

        # Add attributes to variables
        self.__base_date = datetime(1990, 1, 1, 0, 0, 0)
        self.__group_main_var_time.units = "minutes since 1990-01-01 00:00:00 Z"
        self.__group_main_var_time.axis = "T"
        self.__group_main_var_time.coordinates = "time"

        self.__group_main_var_lon.coordinates = "lat lon"
        self.__group_main_var_lon.units = "degrees_east"
        self.__group_main_var_lon.standard_name = "longitude"
        self.__group_main_var_lon.axis = "x"

        self.__group_main_var_lat.coordinates = "lat lon"
        self.__group_main_var_lat.units = "degrees_north"
        self.__group_main_var_lat.standard_name = "latitude"
        self.__group_main_var_lat.axis = "y"
        
        self.__group_main_var_psfc.units = "mb"
        self.__group_main_var_psfc.coordinates = "time lat lon"        

        self.__group_main_var_u10.units = "m s-1"
        self.__group_main_var_u10.coordinates = "time lat lon"

        self.__group_main_var_v10.units = "m s-1"
        self.__group_main_var_v10.coordinates = "time lat lon"

        if self.__bounds:
            self.__group_main_var_lat[:] = self.__equidistant_wind_grid.lat()
            self.__group_main_var_lon[:] = self.__equidistant_wind_grid.lon()
        else:
            self.__group_main_var_lat[:] = wind_grid.lat()
            self.__group_main_var_lon[:] = wind_grid.lon()

    def append(self, idx, wind_data):
        delta = (wind_data.date() - self.__base_date)
        minutes = round((delta.days * 86400 + delta.seconds) / 60)

        if self.__bounds:
            press = WindGrid.interpolate_to_grid(wind_data.wind_grid(),wind_data.pressure(),self.__equidistant_wind_grid)
            u_vel = WindGrid.interpolate_to_grid(wind_data.wind_grid(),wind_data.u_velocity(),self.__equidistant_wind_grid)
            v_vel = WindGrid.interpolate_to_grid(wind_data.wind_grid(),wind_data.v_velocity(),self.__equidistant_wind_grid)
        else:
            press = wind_data.pressure()
            u_vel = wind_data.u_velocity()
            v_vel = wind_data.v_velocity()

        self.__group_main_var_time[idx] = minutes
        self.__group_main_var_psfc[idx, :, :] = press       
        self.__group_main_var_u10[idx, :, :] = u_vel
        self.__group_main_var_v10[idx, :, :] = v_vel

    def close(self):
        self.__nc.close()

    
class OwiAscii:
    # NOTE: This class assumes the same number of grid points in each time slice.
    # The conversion will fail if this isn't the case.
    def __init__(self, u_filename, v_filename, pre_filename, idx):
        self.__u_filename = u_filename
        self.__v_filename = v_filename
        self.__pre_filename = pre_filename
        self.__idx = idx
        self.__num_lats = self.__get_num_lats()
        self.__num_lons = self.__get_num_lons()
        self.__pre_idx_header_row = self.__get_pre_idx_header_row()
        self.__date = self.__get_date()
        self.__grid = self.__get_grid()

    def date(self):
        return self.__date

    def grid(self):
        return self.__grid
    
    def __get_num_lats(self):
        pre_file = open(self.__pre_filename, 'r')
        lines = pre_file.readlines()
        num_lats = lines[1][5:9]
        pre_file.close()
        return int(num_lats)
    
    def __get_num_lons(self):
        pre_file = open(self.__pre_filename, 'r')
        lines = pre_file.readlines()
        num_lons = lines[1][15:19]
        pre_file.close()
        return int(num_lons)    
            
    def __get_pre_idx_header_row(self):
        from math import ceil
        return 1 + ceil((self.__num_lats * self.__num_lons) / 8) * self.__idx + self.__idx

    def __get_date(self):
        from datetime import datetime
        pre_file = open(self.__pre_filename, 'r')
        lines = pre_file.readlines()
        date_str = lines[self.__pre_idx_header_row][68:80]
        idx_date = datetime(int(date_str[0:4]), int(date_str[4:6]), int(date_str[6:8]), int(date_str[8:10]), int(date_str[10:12]))
        pre_file.close()
        return idx_date
    
    def __get_grid(self):
        from numpy import linspace
        pre_file = open(self.__pre_filename, 'r')
        lines = pre_file.readlines()
        lat_step = float(lines[self.__pre_idx_header_row][31:37])
        lon_step = float(lines[self.__pre_idx_header_row][22:28])
        sw_corner_lat = float(lines[self.__pre_idx_header_row][43:51])
        sw_corner_lon = float(lines[self.__pre_idx_header_row][57:65])
        lat = linspace(sw_corner_lat, sw_corner_lat + (self.__num_lats - 1) * lat_step, self.__num_lats)
        lon = linspace(sw_corner_lon, sw_corner_lon + (self.__num_lons - 1) * lon_step, self.__num_lons)
        pre_file.close()
        return WindGrid(lon, lat)

    def get(self):
        from math import floor
        from netCDF4 import Dataset
        from scipy.interpolate import interp2d    
        pre_file = open(self.__pre_filename, 'r')
        lines = pre_file.readlines()
        prmsl = [[None for i in range(self.__num_lons)] for j in range(self.__num_lats)]
        for i in range(self.__num_lats * self.__num_lons):
            low_idx = 1 + 10 * (i % 8)
            high_idx = 10 + 10 * (i % 8)
            line_idx = self.__pre_idx_header_row + 1 + floor(i / 8)
            lon_idx = i % self.__num_lons
            lat_idx = floor(i / self.__num_lons)
            prmsl[lat_idx][lon_idx] = float(lines[line_idx][low_idx:high_idx])
        pre_file.close()
        
        # Interpolate wind speed from HBL data at OWI grid points
        hbl_idx = (self.__idx-384) * 15 #OWI ASCII starts way earlier in time and has a 15 minute step. This makes the indices line up.
        f_u = Dataset(self.__u_filename, 'r')
        f_v = Dataset(self.__v_filename, 'r')
        hbl_lon = f_u.variables["lon"][:] # Some files have had this as "loni"; change if you get an error
        hbl_lat = f_u.variables["lat"][:] # Some files have had this as "lati"; change if you get an error
        hbl_uvel = f_u.variables["u10"][:][:][hbl_idx]
        owi_lon = self.__grid.lon1d()
        owi_lat = self.__grid.lat1d()
        u_interpolant = interp2d(hbl_lon, hbl_lat, hbl_uvel)
        u_interp = u_interpolant(owi_lon, owi_lat)
        del hbl_uvel # Save RAM
        f_u.close()
        hbl_vvel = f_v.variables["v10"][:][:][hbl_idx]
        v_interpolant = interp2d(hbl_lon, hbl_lat, hbl_vvel)
        v_interp = v_interpolant(owi_lon, owi_lat)
        del hbl_vvel # Save RAM
        f_v.close()
                
        return WindData(self.__date, self.__grid, prmsl, u_interp, v_interp)    

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Convert HBL output to alternate formats")

    # Arguments
    parser.add_argument("files", metavar="file", type=str, help="Files to be converted; must be exactly three with ""u"" file listed first, ""v"" file listed second, and OWI ASCII PRE file listed third", nargs='+')
    parser.add_argument("-f", metavar="fmt", type=str,
                        help="Format of output file (netcdf). Default: netcdf",
                        default="netcdf")
    parser.add_argument("-o", metavar="outfile", type=str,
                        help="Name of output file to be created. Default: [fort].nc|[fort].221,.222|[fort].amu,amv,amp",
                        required=True, default="fort")
    parser.add_argument("-b", metavar="x1,y1,x2,y2,dx,dy", type=str, help="Bounding box. Default: None",default=None,nargs=6)

    # Read the command line arguments
    args = parser.parse_args()

    file_list = args.files
    num_files = len(file_list)
    if num_files == 0:
        raise RuntimeError("No files found for conversion")
    if num_files != 3:
        raise RuntimeError("Must specify exactly five files with the ""u"" file listed first, the ""v"" file listed second, p2 ""u"" file listed first, p2 ""v"" file listed second, and the OWI ASCII PRE file listed third")

    if args.b:
        bounds = [float(args.b[0]),float(args.b[1]),float(args.b[2]),
                  float(args.b[3]),float(args.b[4]),float(args.b[5])]
        if not len(bounds) == 6:
            raise RuntimeError("Incorrectly formatted bounding box")
    else:
        bounds = None

    output_format = args.f

    wind = None
    num_times = 216; # 3250 HBL time slices / 15 minute OWI temporal resolution (no remainder)

    time_index = 384 #This needs to updated based on how the HBL and OWI files' times line up. Manual for now.
    while time_index - 384 < num_times: #This, plus making our data file class time-slice specific, lets us maintain the old OwiNetcdf class granularity and diverge less from the original code
        owi_ascii = OwiAscii(file_list[0], file_list[1], file_list[2], time_index)
        print("INFO: Processing time slice {:d} of {:d}".format(time_index - 384 + 1, num_times), flush=True)
        wind_data = owi_ascii.get()
        if not wind:
            if output_format == "netcdf":
                wind = OwiNetcdf(args.o, wind_data.wind_grid(), bounds)
            else:
                raise RuntimeError("Invalid output format selected")
        wind.append(time_index - 384, wind_data)
        time_index += 1  
    
    wind.close()

if __name__ == '__main__':
    main()
