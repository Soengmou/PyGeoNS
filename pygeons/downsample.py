#!/usr/bin/env python 
from __future__ import division
import numpy as np
from scipy.spatial import cKDTree
import rbf.geometry
import warnings
import pygeons.cuts

def weighted_mean(x,sigma,axis=None):
  ''' 
  computes the weighted mean of *x* with uncertainties *sigma*
  
  Parameters
  ----------
    x : (N,...) array
    
    sigma : (N,...) array
      
    axis : int, optional
    
  Notes
  -----
    If all uncertainties along the axis are np.inf then then the 
    returned mean is 0.0 with uncertainty is np.inf
    
    If there are 0 entries along the axis then the returned mean is 
    0.0 with uncertainty np.inf
    
    All input uncertainties less than 1e-10 are first set to 1e-10, to 
    prevent division by zero complications. All calculated 
    uncertainties less than 1e-10 are set to zero before being 
    returned
    
  '''
  # values less than this are considered zero
  min_sigma = 1e-20

  x = np.asarray(x)
  sigma = np.asarray(sigma)
  # replace any zeros or near zeros with min_sigma
  sigma[sigma < min_sigma] = min_sigma

  numer = np.sum(x/sigma**2,axis=axis)
  denom = np.sum(1.0/sigma**2,axis=axis)
  with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    # out_value can be nan if the arrays have zero length along axis 
    # or if sigma is inf. out_sigma will be inf in that case 
    out_value = numer/denom
    out_sigma = np.sqrt(1.0/denom)
  
  if out_sigma.ndim == 0:
    if np.isnan(out_value):
      out_value = 0.0
    if out_sigma <= min_sigma:
      out_sigma = 0.0
  else:
    out_value[np.isnan(out_value)] = 0.0
    out_sigma[out_sigma <= min_sigma] = 0.0

  return out_value,out_sigma

class MeanInterpolant:
  '''   
  An interplant whose value at x is the mean of all values observed 
  within some radius of x
  
  If no values are within the radius of a queried position then the
  returned value is 0.0 with np.inf for its uncertainty
  
  If all values within a radius have np.inf for their uncertainty
  then the returned value is 0.0 with np.inf for its uncertainty

  '''
  def __init__(self,x,value,sigma=None,vert=None,smp=None):
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

    if vert is None:
      vert = np.zeros((0,x.shape[1]),dtype=float)
    else:
      vert = np.asarray(vert)

    if smp is None:
      smp = np.zeros((0,x.shape[1]),dtype=int)
    else:
      smp = np.asarray(smp)

    # form observation KDTree 
    self.Tobs = cKDTree(x)
    self.x = x
    self.value = value
    self.sigma = sigma
    self.value_shape = value.shape[1:]
    self.vert = vert
    self.smp = smp

  def __call__(self,xitp,radius=None):
    ''' 
    Parameters
    ----------
      x : (K,D) array

      radius : scalar, optional
        values within this distance from the interpolation points are 
        used to compute the mean. If not given then half the average 
        distance between interpolation points is used. If xitp has 
        only one point then radius is inf

      vert : (P,D) array, optional

      smp : (P,D) int array, optional
    Returns
    -------  
      out_value : (K,...) array

      out_sigma : (K,...) array
    '''
    xitp = np.asarray(xitp)
    Nitp = xitp.shape[0]
    Titp = cKDTree(xitp)
    if radius is None:
      # half of the average nearest neighbor distance
      radius = np.mean(Titp.query(xitp,2)[0][:,1])/2.0

    idx_arr = Titp.query_ball_tree(self.Tobs,radius)
    # make sure that the line segments connecting the observation 
    # points to the interpolation point do not intersect a boundary
    for i in range(Nitp):
      idx = idx_arr[i]
      xitp_ext = np.repeat(xitp[[i]],len(idx),axis=0)
      count = rbf.geometry.intersection_count(self.x[idx],xitp_ext,
                                              self.vert,self.smp)
      # throw out observation points that cross a boundary
      idx_arr[i] = [j for j,c in zip(idx,count) if c == 0]

    out_value = np.zeros((xitp.shape[0],)+self.value_shape)
    out_sigma = np.zeros((xitp.shape[0],)+self.value_shape)
    for i,idx in enumerate(idx_arr):
      out_value[i],out_sigma[i] = weighted_mean(self.value[idx],
                                                self.sigma[idx],
                                                axis=0)
    
    return out_value,out_sigma


def network_downsampler(u,t,t_itp,x,sigma=None,time_cuts=None):
  ''' 
  Parameters
  ---------- 
    u : (Nt,Nx) array
    
    t : (Nt,) array
    
    t_itp : (Nitp,) array

    x : (Nx,2) array

    sigma : (Nin,Nx) array, optional
    
    time_cuts : TimeCuts, optional

  Returns
  -------
    u_out : (Nout,Nx) array

    sigma_out :(Nout,Nx) array
  
  '''
  u = np.asarray(u)
  t = np.asarray(t)
  t_itp = np.asarray(t_itp)
  x = np.asarray(x)
  if time_cuts is None:
    time_cuts = pygeons.cuts.TimeCuts()

  u_out = np.zeros((t_itp.shape[0],x.shape[0]))
  sigma_out = np.zeros((t_itp.shape[0],x.shape[0]))
  for i,xi in enumerate(x):
    vert,smp = time_cuts.get_vert_and_smp(xi)
    I = MeanInterpolant(t[:,None],u[:,i],sigma=sigma[:,i],vert=vert,smp=smp)
    u_out[:,i],sigma_out[:,i] = I(t_itp[:,None])

  return u_out,sigma_out











