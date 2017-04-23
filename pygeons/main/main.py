''' 
Defines the main filtering functions which are called by the 
PyGeoNS executable.
'''
from __future__ import division
import numpy as np
import logging
import subprocess as sp
from pygeons.main.reml import reml
from pygeons.main.strain import strain
from pygeons.main.autoclean import autoclean
from pygeons.main.gprocs import get_units
from pygeons.mjd import mjd_inv,mjd
from pygeons.basemap import make_basemap
from pygeons.io.convert import dict_from_hdf5,hdf5_from_dict
logger = logging.getLogger(__name__)


def _params_dict(b):
  ''' 
  coerce the list *b* into a dictionary of hyperparameters for each
  direction. The dictionary keys are 'east', 'north', and 'vertical'.
  The dictionary values are each an N array of hyperparameters.
  
    >>> b1 = [1.0,2.0]
    >>> b2 = ['1.0','2.0']
    >>> b3 = ['east','1.0','2.0','north','1.0','2.0','vertical','1.0','2.0']
  
  '''
  b = list(b)
  msg = ('the hyperparameters must be a list of N floats or 3 lists '
         'of N floats where each list is preceded by "east", "north", '
         'or "vertical"')

  if ('east' in b) & ('north' in b) & ('vertical' in b):
    if (len(b) % 3) != 0:
      raise ValueError(msg)

    arr = np.reshape(b,(3,-1))
    dirs = arr[:,0].astype(str) # directions
    vals = arr[:,1:].astype(float) # hyperparameter array
    out = dict(zip(dirs,vals))
    # make sure the keys contain 'east', 'north', and 'vertical'
    if set(out.keys()) != set(['east','north','vertical']):
      raise ValueError(msg)

  else:
    try:
      arr = np.array(b,dtype=float)
    except ValueError:
      raise ValueError(msg)

    out = {'east':arr,
           'north':arr,
           'vertical':arr}

  return out


def _remove_extension(f):
  '''remove file extension if one exists'''
  if '.' not in f:
    return f
  else:
    return '.'.join(f.split('.')[:-1])


def _log_autoclean(input_file,
                   network_model,network_params, 
                   station_model,station_params,
                   outlier_tol,
                   output_edited_file,output_fit_file):
  msg  = '\n'                     
  msg += '------------- PYGEONS AUTOCLEAN RUN INFORMATION --------------\n\n'
  msg += 'input file : %s\n' % input_file
  msg += 'network :\n' 
  msg += '    model : %s\n' % ', '.join(network_model)
  msg += '    parameter units : %s\n' % ', '.join(get_units(network_model))
  msg += '    east parameters : %s\n' % ', '.join(['%0.4e' % i for i in network_params['east']])
  msg += '    north parameters : %s\n' % ', '.join(['%0.4e' % i for i in network_params['north']])
  msg += '    vertical parameters : %s\n' % ', '.join(['%0.4e' % i for i in network_params['vertical']])
  msg += 'station :\n' 
  msg += '    model : %s\n' % ', '.join(station_model)
  msg += '    parameter units : %s\n' % ', '.join(get_units(station_model))
  msg += '    east parameters : %s\n' % ', '.join(['%0.4e' % i for i in station_params['east']])
  msg += '    north parameters : %s\n' % ', '.join(['%0.4e' % i for i in station_params['north']])
  msg += '    vertical parameters : %s\n' % ', '.join(['%0.4e' % i for i in station_params['vertical']])
  msg += 'outlier tolerance : %s\n' % outlier_tol  
  msg += 'output edited file : %s\n' % output_edited_file  
  msg += 'output fit file : %s\n\n' % output_fit_file  
  msg += '--------------------------------------------------------------\n'
  logger.info(msg)
  return 


def _log_reml(input_file,
              network_model,network_params,network_fix, 
              station_model,station_params,station_fix,
              output_file):
  msg  = '\n'                     
  msg += '---------------- PYGEONS REML RUN INFORMATION ----------------\n\n'
  msg += 'input file : %s\n' % input_file
  msg += 'network :\n' 
  msg += '    model : %s\n' % ', '.join(network_model)
  msg += '    parameter units : %s\n' % ', '.join(get_units(network_model))
  msg += '    fixed parameters : %s\n' % ', '.join(network_fix.astype(str))
  msg += '    initial east parameters : %s\n' % ', '.join(['%0.4e' % i for i in network_params['east']])
  msg += '    initial north parameters : %s\n' % ', '.join(['%0.4e' % i for i in network_params['north']])
  msg += '    initial vertical parameters : %s\n' % ', '.join(['%0.4e' % i for i in network_params['vertical']])
  msg += 'station :\n' 
  msg += '    model : %s\n' % ', '.join(station_model)
  msg += '    parameter units : %s\n' % ', '.join(get_units(station_model))
  msg += '    fixed parameters : %s\n' % ', '.join(station_fix.astype(str))
  msg += '    initial east parameters : %s\n' % ', '.join(['%0.4e' % i for i in station_params['east']])
  msg += '    initial north parameters : %s\n' % ', '.join(['%0.4e' % i for i in station_params['north']])
  msg += '    initial vertical parameters : %s\n' % ', '.join(['%0.4e' % i for i in station_params['vertical']])
  msg += 'output file : %s\n\n' % output_file  
  msg += '--------------------------------------------------------------\n'
  logger.info(msg)
  return msg


def _log_reml_results(input_file,
                      network_model,network_params,network_fix, 
                      station_model,station_params,station_fix,
                      likelihood,output_file):
  msg  = '\n'                     
  msg += '-------------------- PYGEONS REML RESULTS --------------------\n\n'
  msg += 'input file : %s\n' % input_file
  msg += 'network :\n' 
  msg += '    model : %s\n' % ' '.join(network_model)
  msg += '    parameter units : %s\n' % ', '.join(get_units(network_model))
  msg += '    fixed parameters : %s\n' % ', '.join(network_fix.astype(str))
  msg += '    optimal east parameters : %s\n' % ', '.join(['%0.4e' % i for i in network_params['east']])
  msg += '    optimal north parameters : %s\n' % ', '.join(['%0.4e' % i for i in network_params['north']])
  msg += '    optimal vertical parameters : %s\n' % ', '.join(['%0.4e' % i for i in network_params['vertical']])
  msg += 'station :\n' 
  msg += '    model : %s\n' % ' '.join(station_model)
  msg += '    parameter units : %s\n' % ', '.join(get_units(station_model))
  msg += '    fixed parameters : %s\n' % ', '.join(station_fix.astype(str))
  msg += '    optimal east parameters : %s\n' % ', '.join(['%0.4e' % i for i in station_params['east']])
  msg += '    optimal north parameters : %s\n' % ', '.join(['%0.4e' % i for i in station_params['north']])
  msg += '    optimal vertical parameters : %s\n' % ', '.join(['%0.4e' % i for i in station_params['vertical']])
  msg += 'log likelihood :\n' 
  msg += '    east : %s\n' % likelihood['east']
  msg += '    north : %s\n' % likelihood['north']
  msg += '    vertical : %s\n' % likelihood['vertical']
  msg += 'output file : %s\n\n' % output_file  
  msg += '--------------------------------------------------------------\n'
  logger.info(msg)
  return msg
  

def _log_strain(input_file,
                network_prior_model,network_prior_params, 
                network_noise_model,network_noise_params, 
                station_noise_model,station_noise_params, 
                start_date,stop_date,positions,
                output_dx_file,output_dy_file):
  msg  = '\n'
  msg += '--------------- PYGEONS STRAIN RUN INFORMATION ---------------\n\n'
  msg += 'input file : %s\n' % input_file
  msg += 'network prior :\n' 
  msg += '    model : %s\n' % ', '.join(network_prior_model)
  msg += '    parameter units : %s\n' % ', '.join(get_units(network_prior_model))
  msg += '    east parameters : %s\n' % ', '.join(['%0.4e' % i for i in network_prior_params['east']])
  msg += '    north parameters : %s\n' % ', '.join(['%0.4e' % i for i in network_prior_params['north']])
  msg += '    vertical parameters : %s\n' % ', '.join(['%0.4e' % i for i in network_prior_params['vertical']])
  msg += 'network noise :\n' 
  msg += '    model : %s\n' % ' '.join(network_noise_model)
  msg += '    parameter units : %s\n' % ', '.join(get_units(network_noise_model))
  msg += '    east parameters : %s\n' % ', '.join(['%0.4e' % i for i in network_noise_params['east']])
  msg += '    north parameters : %s\n' % ', '.join(['%0.4e' % i for i in network_noise_params['north']])
  msg += '    vertical parameters : %s\n' % ', '.join(['%0.4e' % i for i in network_noise_params['vertical']])
  msg += 'station noise :\n' 
  msg += '    model : %s\n' % ' '.join(station_noise_model)
  msg += '    parameter units : %s\n' % ', '.join(get_units(station_noise_model))
  msg += '    east parameters : %s\n' % ', '.join(['%0.4e' % i for i in station_noise_params['east']])
  msg += '    north parameters : %s\n' % ', '.join(['%0.4e' % i for i in station_noise_params['north']])
  msg += '    vertical parameters : %s\n' % ', '.join(['%0.4e' % i for i in station_noise_params['vertical']])
  msg += 'output start date : %s\n' % start_date
  msg += 'output stop date : %s\n' % stop_date
  if positions is None:
    msg += 'output positions file : < using same positions as input >\n'
  else:   
    msg += 'output positions file : %s\n' % positions

  msg += 'output east derivative file : %s\n' % output_dx_file
  msg += 'output north derivative file : %s\n\n' % output_dy_file
  msg += '--------------------------------------------------------------\n'
  logger.info(msg)
  

def pygeons_autoclean(input_file,
                      network_model=('se-se',),
                      network_params=(1.0,0.05,50.0),
                      station_model=('p0',),
                      station_params=(),
                      output_stem=None,
                      outlier_tol=4.0):
  ''' 
  Remove outliers with a data editing algorithm
  '''
  logger.info('Running pygeons autoclean ...')
  data = dict_from_hdf5(input_file)
  if data['time_exponent'] != 0:
    raise ValueError('input dataset must have units of displacement')

  if data['space_exponent'] != 1:
    raise ValueError('input dataset must have units of displacement')

  out_edited = dict((k,np.copy(v)) for k,v in data.iteritems())
  out_fit = dict((k,np.copy(v)) for k,v in data.iteritems())

  # convert params to a dictionary of hyperparameters for each direction
  network_params = _params_dict(network_params)
  station_params = _params_dict(station_params)

  # make output file name
  if output_stem is None:
    output_stem = _remove_extension(input_file) + '.autoclean'

  output_edited_file = output_stem + '.edited.h5'
  output_fit_file = output_stem + '.fit.h5'
  
  # convert geodetic positions to cartesian
  bm = make_basemap(data['longitude'],data['latitude'])
  x,y = bm(data['longitude'],data['latitude'])
  xy = np.array([x,y]).T

  _log_autoclean(input_file,
                 network_model,network_params,
                 station_model,station_params,
                 outlier_tol,
                 output_edited_file,output_fit_file)
  
  for dir in ['east','north','vertical']:
    de,sde,fit = autoclean(data['time'][:,None], 
                           xy, 
                           data[dir], 
                           data[dir+'_std_dev'],
                           network_model=network_model,
                           network_params=network_params[dir],
                           station_model=station_model,
                           station_params=station_params[dir])
    out_edited[dir] = de
    out_edited[dir+'_std_dev'] = sde
    out_fit[dir] = fit
    # set unmasked uncertainties to zero 
    out_fit[dir+'_std_dev'][~np.isinf(data[dir+'_std_dev'])] = 0.0

  hdf5_from_dict(output_edited_file,out_edited)
  hdf5_from_dict(output_fit_file,out_fit)
  logger.info('Edited data written to %s' % output_edited_file)
  logger.info('Data fit written to %s' % output_fit_file)
  return


def pygeons_reml(input_file,
                 network_model=('se-se',),
                 network_params=(1.0,0.05,50.0),
                 network_fix=(),
                 station_model=('p0',),
                 station_params=(),
                 station_fix=(),
                 output_stem=None):
  ''' 
  Restricted maximum likelihood estimation
  '''
  logger.info('Running pygeons reml ...')
  data = dict_from_hdf5(input_file)
  if data['time_exponent'] != 0:
    raise ValueError('input dataset must have units of displacement')

  if data['space_exponent'] != 1:
    raise ValueError('input dataset must have units of displacement')

  # convert params to a dictionary of hyperparameters for each direction
  network_params = _params_dict(network_params)
  network_fix = np.asarray(network_fix,dtype=int)
  station_params = _params_dict(station_params)
  station_fix = np.asarray(station_fix,dtype=int)

  # make output file name
  if output_stem is None:
    output_stem = _remove_extension(input_file) + '.reml'

  output_file = output_stem + '.txt'
  
  # convert geodetic positions to cartesian
  bm = make_basemap(data['longitude'],data['latitude'])
  x,y = bm(data['longitude'],data['latitude'])
  xy = np.array([x,y]).T

  # call "pygeons info" on the input data file. pipe the results to
  # the output file
  sp.call('pygeons info %s > %s' % (input_file,output_file),shell=True)
  
  msg = _log_reml(input_file,
                  network_model,network_params,network_fix, 
                  station_model,station_params,station_fix,
                  output_file)
  # write log entry to file
  with open(output_file,'a') as fout:
    fout.write(msg)

  # make a dictionary storing likelihoods
  likelihood = {}
  for dir in ['east','north','vertical']:
    net_opt,sta_opt,like = reml(data['time'][:,None], 
                                xy, 
                                data[dir], 
                                data[dir+'_std_dev'],
                                network_model=network_model,
                                network_params=network_params[dir],
                                network_fix=network_fix,
                                station_model=station_model,
                                station_params=station_params[dir],
                                station_fix=station_fix)

    # update the parameter dict with the optimal values
    network_params[dir] = net_opt
    station_params[dir] = sta_opt
    likelihood[dir] = like

  msg = _log_reml_results(input_file,
                          network_model,network_params,network_fix, 
                          station_model,station_params,station_fix,
                          likelihood,output_file)
  # write log entry to file                 
  with open(output_file,'a') as fout:
    fout.write(msg)
    
  logger.info('Optimal parameters written to %s' % output_file)
  return


def pygeons_strain(input_file,
                   network_prior_model=('se-se',),
                   network_prior_params=(1.0,0.05,50.0),
                   network_noise_model=(),
                   network_noise_params=(),
                   station_noise_model=('p0',),
                   station_noise_params=(),
                   start_date=None,stop_date=None,positions=None,
                   output_stem=None):
  ''' 
  calculates strain
  '''
  logger.info('Running pygeons strain ...')
  data = dict_from_hdf5(input_file)
  if data['time_exponent'] != 0:
    raise ValueError('input dataset must have units of displacement')

  if data['space_exponent'] != 1:
    raise ValueError('input dataset must have units of displacement')
    
  out_dx = dict((k,np.copy(v)) for k,v in data.iteritems())
  out_dy = dict((k,np.copy(v)) for k,v in data.iteritems())

  # convert params to a dictionary of hyperparameters for each direction
  network_prior_params = _params_dict(network_prior_params)
  network_noise_params = _params_dict(network_noise_params)
  station_noise_params = _params_dict(station_noise_params)

  # convert geodetic input positions to cartesian
  bm = make_basemap(data['longitude'],data['latitude'])
  x,y = bm(data['longitude'],data['latitude'])
  xy = np.array([x,y]).T

  # set output positions
  if positions is None:
    output_id = np.array(data['id'],copy=True)
    output_lon = np.array(data['longitude'],copy=True)
    output_lat = np.array(data['latitude'],copy=True)
  else:  
    pos = np.loadtxt(positions,dtype=str)
    # pos = id,longitude,latitude
    output_id = pos[:,0]
    output_lon = pos[:,1].astype(float)
    output_lat = pos[:,2].astype(float)

  # convert geodetic output positions to cartesian
  output_x,output_y = bm(output_lon,output_lat)
  output_xy = np.array([output_x,output_y]).T 
  
  # set output times
  if start_date is None:
    start_date = mjd_inv(np.min(data['time']),'%Y-%m-%d')

  if stop_date is None:
    stop_date = mjd_inv(np.max(data['time']),'%Y-%m-%d')
  
  start_time = mjd(start_date,'%Y-%m-%d')  
  stop_time = mjd(stop_date,'%Y-%m-%d')  
  output_time = np.arange(start_time,stop_time+1)
  
  # set output file names
  if output_stem is None:
    output_stem = _remove_extension(input_file) + '.strain'

  output_dx_file = output_stem + '.xdiff.h5'
  output_dy_file = output_stem + '.ydiff.h5'

  _log_strain(input_file,
              network_prior_model,network_prior_params, 
              network_noise_model,network_noise_params, 
              station_noise_model,station_noise_params, 
              start_date,stop_date,positions,
              output_dx_file,output_dy_file)

  for dir in ['east','north','vertical']:
    dx,sdx,dy,sdy  = strain(data['time'][:,None],
                            xy,
                            data[dir],
                            data[dir+'_std_dev'],
                            network_prior_model=network_prior_model,
                            network_prior_params=network_prior_params[dir],
                            network_noise_model=network_noise_model,
                            network_noise_params=network_noise_params[dir],
                            station_noise_model=station_noise_model,
                            station_noise_params=station_noise_params[dir],
                            out_t=output_time[:,None],
                            out_x=output_xy)
    out_dx[dir] = dx
    out_dx[dir+'_std_dev'] = sdx
    out_dy[dir] = dy
    out_dy[dir+'_std_dev'] = sdy

  # set the new lon lat and id if positions was given
  out_dx['time'] = output_time
  out_dx['longitude'] = output_lon
  out_dx['latitude'] = output_lat
  out_dx['id'] = output_id
  out_dx['time_exponent'] = -1
  out_dx['space_exponent'] = 0
  
  out_dy['time'] = output_time
  out_dy['longitude'] = output_lon
  out_dy['latitude'] = output_lat
  out_dy['id'] = output_id
  out_dy['time_exponent'] = -1
  out_dy['space_exponent'] = 0

  output_dx_file = output_stem + '.xdiff.h5'
  output_dy_file = output_stem + '.ydiff.h5'
  hdf5_from_dict(output_dx_file,out_dx)
  hdf5_from_dict(output_dy_file,out_dy)
  logger.info('East derivative written to %s' % output_dx_file)
  logger.info('North derivative written to %s' % output_dy_file)
  return
