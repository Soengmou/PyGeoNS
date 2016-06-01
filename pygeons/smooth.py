#!/usr/bin/env python
import numpy as np
import modest.cv
import rbf.fd
import modest
import modest.solvers
import scipy.sparse
import logging
from scipy.spatial import cKDTree
import pygeons.cuts
import modest.mp

logger = logging.getLogger(__name__)


def _identify_duplicate_stations(pos):
  ''' 
  identifies stations which are abnormally close to eachother
  '''
  T = cKDTree(pos)
  dist,idx = T.query(pos,2)
  r = dist[:,1]
  ri = idx[:,1]
  logr = np.log10(r)
  cutoff = np.mean(logr) - 4*np.std(logr)
  duplicates = np.nonzero(logr < cutoff)[0]
  for d in duplicates:
    logger.warning('station %s is abnormally close to station %s. '
                   'This may result in numerical instability. One '                 
                   'of the stations should be removed or they should '
                   'be merged together.' % (d,ri[d]))



class _RunningVariance(object):
  ''' 
  estimates uncertainty from bootstrapping without storing all 
  of the bootstrapped solutions

  Usage
  -----
    >> a = _RunningVariance()
    >> a.add(1.8)
    >> a.add(2.3)
    >> a.add(1.5)
    >> a.get_variance()
       0.163333333333334
  '''
  def __init__(self):
    self.sum = None
    self.sumsqs = None
    self.count = 0.0

  def add(self,entry):
    entry = np.asarray(entry,dtype=float)
    self.count += 1.0
    if self.sum is None:
      self.sum = np.copy(entry)
      self.sumsqs = np.copy(entry)**2
    else:
      self.sum += entry
      self.sumsqs += entry**2

  def get_variance(self):
    return (self.sumsqs - self.sum**2/self.count)/(self.count-1.0)


def _bootstrap_uncertainty(G,L,itr=10,**kwargs):
  ''' 
  estimates the uncertainty for the solution to the regularized linear 
  system.  Bootstrapping is necessary because computing the model 
  covariance matrix is too expensive.  It is assumed that G is already 
  weighted by the data uncertainty
  '''
  if itr <= 1:
    logger.info('cannot bootstrap uncertainties with %s iterations. returning zeros' % itr)
    return np.zeros(G.shape[1])

  soln = _RunningVariance()
  for i in range(itr):
    d = np.random.normal(0.0,1.0,G.shape[0])
    solni = modest.sparse_reg_petsc(G,L,d,**kwargs)
    soln.add(solni)
    logger.info('finished bootstrap iteration %s of %s' % (i+1,itr))

  return np.sqrt(soln.get_variance())


def _reg_matrices(t,x,
                  stencil_size=5,
                  reg_basis=rbf.basis.phs3,
                  reg_poly_order=1, 
                  time_cuts=None,
                  space_cuts=None,
                  Nprocs=None):
  # compile the necessary derivatives for our rbf. This is done so 
  # that each subprocesses does not need to
  reg_basis(np.zeros((0,1)),np.zeros((0,1)),diff=(0,))
  reg_basis(np.zeros((0,1)),np.zeros((0,1)),diff=(2,))
  reg_basis(np.zeros((0,2)),np.zeros((0,2)),diff=(0,0))
  reg_basis(np.zeros((0,2)),np.zeros((0,2)),diff=(2,0))
  reg_basis(np.zeros((0,2)),np.zeros((0,2)),diff=(0,2))

  time_stencil_size = 3
  time_reg_poly_order = 2

  if time_cuts is None:
    time_cuts = pygeons.cuts.CutCollection()
  if space_cuts is None:
    space_cuts = pygeons.cuts.CutCollection()

  # make a spatial regularization matrix for each time step
  # argument generator
  def space_args_maker():
    for ti in t:
      vert,smp = space_cuts.get_vert_smp(ti) 
      args = (x,stencil_size,
              np.array([1.0,1.0]),
              np.array([[2,0],[0,2]]), 
              reg_basis,reg_poly_order,
              vert,smp)
      yield args 

  def time_args_maker():
    for xi in x:
      vert,smp = time_cuts.get_vert_smp(xi) 
      args = (t[:,None],time_stencil_size,
              np.array([1.0]),
              np.array([[2]]), 
              reg_basis,time_reg_poly_order,
              vert,smp)
      yield args 

  def mappable_diff_matrix(args):
    return rbf.fd.diff_matrix(args[0],N=args[1],
                              coeffs=args[2],diffs=args[3],
                              basis=args[4],order=args[5],
                              vert=args[6],smp=args[7])

  Lx = modest.mp.parmap(mappable_diff_matrix,space_args_maker(),Nprocs=Nprocs)
  Lt = modest.mp.parmap(mappable_diff_matrix,time_args_maker(),Nprocs=Nprocs)

  Nx = len(x)
  Nt = len(t)

  # extract the rcv data for the t matrices 
  rows = np.zeros((time_stencil_size*Nt,Nx))
  cols = np.zeros((time_stencil_size*Nt,Nx))
  vals = np.zeros((time_stencil_size*Nt,Nx))
  for i,Li in enumerate(Lt):
    Li = Li.tocoo()
    ri,ci,vi = Li.row,Li.col,Li.data
    rows[:,i] = ri
    cols[:,i] = ci
    vals[:,i] = vi

  rows *= Nx
  rows += np.arange(Nx)
  rows = rows.ravel()

  cols *= Nx
  cols += np.arange(Nx)
  cols = cols.ravel()

  vals = vals.ravel()
  
  Lt_out = scipy.sparse.csr_matrix((vals,(rows,cols)),(Nx*Nt,Nx*Nt))

  # extract the rcv data for the x matrices
  rows = np.zeros((stencil_size*Nx,Nt))
  cols = np.zeros((stencil_size*Nx,Nt))
  vals = np.zeros((stencil_size*Nx,Nt))
  for i,Li in enumerate(Lx):
    Li = Li.tocoo()
    ri,ci,vi = Li.row,Li.col,Li.data
    rows[:,i] = ri
    cols[:,i] = ci
    vals[:,i] = vi

  rows += np.arange(Nt)*Nx
  rows = rows.ravel()

  cols += np.arange(Nt)*Nx
  cols = cols.ravel()

  vals = vals.ravel()
  
  Lx_out = scipy.sparse.csr_matrix((vals,(rows,cols)),(Nx*Nt,Nx*Nt))
  
  return Lt_out,Lx_out


def network_smoother(u,t,x,
                     sigma=None,
                     stencil_size=5,
                     stencil_connectivity=None,
                     stencil_space_vert=None,
                     stencil_space_smp=None,
                     stencil_time_vert=None,
                     stencil_time_smp=None,
                     reg_basis=rbf.basis.phs3,
                     reg_poly_order=1,
                     reg_time_parameter=None,
                     reg_space_parameter=None,
                     solve_ksp='lgmres',
                     solve_pc='icc',
                     solve_max_itr=1000,
                     solve_atol=1e-6, 
                     solve_rtol=1e-8, 
                     solve_view=False, 
                     cv_itr=100,
                     cv_space_bounds=None,
                     cv_time_bounds=None,
                     cv_plot=False,
                     cv_fold=10,
                     cv_procs=None,
                     bs_itr=10):

  # check for duplicate stations 
  _identify_duplicate_stations(x)

  if cv_space_bounds is None:
    cv_space_bounds = [-4.0,4.0]
  if cv_time_bounds is None:
    cv_time_bounds = [-4.0,4.0]
 
  u = np.asarray(u)

  Nx = x.shape[0]
  Nt = t.shape[0]

  if u.shape != (Nt,Nx):
    raise TypeError('u must have shape (Nt,Nx)')

  if sigma is None:
    sigma = np.ones((Nt,Nx))
  
  else:
    sigma = np.array(sigma,copy=True)
    # replace any infinite uncertainties with 1e100. This does not 
    # seem to introduce any numerical instability and seems to be 
    # sufficient in all cases. Infs need to be replaced in order to 
    # keep the LHS matrix positive definite
    sigma[sigma==np.inf] = 1e10
    
    
  if sigma.shape != (Nt,Nx):
    raise TypeError('sigma must have shape (Nt,Nx)')

  u_flat = u.flatten()
  sigma_flat = sigma.flatten()

  # form space smoothing matrix
  Lx = rbf.fd.diff_matrix(x,
                          N=stencil_size,
                          C=stencil_connectivity,
                          coeffs=np.array([1.0,1.0]),
                          diffs=np.array([[2,0],[0,2]]), 
                          basis=reg_basis,
                          order=reg_poly_order,
                          vert=stencil_space_vert,
                          smp=stencil_space_smp)
  # this produces the traditional finite difference matrix for a 
  # second derivative
  Lt = rbf.fd.diff_matrix(t[:,None],
                          N=3,
                          coeffs=np.array([1.0]),
                          diffs=np.array([[2]]), 
                          basis=reg_basis,
                          order=2,
                          vert=stencil_time_vert,
                          smp=stencil_time_smp)
  # the solution for the first timestep is defined to be zero and so 
  # we do not need the first column
  Lt = Lt[:,1:]

  Lt,Lx = rbf.fd.grid_diff_matrices(Lt,Lx)

  # I will be estimating baseline displacement for each station
  # which have no regularization constraints.  
  ext = scipy.sparse.csr_matrix((Lt.shape[0],Nx))
  Lt = scipy.sparse.hstack((ext,Lt))
  Lt = Lt.tocsr()

  ext = scipy.sparse.csr_matrix((Lx.shape[0],Nx))
  Lx = scipy.sparse.hstack((ext,Lx))
  Lx = Lx.tocsr()

  # build observation matrix
  G = scipy.sparse.eye(Nx*Nt)
  G = G.tocsr()

  # chop off the first Nx columns to make room for the baseline 
  # conditions
  G = G[:,Nx:]

  # add baseline elements
  Bt = scipy.sparse.csr_matrix(np.ones((Nt,1)))
  Bx = scipy.sparse.csr_matrix((0,Nx))
  Bt,Bx = rbf.fd.grid_diff_matrices(Bt,Bx)
  G = scipy.sparse.hstack((Bt,G))
  G = G.tocsr()

  # weigh G and u by the inverse of data uncertainty. this creates 
  # duplicates but G should still be small
  W = scipy.sparse.diags(1.0/sigma_flat,0)
  G = W.dot(G)
  u_flat = W.dot(u_flat)

  # clean up any zero entries
  G.eliminate_zeros()

  # make cross validation testing sets if necessary
  if (reg_time_parameter is None) | (reg_space_parameter is None):
    cv_fold = min(cv_fold,Nx)
    testing_x_sets = modest.cv.chunkify(range(Nx),cv_fold) 
    data_indices = np.arange(Nt*Nx).reshape((Nt,Nx))
    testing_sets = []
    for tx in testing_x_sets:
      testing_sets += [data_indices[:,tx].flatten()]
  
  # estimate damping parameters
  if (reg_time_parameter is None) & (reg_space_parameter is None):
    logger.info(
      'damping parameters were not specified and will now be '
      'estimated with cross validation')

    out = modest.cv.optimal_damping_parameters(
            G,[Lt,Lx],u_flat,itr=cv_itr,fold=testing_sets,
            plot=cv_plot,log_bounds=[cv_time_bounds,cv_space_bounds],
            solver='petsc',ksp=solve_ksp,pc=solve_pc,
            maxiter=solve_max_itr,view=solve_view,atol=solve_atol,
            rtol=solve_rtol,Nprocs=cv_procs)

    reg_time_parameter = out[0][0] 
    reg_space_parameter = out[0][1] 
    
  elif reg_time_parameter is None:
    logger.info(
      'time damping parameter was not specified and will now be '
      'estimated with cross validation')
    out = modest.cv.optimal_damping_parameters(
            G,[Lt,Lx],u_flat,itr=cv_itr,fold=testing_sets,plot=cv_plot,
            log_bounds=[cv_time_bounds,
                        [np.log10(reg_space_parameter)-1e-4,
                         np.log10(reg_space_parameter)+1e-4]],
            solver='petsc',ksp=solve_ksp,pc=solve_pc,
            maxiter=solve_max_itr,view=solve_view,atol=solve_atol,
            rtol=solve_rtol,Nprocs=cv_procs)
    reg_time_parameter = out[0][0]

  elif reg_space_parameter is None:
    logger.info(
      'spatial damping parameter was not specified and will now be '
      'estimated with cross validation')
    out = modest.cv.optimal_damping_parameters(
            G,[Lt,Lx],u_flat,itr=cv_itr,fold=testing_sets,plot=cv_plot,
            log_bounds=[[np.log10(reg_time_parameter)-1e-4,
                         np.log10(reg_time_parameter)+1e-4],
                        cv_space_bounds],
            solver='petsc',ksp=solve_ksp,pc=solve_pc,
            maxiter=solve_max_itr,view=solve_view,atol=solve_atol,
            rtol=solve_rtol,Nprocs=cv_procs)
    reg_space_parameter = out[0][1]


  # this makes matrix copies
  L = scipy.sparse.vstack((reg_time_parameter*Lt,reg_space_parameter*Lx))

  logger.info('solving for predicted displacements ...')
  u_pred = modest.sparse_reg_petsc(G,L,u_flat,
                                   ksp=solve_ksp,pc=solve_pc,
                                   maxiter=solve_max_itr,view=solve_view,
                                   atol=solve_atol,rtol=solve_rtol)
  logger.info('finished')

  logger.info('bootstrapping uncertainty ...')
  sigma_u_pred = _bootstrap_uncertainty(G,L,itr=bs_itr,
                                        ksp=solve_ksp,pc=solve_pc,
                                        maxiter=solve_max_itr,view=solve_view,
                                        atol=solve_atol,rtol=solve_rtol)
  logger.info('finished')

  u_pred = u_pred.reshape((Nt,Nx))
  sigma_u_pred = sigma_u_pred.reshape((Nt,Nx))

  # zero the initial displacements
  u_pred[0,:] = 0.0
  sigma_u_pred[0,:] = 0.0

  return u_pred,sigma_u_pred


