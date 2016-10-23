# This script generates synthetic data along the Cascadia subduction 
# zone.  The east, north, and vertical component of the synthetic data 
# are
#
#   u(x,y) = 0.01*cos(x*w*2*pi)*sin(y*w*2*pi) + eps
#   v(x,y) = 0.01*sin(x*w*2*pi)*cos(y*w*2*pi) + eps
#   z(x,y) = 0.01*cos(x*w*2*pi)*cos(y*w*2*pi) + eps
#
# where w is the cutoff frequency (1.0/400000 km^-1), and eps is white 
# noise with standard deviation 0.005 m.


import numpy as np
import matplotlib.pyplot as plt
import pygeons.interface
import pygeons.ioconv

def make_data(pos,times):
  '''returns synthetic displacements'''
  Nx = len(pos)
  Nt = len(times)
  mean = np.zeros((Nt,Nx,3))
  omega = 1.0/400000.0
  mean[:,:,0] = 0.01*np.cos(pos[:,0]*omega*2*np.pi)*np.sin(pos[:,1]*omega*2*np.pi)
  mean[:,:,1] = 0.01*np.sin(pos[:,0]*omega*2*np.pi)*np.cos(pos[:,1]*omega*2*np.pi)
  mean[:,:,2] = 0.01*np.cos(pos[:,0]*omega*2*np.pi)*np.cos(pos[:,1]*omega*2*np.pi)
  return mean

# load Cascadia GPS station location
lonlat = np.loadtxt('.make_data/lonlat.txt')
pos_geo = np.zeros((lonlat.shape[0],3))
pos_geo[:,0] = lonlat[:,0]
pos_geo[:,1] = lonlat[:,1]

# convert geodetic coordinates to cartesian
bm = pygeons.interface._make_basemap(pos_geo[:,0],pos_geo[:,1],resolution='i')
pos = np.array(bm(pos_geo[:,0],pos_geo[:,1])).T
pos = np.array([pos[:,0],pos[:,1],0*pos[:,0]]).T

time_start = pygeons.dateconv.decday('2000-01-01','%Y-%m-%d')
time_stop = pygeons.dateconv.decday('2000-01-02','%Y-%m-%d')
times = np.arange(int(time_start),int(time_stop))

mean = make_data(pos,times)
sigma = 0.00001*np.ones(mean.shape)
data_dict = {}
data_dict['id'] = np.arange(len(pos)).astype(str)
data_dict['longitude'] = pos_geo[:,0]
data_dict['latitude'] = pos_geo[:,1]
data_dict['time'] = times
data_dict['east'] = mean[:,:,0]
data_dict['north'] = mean[:,:,1]
data_dict['vertical'] = mean[:,:,2]
data_dict['east_std'] = sigma[:,:,0]
data_dict['north_std'] = sigma[:,:,1]
data_dict['vertical_std'] = sigma[:,:,2]
data_dict['time_power'] = 0
data_dict['space_power'] = 1
pygeons.ioconv.csv_from_dict('synthetic.nonoise.csv',data_dict)

mean = make_data(pos,times)
sigma = 0.005*np.ones(mean.shape)
mean += np.random.normal(0.0,sigma)
data_dict = {}
data_dict['id'] = np.arange(len(pos)).astype(str)
data_dict['longitude'] = pos_geo[:,0]
data_dict['latitude'] = pos_geo[:,1]
data_dict['time'] = times
data_dict['east'] = mean[:,:,0]
data_dict['north'] = mean[:,:,1]
data_dict['vertical'] = mean[:,:,2]
data_dict['east_std'] = sigma[:,:,0]
data_dict['north_std'] = sigma[:,:,1]
data_dict['vertical_std'] = sigma[:,:,2]
data_dict['time_power'] = 0
data_dict['space_power'] = 1
pygeons.ioconv.csv_from_dict('synthetic.csv',data_dict)
