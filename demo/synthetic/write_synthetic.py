#!/usr/bin/env python
import numpy as np
import pygeons.ioconv
import pygeons.dateconv
import rbf.halton

Nx = 10
start_time = pygeons.dateconv.decday('2000-01-01','%Y-%m-%d')
stop_time = pygeons.dateconv.decday('2001-01-01','%Y-%m-%d')
time = np.arange(start_time,stop_time+1)

Nt = len(time)
pos = 2*np.pi*(rbf.halton.halton(Nx,2) - 0.5)
lon = pos[:,0] - 84.5
lat = pos[:,1] + 43.0

east = 100*np.sin(lon[None,:])*np.cos(lat[None,:])*np.cos(time[:,None]/365.25)
north = 100*np.cos(lon[None,:])*np.sin(lat[None,:])*np.cos(time[:,None]/365.25)
vertical = 100*np.cos(lon[None,:])*np.cos(lat[None,:])*np.sin(time[:,None]/365.25)

east_std = 0.0*np.ones((Nt,Nx))
north_std = 0.0*np.ones((Nt,Nx))
vertical_std = 0.0*np.ones((Nt,Nx))
id = np.arange(Nx).astype(str)

data = {'time':time,
        'longitude':lon,
        'latitude':lat,
        'id':id,
        'east':east,
        'north':north,
        'vertical':vertical,
        'east_std':east_std,
        'north_std':north_std,
        'vertical_std':vertical_std}
noisy_data = {'time':time,
        'longitude':lon,
        'latitude':lat,
        'id':id,
        'east':east + 0*np.random.normal(0.0,10.0,(Nt,Nx)),
        'north':north + 0*np.random.normal(0.0,10.0,(Nt,Nx)),
        'vertical':vertical + 0*np.random.normal(0.0,10.0,(Nt,Nx)),
        'east_std':east_std + 10,
        'north_std':north_std + 10,
        'vertical_std':vertical_std + 10}

pygeons.ioconv.file_from_dict('data/synthetic.csv',data)
pygeons.ioconv.file_from_dict('data/synthetic.noise.csv',noisy_data)