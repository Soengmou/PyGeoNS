''' 
Defines functions which are called by the PyGeoNS executables. These 
are the highest level of plotting functions. There is a vector 
plotting function and a strain plotting function. Both take data 
dictionaries as input, as well as additional plotting parameters.
'''
from __future__ import division
import numpy as np
import matplotlib.pyplot as plt
import logging
from pygeons.plot.iview import interactive_viewer
from pygeons.plot.istrain import interactive_strain_viewer
from pygeons.mjd import mjd_inv
from pygeons.basemap import make_basemap
from pygeons.breaks import make_space_vert_smp
logger = logging.getLogger(__name__)


def _unit_string(space_power,time_power):
  ''' 
  returns a string indicating the units
  '''
  if (space_power == 0) & (time_power == 0):
    return ''

  if space_power == 0:
    space_str = '1'
  elif space_power == 1:
    space_str = 'mm'
  else:
    space_str = 'mm^%s' % space_power

  if time_power == 0:
    time_str = ''
  elif time_power == -1:
    time_str = '/yr'
  else:
    time_str = '/yr^%s' % -time_power
  
  return space_str + time_str
        

def _unit_conversion(space_power,time_power):
  ''' 
  returns the scalar which converts 
  
    meters**(space_power) * days*(time_power)
  
  to   

    mm**(space_power) * years*(time_power)
  '''
  return 1000**space_power * (1.0/365.25)**time_power
  

def _get_meridians_and_parallels(bm,ticks):
  ''' 
  attempts to find nice locations for the meridians and parallels 
  '''
  diff_lon = (bm.urcrnrlon-bm.llcrnrlon)
  round_digit = int(np.ceil(np.log10(ticks/diff_lon)))
  dlon = np.round(diff_lon/ticks,round_digit)

  diff_lat = (bm.urcrnrlat-bm.llcrnrlat)
  round_digit = int(np.ceil(np.log10(ticks/diff_lat)))
  dlat = np.round(diff_lat/ticks,round_digit)

  # round down to the nearest rounding digit
  lon_low = np.floor(bm.llcrnrlon*10**round_digit)/10**round_digit
  lat_low = np.floor(bm.llcrnrlat*10**round_digit)/10**round_digit
  # round up to the nearest rounding digit
  lon_high = np.ceil(bm.urcrnrlon*10**round_digit)/10**round_digit
  lat_high = np.ceil(bm.urcrnrlat*10**round_digit)/10**round_digit

  meridians = np.arange(lon_low,lon_high+dlon,dlon)
  parallels = np.arange(lat_low,lat_high+dlat,dlat)
  return meridians,parallels
  

def _setup_map_ax(bm,ax):
  ''' 
  prepares the map axis for display
  '''
  # function which prints out the coordinates on the bottom left 
  # corner of the figure
  def coord_string(x,y):                         
    str = 'x : %g  y : %g  ' % (x,y)
    str += '(lon : %g E  lat : %g N)' % bm(x,y,inverse=True)
    return str 

  ax.format_coord = coord_string
  bm.drawcountries(ax=ax)
  bm.drawstates(ax=ax) 
  bm.drawcoastlines(ax=ax)
  mer,par =  _get_meridians_and_parallels(bm,3)
  bm.drawmeridians(mer,
                   labels=[0,0,0,1],dashes=[2,2],
                   ax=ax,zorder=1,color=(0.3,0.3,0.3,1.0))
  bm.drawparallels(par,
                   labels=[1,0,0,0],dashes=[2,2],
                   ax=ax,zorder=1,color=(0.3,0.3,0.3,1.0))
  return
                     

def _setup_ts_ax(ax_lst,times):
  ''' 
  prepares the time series axes for display
  '''
  # display time in MJD and date on time series plot
  def ts_coord_string(x,y):                         
    str = 'time : %g  ' % x
    str += '(date : %s)' % mjd_inv(x,'%Y-%m-%d')
    return str 

  ticks = np.linspace(times.min(),times.max(),13)[1:-1:2]
  ticks = np.round(ticks)
  tick_labels = [mjd_inv(t,'%Y-%m-%d') for t in ticks]
  ax_lst[2].set_xticks(ticks)
  ax_lst[2].set_xticklabels(tick_labels)
  ax_lst[0].format_coord = ts_coord_string
  ax_lst[1].format_coord = ts_coord_string
  ax_lst[2].format_coord = ts_coord_string
  return


def pygeons_view(data_list,resolution='i',
                 break_lons=None,break_lats=None,
                 break_conn=None,**kwargs):
  ''' 
  runs the PyGeoNS interactive Viewer
  
  Parameters
  ----------
    data_list : (N,) list of dicts
      list of data dictionaries being plotted
      
    resolution : str
      basemap resolution
    
    break_lons : (N,) array

    break_lats : (N,) array

    break_con : (M,) array   
      
    **kwargs :
      gets passed to pygeons.plot.view.interactive_view

  '''
  for d in data_list:
    d.check_self_consistency()
  for d in data_list[1:]:
    d.check_compatibility(data_list[0])

  t = data_list[0]['time']
  lon = data_list[0]['longitude']
  lat = data_list[0]['latitude']
  id = data_list[0]['id']
  dates = [mjd_inv(ti,'%Y-%m-%d') for ti in t]
  conv = _unit_conversion(data_list[0]['space_power'],
                          data_list[0]['time_power'])
  units = _unit_string(data_list[0]['space_power'],
                       data_list[0]['time_power'])
  u = [conv*d['east'] for d in data_list]
  v = [conv*d['north'] for d in data_list]
  z = [conv*d['vertical'] for d in data_list]
  su = [conv*d['east_std'] for d in data_list]
  sv = [conv*d['north_std'] for d in data_list]
  sz = [conv*d['vertical_std'] for d in data_list]
  ts_fig,ts_ax = plt.subplots(3,1,sharex=True,num='Time Series View',
                              facecolor='white')
  _setup_ts_ax(ts_ax,data_list[0]['time'])
  map_fig,map_ax = plt.subplots(num='Map View',facecolor='white')
  bm = make_basemap(lon,lat,resolution=resolution)
  _setup_map_ax(bm,map_ax)
  # draw breaks if there are any
  vert,smp = make_space_vert_smp(break_lons,break_lats,
                                 break_conn,bm)
  for s in smp:
    map_ax.plot(vert[s,0],vert[s,1],'k--',lw=2,zorder=2)

  x,y = bm(lon,lat)
  pos = np.array([x,y]).T
  interactive_viewer(
    t,pos,u=u,v=v,z=z,su=su,sv=sv,sz=sz,
    ts_ax=ts_ax,map_ax=map_ax,
    station_labels=id,time_labels=dates,
    units=units,**kwargs)

  return


def pygeons_strain(data_dx,data_dy,resolution='i',
                   break_lons=None,break_lats=None,
                   break_conn=None,**kwargs):
  ''' 
  runs the PyGeoNS Interactive Strain Viewer
  
  Parameters
  ----------
    data_dx : x derivative data dictionaries 

    data_dy : y derivative data dictionaries 
      
    resolution : str
      basemap resolution
      
    break_lons : (N,) array

    break_lats : (N,) array

    break_con : (M,) array   

    **kwargs :
      gets passed to pygeons.strain.view

  '''
  data_dx.check_self_consistency()
  data_dy.check_self_consistency()
  data_dx.check_compatibility(data_dy)
  if (data_dx['space_power'] != 0) | data_dy['space_power'] != 0:
    raise ValueError('data sets cannot have spatial units')
  
  t = data_dx['time']
  lon = data_dx['longitude']
  lat = data_dx['latitude']
  dates = [mjd_inv(ti,'%Y-%m-%d') for ti in t]
  conv = _unit_conversion(data_dx['space_power'],
                          data_dx['time_power'])
  units = _unit_string(data_dx['space_power'],
                       data_dx['time_power'])
  ux = conv*data_dx['east']
  sux = conv*data_dx['east_std']
  vx = conv*data_dx['north']
  svx = conv*data_dx['north_std']
  uy = conv*data_dy['east']
  suy = conv*data_dy['east_std']
  vy = conv*data_dy['north']
  svy = conv*data_dy['north_std']
  fig,ax = plt.subplots(num='Map View',facecolor='white')
  bm = make_basemap(lon,lat,resolution=resolution)
  _setup_map_ax(bm,ax)
  # draw breaks if there are any
  vert,smp = make_space_vert_smp(break_lons,break_lats,
                                 break_conn,bm)
  for s in smp:
    ax.plot(vert[s,0],vert[s,1],'k--',lw=2,zorder=2)

  ## draw map scale
  # find point 0.1,0.1
  # XXXXXXXXXXXX 
  scale_lon,scale_lat = bm(*ax.transData.inverted().transform(ax.transAxes.transform([0.15,0.1])),inverse=True)
  bm.drawmapscale(scale_lon,scale_lat,scale_lon,scale_lat,150,ax=ax,barstyle='fancy',fontsize=10)
  # XXXXXXXXXXXX 

  x,y = bm(lon,lat)
  pos = np.array([x,y]).T
  interactive_strain_viewer(
    t,pos,ux,uy,vx,vy,sux,suy,svx,svy,
    ax=ax,time_labels=dates,units=units,**kwargs)

  return
