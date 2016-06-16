#!/usr/bin/env python
import numpy as np
import modest.cv
import modest
import modest.solvers
import scipy.sparse
from scipy.spatial import cKDTree
import logging
import pygeons.cuts
import modest.mp
import pygeons.diff
logger = logging.getLogger(__name__)


def _average_shortest_distance(x):
  ''' 
  returns the average distance to nearest neighbor           

  Parameters
  ----------
    x : (N,D) array

  Returns
  -------
    out : float
  '''
  T = cKDTree(x)
  out = np.mean(T.query(x,2)[0][:,1])
  return out


def _estimate_scales(t,x):
  ''' 
  returns a time and spatial scale which is 10x the average shortest 
  distance between times
  '''
  dt = _average_shortest_distance(t[:,None])
  dl = _average_shortest_distance(x)
  T = 10*dt
  L = 10*dl
  return T,L


def _rms(x):
  ''' 
  root mean squares
  '''
  x = np.asarray(x)
  return np.sqrt(np.sum(x**2)/x.size)


def _penalty(T,L,sigma,diff_specs):
  ''' 
  returns scaling parameter for the regularization constraint
  '''
  sigma = np.asarray(sigma)
  S = 1.0/_rms(1.0/sigma) # characteristic uncertainty 

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
  out = (T/2.0)**tord*(L/2.0)**xord/S
  return out  
  

def network_smoother(u,t,x,
                     sigma=None,
                     diff_specs=None,
                     length_scale=None,                      
                     time_scale=None,
                     use_umfpack=True,
                     procs=None,
                     perts=10):
  u = np.asarray(u)
  t = np.asarray(t)
  x = np.asarray(x)

  Nx = x.shape[0]
  Nt = t.shape[0]

  if diff_specs is None:
    diff_specs = [pygeons.diff.acc(),
                  pygeons.diff.disp_laplacian()]

  if u.shape != (Nt,Nx):
    raise TypeError('u must have shape (Nt,Nx)')

  if sigma is None:
    sigma = np.ones((Nt,Nx))
  
  else:
    sigma = np.array(sigma,copy=True)
    # replace any infinite uncertainties with 1e10. This does not 
    # seem to introduce any numerical instability and seems to be 
    # sufficient in all cases. Infs need to be replaced in order to 
    # keep the LHS matrix positive definite
    sigma[sigma==np.inf] = 1e10
    
  if sigma.shape != (Nt,Nx):
    raise TypeError('sigma must have shape (Nt,Nx)')

  u_flat = u.ravel()
  sigma_flat = sigma.ravel()

  logger.info('building regularization matrix...')
  reg_matrices = [pygeons.diff.diff_matrix(t,x,d,procs=procs) for d in diff_specs]
  logger.info('done')

  # estimate length scale and time scale if not given
  default_time_scale,default_length_scale = _estimate_scales(t,x)
  if length_scale is None:
    length_scale = default_length_scale

  if time_scale is None:
    time_scale = default_time_scale
    
  # create regularization penalty parameters
  penalties = [_penalty(time_scale,length_scale,sigma,d) for d in diff_specs]
  
  # system matrix is the identity matrix scaled by data weight
  Gdata = 1.0/sigma_flat
  Grow = range(Nt*Nx)
  Gcol = range(Nt*Nx)
  Gsize = (Nt*Nx,Nt*Nx)
  G = scipy.sparse.csr_matrix((Gdata,(Grow,Gcol)),Gsize)
  
  # weigh u by the inverse of data uncertainty.
  u_flat = u_flat/sigma_flat

  # this makes matrix copies
  L = scipy.sparse.vstack(p*r for p,r in zip(penalties,reg_matrices))
  L.eliminate_zeros()
  
  logger.info('solving for predicted displacements...')
  u_pred = modest.sparse_reg_dsolve(G,L,u_flat,use_umfpack=use_umfpack)
  logger.info('done')

  logger.info('computing perturbed predicted displacements...')
  u_pert = np.zeros((perts,G.shape[0]))
  # perturbed displacements will be computed in parallel and so this 
  # needs to be turned into a mappable function
  def mappable_dsolve(args):
    G = args[0]
    L = args[1]
    d = args[2]
    use_umfpack=args[3]
    return modest.sparse_reg_dsolve(G,L,d,use_umfpack=use_umfpack)

  # generator for arguments that will be passed to calculate_pert
  args = ((G,L,np.random.normal(0.0,1.0,G.shape[0]),use_umfpack)
           for i in range(perts))
  u_pert = modest.mp.parmap(mappable_dsolve,args,workers=procs)
  u_pert = np.reshape(u_pert,(perts,(Nt*Nx)))
  u_pert += u_pred[None,:]

  logger.info('done')

  u_pred = u_pred.reshape((Nt,Nx))
  u_pert = u_pert.reshape((perts,Nt,Nx))

  return u_pred,u_pert


