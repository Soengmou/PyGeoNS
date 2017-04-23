''' 
Defines the main filtering functions which are called by the 
PyGeoNS executable.
'''
from __future__ import division
import numpy as np
import logging
import os
from pygeons.main.reml import reml
from pygeons.main.strain import strain
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


def _change_extension(f,ext):
  return '.'.join(f.split('.')[:-1] + [ext])


def _log_reml(input_file,
              network_model,network_params,network_fix, 
              station_model,station_params,station_fix,
              parameter_file):
  msg  = '\n'                     
  msg += '---------------- PYGEONS REML RUN INFORMATION ----------------\n\n'
  msg += 'input file : %s\n' % input_file
  msg += 'network :\n' 
  msg += '    model : %s\n' % ' '.join(network_model)
  msg += '    fixed : %s\n' % ' '.join(network_fix.astype(str))
  msg += '    parameter units : %s\n' % ' '.join(get_units(network_model))
  msg += '    initial east parameters : %s\n' % ' '.join(network_params['east'].astype(str))
  msg += '    initial north parameters : %s\n' % ' '.join(network_params['north'].astype(str))
  msg += '    initial vertical parameters : %s\n' % ' '.join(network_params['vertical'].astype(str))
  msg += 'station :\n' 
  msg += '    model : %s\n' % ' '.join(station_model)
  msg += '    fixed : %s\n' % ' '.join(station_fix.astype(str))
  msg += '    parameter units : %s\n' % ' '.join(get_units(station_model))
  msg += '    initial east parameters : %s\n' % ' '.join(station_params['east'].astype(str))
  msg += '    initial north parameters : %s\n' % ' '.join(station_params['north'].astype(str))
  msg += '    initial vertical parameters : %s\n' % ' '.join(station_params['vertical'].astype(str))
  msg += 'output file : %s\n\n' % parameter_file  
  msg += '--------------------------------------------------------------\n'
  logger.info(msg)
  return msg


def _log_reml_results(input_file,
                      network_model,network_params,network_fix, 
                      station_model,station_params,station_fix,
                      likelihood,parameter_file):
  msg  = '\n'                     
  msg += '-------------------- PYGEONS REML RESULTS --------------------\n\n'
  msg += 'input file : %s\n' % input_file
  msg += 'network :\n' 
  msg += '    model : %s\n' % ' '.join(network_model)
  msg += '    fixed : %s\n' % ' '.join(network_fix.astype(str))
  msg += '    parameter units : %s\n' % ' '.join(get_units(network_model))
  msg += '    optimal east parameters : %s\n' % ' '.join(network_params['east'].astype(str))
  msg += '    optimal north parameters : %s\n' % ' '.join(network_params['north'].astype(str))
  msg += '    optimal vertical parameters : %s\n' % ' '.join(network_params['vertical'].astype(str))
  msg += 'station :\n' 
  msg += '    model : %s\n' % ' '.join(station_model)
  msg += '    fixed : %s\n' % ' '.join(station_fix.astype(str))
  msg += '    parameter units : %s\n' % ' '.join(get_units(station_model))
  msg += '    optimal east parameters : %s\n' % ' '.join(station_params['east'].astype(str))
  msg += '    optimal north parameters : %s\n' % ' '.join(station_params['north'].astype(str))
  msg += '    optimal vertical parameters : %s\n' % ' '.join(station_params['vertical'].astype(str))
  msg += 'log likelihood : %s\n' % likelihood
  msg += 'output file : %s\n\n' % parameter_file  
  msg += '--------------------------------------------------------------\n'
  logger.info(msg)
  return msg
  
  
def pygeons_reml(input_file,
                 network_model=('se-se',),
                 network_params=(1.0,0.05,50.0),
                 network_fix=(),
                 station_model=('p0',),
                 station_params=(),
                 station_fix=(),
                 parameter_file=None):
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

  # make output file
  if parameter_file is None:
    parameter_file = 'parameters.txt'
    # make sure an existing file is not overwritten
    count = 0
    while os.path.exists(parameter_file):
      count += 1
      parameter_file = 'parameters.%s.txt' % count

  bm = make_basemap(data['longitude'],data['latitude'])
  x,y = bm(data['longitude'],data['latitude'])
  xy = np.array([x,y]).T

  _log_reml(input_file,
            network_model,network_params,network_fix, 
            station_model,station_params,station_fix,
            parameter_file)

  for dir in ['east','north','vertical']:
    # optimal hyperparameters for each timeseries, coresponding
    # likelihoods and data counts.
    opt,like = reml(data['time'][:,None], 
                    xy, 
                    data[dir], 
                    data[dir+'_std_dev'],
                    network_model=network_model,
                    network_params=network_params[dir],
                    network_fix=network_fix,
                    station_model=station_model,
                    station_params=station_params[dir],
                    station_fix=station_fix)
                             
    if dir == 'east':                                
      with open(parameter_file,'w') as fout:
        header = '%-15s%-15s' % ('component','count') 
        header += "".join(['%-15s' % ('p%s[%s]' % (j,i)) for j,i in enumerate(param_units)])
        header += '%-15s\n' % 'likelihood'
        fout.write(header)
        fout.flush()
        
    # convert units optimal hyperparameters back to mm and yr   
    with open(parameter_file,'a') as fout:
      entry  = '%-15s%-15s' % (dir,count)
      entry += "".join(['%-15.4e' % j for j in opt])
      entry += '%-15.4e\n' % like
      fout.write(entry)
      fout.flush()


def _log_strain(input_file,
                network_prior_model,network_prior_params, 
                network_noise_model,network_noise_params, 
                station_noise_model,station_noise_params, 
                start_date,stop_date,positions,
                outlier_tol,output_dir):
  msg  = '\n'
  msg += '--------------- PYGEONS STRAIN RUN INFORMATION ---------------\n\n'
  msg += 'input file : %s\n' % input_file
  msg += 'network prior :\n' 
  msg += '    model : %s\n' % ' '.join(network_prior_model)
  msg += '    parameter units : %s\n' % ' '.join(get_units(network_prior_model))
  msg += '    east parameters : %s\n' % ' '.join(network_prior_params['east'].astype(str))
  msg += '    north parameters : %s\n' % ' '.join(network_prior_params['north'].astype(str))
  msg += '    vertical parameters : %s\n' % ' '.join(network_prior_params['vertical'].astype(str))
  msg += 'network noise :\n' 
  msg += '    model : %s\n' % ' '.join(network_noise_model)
  msg += '    parameter units : %s\n' % ' '.join(get_units(network_noise_model))
  msg += '    east parameters : %s\n' % ' '.join(network_noise_params['east'].astype(str))
  msg += '    north parameters : %s\n' % ' '.join(network_noise_params['north'].astype(str))
  msg += '    vertical parameters : %s\n' % ' '.join(network_noise_params['vertical'].astype(str))
  msg += 'station noise :\n' 
  msg += '    model : %s\n' % ' '.join(station_noise_model)
  msg += '    parameter units : %s\n' % ' '.join(get_units(station_noise_model))
  msg += '    east parameters : %s\n' % ' '.join(station_noise_params['east'].astype(str))
  msg += '    north parameters : %s\n' % ' '.join(station_noise_params['north'].astype(str))
  msg += '    vertical parameters : %s\n' % ' '.join(station_noise_params['vertical'].astype(str))
  msg += 'outlier tolerance : %s\n' % outlier_tol  
  msg += 'output start date : %s\n' % start_date
  msg += 'output stop date : %s\n' % stop_date
  if positions is None:
    msg += 'output positions file : < using same positions as input >\n'
  else:   
    msg += 'output positions file : %s\n' % positions

  msg += 'output directory : %s\n\n' % output_dir  
  msg += '--------------------------------------------------------------\n'
  logger.info(msg)


def pygeons_strain(input_file,
                   network_prior_model=('se-se',),
                   network_prior_params=(1.0,0.05,50.0),
                   network_noise_model=(),
                   network_noise_params=(),
                   station_noise_model=('p0',),
                   station_noise_params=(),
                   start_date=None,stop_date=None,positions=None,
                   outlier_tol=4.0,
                   output_dir=None):
  ''' 
  calculates strain
  '''
  logger.info('Running pygeons strain ...')
  data = dict_from_hdf5(input_file)
  if data['time_exponent'] != 0:
    raise ValueError('input dataset must have units of displacement')

  if data['space_exponent'] != 1:
    raise ValueError('input dataset must have units of displacement')
    
  out_edit = dict((k,np.copy(v)) for k,v in data.iteritems())
  out_fit = dict((k,np.copy(v)) for k,v in data.iteritems())
  out_dx = dict((k,np.copy(v)) for k,v in data.iteritems())
  out_dy = dict((k,np.copy(v)) for k,v in data.iteritems())

  # convert params to a dictionary of hyperparameters for each direction
  network_prior_params = _params_dict(network_prior_params)
  network_noise_params = _params_dict(network_noise_params)
  station_noise_params = _params_dict(station_noise_params)

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
  
  if output_dir is None:
    output_dir = _change_extension(input_file,'strain')

  _log_strain(input_file,
              network_prior_model,network_prior_params, 
              network_noise_model,network_noise_params, 
              station_noise_model,station_noise_params, 
              start_date,stop_date,positions,
              outlier_tol,output_dir)

  # convert the domain units from m to km
  for dir in ['east','north','vertical']:
    de,sde,fit,dx,sdx,dy,sdy  = strain(data['time'][:,None],
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
                                       out_x=output_xy,
                                       tol=outlier_tol)
    out_edit[dir] = de
    out_edit[dir+'_std_dev'] = sde
    out_fit[dir] = fit
    # replace uncertainties for non-missing data with 0.0
    out_fit[dir+'_std_dev'][~np.isinf(data[dir+'_std_dev'])] = 0.0
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

  if not os.path.exists(output_dir):
    os.makedirs(output_dir)
  
  output_edit_file = output_dir + '/edited.h5'
  output_fit_file = output_dir + '/fit.h5'
  output_dx_file = output_dir + '/xdiff.h5'
  output_dy_file = output_dir + '/ydiff.h5'
  hdf5_from_dict(output_edit_file,out_edit)
  hdf5_from_dict(output_fit_file,out_fit)
  hdf5_from_dict(output_dx_file,out_dx)
  hdf5_from_dict(output_dy_file,out_dy)
