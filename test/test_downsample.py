#!/usr/bin/env python
import numpy as np
import matplotlib.pyplot as plt
from pygeons.smooth import network_smoother
from pygeons.diff import ACCELERATION
from scipy.spatial import cKDTree
import pygeons.diff
import warnings

class MeanInterpolant:
  '''   
  An interplant whose value at x is the mean of all values observed 
  within some radius of x
  
  If no values are within the radius of a queried position then the
  returned value is 0.0 with np.inf for its uncertainty
  
  If all values within a radius have np.inf for their uncertainty
  then the returned value is 0.0 with np.inf for its uncertainty

  '''
  def __init__(self,x,value,sigma=None):
    ''' 
    Parameters
    ----------
      x : (N,D) array

      value : (N,...) array

      sigma : (N,...) array

    '''
    x = np.asarray(x,dtype=float)
    value = np.asarray(value,dtype=float)
    if sigma is None:
      sigma = np.ones(value.shape,dtype=float)
    else:
      sigma = np.asarray(sigma,dtype=float)
      
    # form observation KDTree 
    self.Tobs = cKDTree(x)
    self.value = value
    self.sigma = sigma
    self.value_shape = value.shape[1:]

  def __call__(self,xitp,radius):
    ''' 
    Parameters
    ----------
      x : (K,D) array

      radius : scalar

    Returns
    -------  
      out_value : (K,...) array

      out_sigma : (K,...) array
    '''
    xitp = np.asarray(xitp)
    Titp = cKDTree(xitp)
    idx_arr = Titp.query_ball_tree(self.Tobs,radius)
    out_value = np.zeros((xitp.shape[0],)+self.value_shape)
    out_sigma = np.zeros((xitp.shape[0],)+self.value_shape)
    with warnings.catch_warnings():
      warnings.simplefilter('ignore')
      for i,idx in enumerate(idx_arr):
        numer = np.sum(self.value[idx]/self.sigma[idx]**2,axis=0)
        denom = np.sum(1.0/self.sigma[idx]**2,axis=0)
        out_value[i] = numer/denom
        out_sigma[i] = np.sqrt(1.0/denom)

    # replace any nans with zero
    out_value[np.isnan(out_value)] = 0.0
    
    return out_value,out_sigma

def rms(x):
  ''' 
  root mean squares
  '''
  x = np.asarray(x)
  return np.sqrt(np.sum(x**2)/x.shape[0])


def compute_penalty(length_scale,time_scale,sigma,diff_specs):
  sigma = np.asarray(sigma)
  S = 1.0/rms(1.0/sigma)

  # make sure all space derivative terms have the same order
  xords =  [sum(i) for i in diff_specs['space']['diffs']]
  # make sure all time derivative terms have the same order
  tords =  [sum(i) for i in diff_specs['time']['diffs']]
  if not all([i==xords[0] for i in xords]):
    raise ValueError('all space derivative terms must have the same order')
  if not all([i==tords[0] for i in tords]):
    raise ValueError('all time derivative terms must have the same order')

  xord = xords[0]
  tord = tords[0]

  return (time_scale/2.0)**tord*(length_scale/2.0)**xord/S

  
acc = pygeons.diff.DiffSpecs()
acc['space']['diffs'] = [[0,0],[0,0]]
acc['time']['diffs'] = [[2]]

N1 = 10000
N2 = 200
T = 0.1

x = np.array([[0.0,0.0]])
t1 = np.linspace(0.0,1.0,N1)
t2 = np.linspace(0.0,1.0,N2)
dt1 = t1[1] - t1[0]
dt2 = t2[1] - t2[0]
print('dt1 : %s' % dt1)
print('dt2 : %s' % dt2)

sigma_scale = 2.0
sigma1 = sigma_scale*np.ones((N1,1))
u1 = np.random.normal(0.0,sigma1)

I = MeanInterpolant(t1[:,None],u1,sigma=sigma1)
u2,sigma2 = I(t2[:,None],dt2/2.0)

P = [compute_penalty(1.0,T,sigma1,acc)]
smooth1,dummy = network_smoother(u1,t1,x,sigma=sigma1,
                                 diff_specs=[acc],
                                 penalties=P)

P = [compute_penalty(1.0,T,sigma2,acc)]
smooth2,dummy = network_smoother(u2,t2,x,sigma=sigma2,
                                 diff_specs=[acc],
                                 penalties=P)

fig,ax = plt.subplots()
ax.plot(t1,smooth1,'k-')
ax.plot(t2,smooth2,'b-')
plt.show()
