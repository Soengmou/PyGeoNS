#!/usr/bin/env python
import copy
import numpy as np
import logging
logger = logging.getLogger(__name__)

class DataDict(dict):
  ''' 
  Specialized dictionary for GPS data.  An instance of this class 
  contains the following items
  
      time : (Nt,) array
      id : (Nx,) array
      longitude : (Nx,) array
      latitude : (Nx,) array
      east : (Nt,Nx) array
      north : (Nt,Nx) array
      vertical : (Nt,Nx) array
      east_std : (Nt,Nx) array
      north_std : (Nt,Nx) array
      vertical_std : (Nt,Nx) array
  
  '''
  def __init__(self,input=None):
    ''' 
    Initiates a DataDict instance. This can be initiated with the same 
    entries as *input* which is another dictionary or DataDict 
    instance. If *input* is provided then array copies are made so 
    that the new DataDict does not share any data with *input*.
    '''
    dict.__init__(self)
    self['time'] = None
    self['id'] = None
    self['longitude'] = None
    self['latitude'] = None
    self['east'] = None
    self['north'] = None
    self['vertical'] = None
    self['east_std'] = None
    self['north_std'] = None
    self['vertical_std'] = None
    
    if input is not None:
      self.update_with_copy(input)
      
    return

  def __str__(self):
    out = ['DataDict instance']
    for k in self.keys():
      out += ['    %s : %s array' % (k,np.shape(self[k]))]

    return '\n'.join(out)

  def __repr__(self):
    return self.__str__()
        
  def update_with_copy(self,other):
    '''makes a deep copy before update'''
    other = copy.deepcopy(other)
    self.update(other)
    
  def check_self_consistency(self):
    ''' 
    raises an error if any of the following conditions are not met

      - no items are None
      - all items have consistent sizes
      - all inf uncertainties are inf for each direction (e.g. if the 
        easting component is unknown then the northing component should 
        also be unknown)
      - all nan data have corresponding uncertainties of inf
      - all uncertainties are positive and nonzero
      - there are no duplicate station IDs

    '''
    logger.debug('checking self consistency ...')
    # check for Nones
    keys = ['time','id','longitude','latitude',
            'east','north','vertical',
            'east_std','north_std','vertical_std']
    for k in keys:
      if self[k] is None:
        raise ValueError('*%s* has not been set' % k)
    
      self[k] = np.asarray(self[k])
      
    # check for proper sizes
    Nt = len(self['time'])
    Nx = len(self['id'])
    keys = ['longitude','latitude']
    for k in keys:     
      if not self[k].shape == (Nx,):
        raise ValueError('*%s* has shape %s but should be %s' % (k,self[k].shape,(Nx,)))

    keys = ['east','north','vertical',
            'east_std','north_std','vertical_std']
    for k in keys:     
      if not self[k].shape == (Nt,Nx):
        raise ValueError('dimensions of *%s* have shape %s but should be %s' % (k,self[k].shape,(Nt,Nx)))
    
    # make sure infinite uncertainties are consistent for all three directions
    east_isinf = np.isinf(self['east_std'])
    north_isinf = np.isinf(self['north_std'])
    vertical_isinf = np.isinf(self['vertical_std'])
    if not np.all(east_isinf==north_isinf):
      raise ValueError('missing data (i.e. data with infinite uncertainty) must be missing for all three directions')
    if not np.all(east_isinf==vertical_isinf):
      raise ValueError('missing data (i.e. data with infinite uncertainty) must be missing for all three directions')
      
    # make sure that infs correspond with nans
    keys = ['east','north','vertical']
    for k in keys:
      k_isnan = np.isnan(self[k])
      if not np.all(k_isnan == east_isinf):
        raise ValueError('infs in the uncertainties do not correspond to nans in the data')
        
    # make sure that all uncertainties are positive
    keys = ['east_std','north_std','vertical_std']
    for k in keys:
      if np.any(self[k] <= 0.0):
        raise ValueError('found zero or negative uncertainty for *%s*' % k)
     
    # make sure there are no duplicate station IDs
    if len(np.unique(self['id'])) != len(self['id']):
      # there are duplicate stations, now find which ones
      duplicates = []
      for i in np.unique(self['id']):
        if np.sum(i == self['id']) > 1:
          duplicates += [i]

      duplicates = ' '.join(duplicates)
      raise ValueError('There were multiple occurrences of these station IDs: %s' % duplicates)

    logger.debug('ok')
    return

  def check_compatibility(self,other):
    '''make sure that the DataDicts have the same stations and times'''
    # compare agains the first data set
    if len(self['time']) != len(other['time']):
      raise ValueError('DataDicts have inconsistent number of time epochs')
    if len(self['id']) != len(other['id']):
      raise ValueError('DataDicts have inconsistent number of stations')
    if not np.all(self['time'] == other['time']):
      raise ValueError('DataDicts have inconsistent time epochs')
    if not np.all(self['id'] == other['id']):
      raise ValueError('DataDicts have inconsistent stations')

    return

