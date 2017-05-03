''' 
Module for converting between Modified Julian Date (MJD) and date 
strings. In this modules, MJD is the INTEGER number of full days 
ellapsed since midnight on November 17, 1858. So MJD is 0 throughout 
all of November 18, 1858, 1 throughout all of November 19, 1858, etc.
'''
from __future__ import division
import time as timemod
from functools import wraps
from datetime import datetime,timedelta
import numpy as np

_REFERENCE_DATETIME = datetime(1858,11,17,0,0)

def _memoize(fin):
  cache = {}
  @wraps(fin)
  def fout(*args):
    if args not in cache:
      cache[args] = fin(*args)

    return cache[args]

  return fout
  

@_memoize
def mjd(s,fmt):
  ''' 
  Converts a date string into Modified Julian Date (MJD)
  
  Parameters
  ----------
  s : string
    Date string

  fmt : string
    Format string indicating how to parse *s*
      
  Returns
  -------
  out : int
    Modified Julian Date

  '''
  d = datetime.strptime(s,fmt)
  out = (d - _REFERENCE_DATETIME).days
  return out


@_memoize
def mjd_inv(m,fmt):
  ''' 
  Converts Modified Julian Date (MJD) to a date string 
  
  Parameters
  ----------
  m : int
    Modified Julian Date

  fmt : string
    format string indicating how to form *out*
      
  Returns
  -------
  out : str
    Date string
    
  '''
  m = int(m)
  d = _REFERENCE_DATETIME + timedelta(m)
  out = d.strftime(fmt)
  return out
