''' 

This module contains functions that check the consistency of data 
dictionaries. A valid dictionary will contain the following entries

  time : (Nt,) array
    Array of observation times. These are integer values of modified 
    Julian dates. Days are used instead of years because there is no 
    ambiguity about the length of a day
        
  id : (Nx,) array
    Array of 4-character IDs for each station

  longitude : (Nx,) array
    Longitude for each station in degrees
        
  latitude : (Nx,) array
    Latitude for each station in degrees

  east,north,vertical : (Nt,Nx) array
    data components. The units should be in terms of meters and days 
    and should be consistent with the values specified for 
    *space_exponent* and *time_exponent*. For example, if 
    *time_exponent* is -1 and *space_exponent* is 1 then the units 
    should be in meters per day.

  east_std,north_std,vertical_std : (Nt,Nx) array
    One standard deviation uncertainty. These should have the same 
    units as the data components

  time_exponent : int
    Indicates the power of the time units for the data. -1 
    indicates that the data is a rate, -2 is an acceleration etc.

  space_exponent : int
    Indicates the power of the spatial units for the data

'''
import copy
import numpy as np
import logging
logger = logging.getLogger(__name__)

class DataError(Exception):
  ''' 
  An error indicating that the is data dictionary inconsistent.
  '''
  pass


def check_entries(data):
  ''' 
  Checks if all the entries exist in the data dictionary
  '''
  keys = ['time','id','longitude','latitude','east','north',
          'vertical','east_std','north_std','vertical_std',
          'time_exponent','space_exponent']
  for k in keys:
    if not data.has_key(k):
      raise DataError('Data dictionary is missing *%s*' % k)
  

def check_shapes(data):
  ''' 
  Checks if the shapes of each entry are consistent.
  '''
  # check for proper sizes
  Nt = data['time'].shape[0]
  Nx = data['id'].shape[0]
  keys = ['longitude','latitude']
  for k in keys:     
    if not data[k].shape == (Nx,):
      raise DataError('*%s* has shape %s but it should have shape %s' 
                      % (k,data[k].shape,(Nx,)))
  
  keys = ['east','north','vertical','east_std','north_std','vertical_std']
  for k in keys:     
    if not data[k].shape == (Nt,Nx):
      raise DataError('*%s* has shape %s but it should have shape %s' 
                      % (k,data[k].shape,(Nt,Nx)))


def check_positive_uncertainties(data):
  ''' 
  Checks if all the uncertainties are positive.
  '''
  keys = ['east_std','north_std','vertical_std']
  for k in keys:
    if np.any(data[k] <= 0.0):
      raise DataError('*%s* contains zeros or negative values' % k)
     

def check_missing_data(data):
  ''' 
  Checks if all nan observations correspond to inf uncertainties and 
  vice versa. If this is not the case then plotting functions may not 
  work properly.
  '''
  dirs = ['east','north','vertical']
  for d in dirs:
    mu = data[d] 
    sigma = data[d + '_std'] 
    is_nan = np.isnan(mu)
    is_inf = np.isinf(sigma)
    if not np.all(is_nan == is_inf):
      raise DataError('nan values in *%s* do not correspond to inf '
                      'values in *%s*' % (d,d+'_std'))
    
    # make sure that there are no nans in the uncertainties or infs in 
    # the means
    is_inf = np.isinf(mu)
    is_nan = np.isnan(sigma)
    if np.any(is_inf):
      raise DataError('inf values found in *%s*' % d)

    if np.any(is_nan):
      raise DataError('nan values found in *%s*_std' % d)
      

def check_data(data):
  ''' 
  Runs all data consistency check
  '''
  logger.debug('checking data consistency ... ')
  check_entries(data)
  check_shapes(data)
  check_positive_uncertainties(data)
  check_missing_data(data)
  logger.debug('ok')
  
  
def check_compatibility(data1,data2):
  ''' 
  Makes sure that two data sets have the same sizes, times, stations, 
  and units
  '''
  logger.debug('checking data compatibility ... ')
  if data1['time'].shape[0] != data2['time'].shape[0]:
    raise DataError('Data sets have inconsistent number of time epochs')

  if data1['id'].shape[0] != data2['id'].shape[0]:
    raise DataError('Data sets have inconsistent number of stations')

  if not np.all(data1['time'] == data2['time']):
    raise DataError('Data sets have inconsistent time epochs')
    
  if not np.all(data1['id'] == data2['id']):
    raise DataError('Data sets have inconsistent stations')

  if data1['time_exponent'] != data2['time_exponent']:
    raise DataError('Data sets have inconsistent units')

  if data1['space_exponent'] != data2['space_exponent']:
    raise DataError('Data sets have inconsistent units')

  logger.debug('ok')
