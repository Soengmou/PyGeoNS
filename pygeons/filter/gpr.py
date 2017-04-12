''' 
Contains a Gaussian process regression function that has been 
specialized for PyGeoNS
'''
import numpy as np
import logging
import rbf.gauss
from pygeons.mp import parmap
from pygeons.filter.gprocs import gpcomp
logger = logging.getLogger(__name__)


def _is_outlier(d,s,sigma,mu,p,tol):
  ''' 
  Identifies which points in *d* are outliers based on the prior
  defined by *sigma*, *mu*, and *p*.
  
  d : (N,) observations 
  s : (N,) observation uncertainties
  sigma : (N,N) prior covariance matrix
  mu : (N,) prior mean
  p : (N,P) prior basis functions
  tol : outlier tolerance
  
  returns a boolean array indicating which points are outliers
  '''
  out = np.zeros(d.shape[0],dtype=bool)
  while True:
    q = sum(~out)
    a = sigma[np.ix_(~out,~out)] + np.diag(s[~out]**2)
    b = rbf.gauss._cholesky_block_inv(a,p[~out])
    c = np.empty((d.shape[0],b.shape[0]))
    c[:,:q] = sigma[:,~out]
    c[:,q:] = p
    r = np.empty(b.shape[0])
    r[:q] = d[~out] - mu[~out]
    r[q:] = 0.0
    pred = mu + c.dot(b).dot(r)
    res = np.abs(pred - d)/s
    rms = np.sqrt(np.mean(res[~out]**2))
    if np.all(out == (res > tol*rms)):
      break

    else:
      out = (res > tol*rms)

  return out


def gpr(y,d,s,
        prior_model,prior_params,
        x=None,
        diff=None,
        noise_model='null',
        noise_params=(),
        tol=4.0,
        procs=0,
        return_sample=False):
  ''' 
  Performs Guassian process regression. 
  
  Parameters
  ----------
  y : (N,D) array
    Observation points.

  d : (...,N) array
    Observed data at *y*.
  
  s : (...,N) array
    Data uncertainty.
  
  prior_model : str
    String specifying the prior model
  
  prior_params : 2-tuple
    Hyperparameters for the prior model.
  
  x : (M,D) array, optional
    Evaluation points.

  diff : (D,), optional         
    Specifies the derivative of the returned values. 

  noise_model : str, optional
    String specifying the noise model
    
  noise_params : 2-tuple, optional
    Hyperparameters for the noise model
    
  tol : float, optional
    Tolerance for the outlier detection algorithm.
    
  procs : int, optional
    Distribute the tasks among this many subprocesses. 
  
  return_sample : bool, optional
    If True then *out_mean* is a sample of the posterior.

  '''  
  y = np.asarray(y,dtype=float)
  d = np.asarray(d,dtype=float)
  s = np.asarray(s,dtype=float)
  if diff is None:
    diff = np.zeros(y.shape[1],dtype=int)

  if x is None:
    x = y

  m = x.shape[0]
  bcast_shape = d.shape[:-1]
  q = int(np.prod(bcast_shape))
  n = y.shape[0]
  d = d.reshape((q,n))
  s = s.reshape((q,n))

  def task(i):
    logger.debug('Processing dataset %s of %s ...' % (i+1,q))
    if np.any(s[i] <= 0.0):
      raise ValueError(
        'At least one datum has zero or negative uncertainty.')
    
    # if the uncertainty is inf then the data is considered missing
    # and will be tossed out
    toss = np.isinf(s[i])
    yi = y[~toss] 
    di = d[i,~toss]
    si = s[i,~toss]

    prior_gp = gpcomp(prior_model,prior_params)
    noise_gp = gpcomp(noise_model,noise_params)    
    full_gp  = prior_gp + noise_gp 

    full_sigma = full_gp.covariance(yi,yi) # model covariance
    full_mu = full_gp.mean(yi) # model mean
    full_p  = full_gp.basis(yi) # model basis functions
    toss = _is_outlier(di,si,full_sigma,full_mu,full_p,tol)
    logger.info('Detected %s outliers out of %s observations' % (sum(toss),len(toss)))
    yi = yi[~toss] 
    di = di[~toss]
    si = si[~toss]

    noise_sigma = np.diag(si**2) + noise_gp.covariance(yi,yi)
    noise_p     = noise_gp.basis(yi)
    # condition the prior with the data
    post_gp = prior_gp.condition(yi,di,sigma=noise_sigma,p=noise_p)
    post_gp = post_gp.differentiate(diff)
    if return_sample:
      out_mean_i = post_gp.sample(x)
      out_sigma_i = np.zeros_like(out_mean_i)
    else:
      out_mean_i,out_sigma_i = post_gp.meansd(x)

    return out_mean_i,out_sigma_i
    
  def task_with_error_catch(i):    
    try:
      return task(i)

    except Exception as err:  
      logger.info(
        'An error was raised when processing dataset %s:\n%s\n ' 
        'The returned expected values and uncertainties will be NaN '
        'and INF, respectively.' % ((i+1),repr(err)))
        
      out_mean_i = np.full(x.shape[0],np.nan)
      out_sigma_i = np.full(x.shape[0],np.inf)
      return out_mean_i,out_sigma_i

  out = parmap(task_with_error_catch,range(q),workers=procs)
  out_mean = np.array([k[0] for k in out])
  out_sigma = np.array([k[1] for k in out])
  out_mean = out_mean.reshape(bcast_shape + (m,))
  out_sigma = out_sigma.reshape(bcast_shape + (m,))
  return out_mean,out_sigma


# Gaussian process regression function which is specifically designed
# for data that has two spatial dimensions and one time dimension.
def gpr3d(t,x,d,s,
          prior_model,prior_params,
          out_t=None,
          out_x=None,
          diff=None,
          noise_model='null',
          noise_params=(),
          tol=4.0,
          procs=0,
          return_sample=False):
  ''' 
  Performs Guassian process regression. 
  
  Parameters
  ----------
  t : (Nt,1) array
    Observation times.
  
  x : (Nx,2) array
    Observation positions.  

  d : (Nt,Nx) array
    Grid of observations at time *t* and position *x*. 
  
  s : (Nt,Nx) array
    Grid of observation uncertainties
  
  prior_model : str
    String specifying the prior model
  
  prior_params : 2-tuple
    Hyperparameters for the prior model.
  
  out_t : (Mt,) array, optional
    Output times
  
  out_x : (Mx,2) array, optional
    Output positions  

  diff : (3,), optional         
    Tuple specifying the derivative of the returned values. First
    element is the time derivative, and the second two elements are
    the space derivatives.

  noise_model : str, optional
    String specifying the noise model
    
  noise_params : 2-tuple, optional
    Hyperparameters for the noise model
    
  tol : float, optional
    Tolerance for the outlier detection algorithm.
    
  procs : int, optional
    Distribute the tasks among this many subprocesses. 
  
  return_sample : bool, optional
    If True then *out_mean* is a sample of the posterior.

  '''  
  t = np.asarray(t,dtype=float)
  x = np.asarray(x,dtype=float)
  d = np.asarray(d,dtype=float)
  s = np.asarray(s,dtype=float)
  if diff is None:
    diff = np.zeros(3,dtype=int)

  if out_t is None:
    out_t = t

  if out_x is None:
    out_x = x

  d_flat = d.flatten()
  s_flat = s.flatten()
  
  # Do a data check to make sure that there are no stations or times
  # with no data? is it needed

  # if the uncertainty is inf then the data is considered missing
  # and will be tossed out
  toss = np.isinf(s)
  ti = y[~toss] 
  di = d[~toss]
  si = s[~toss]

  prior_gp = gpcomp(prior_model,prior_params)
  noise_gp = gpcomp(noise_model,noise_params)    
  full_gp  = prior_gp + noise_gp 

  full_sigma = full_gp.covariance(yi,yi) # model covariance
  full_mu = full_gp.mean(yi) # model mean
  full_p  = full_gp.basis(yi) # model basis functions
  toss = _is_outlier(di,si,full_sigma,full_mu,full_p,tol)
  logger.info('Detected %s outliers out of %s observations' % (sum(toss),len(toss)))
  yi = yi[~toss] 
  di = di[~toss]
  si = si[~toss]

  noise_sigma = np.diag(si**2) + noise_gp.covariance(yi,yi)
  noise_p     = noise_gp.basis(yi)
  # condition the prior with the data
  post_gp = prior_gp.condition(yi,di,sigma=noise_sigma,p=noise_p)
  post_gp = post_gp.differentiate(diff)
  if return_sample:
    out_mean = post_gp.sample(x)
    out_sigma = np.zeros_like(out_mean_i)
  else:
    out_mean,out_sigma = post_gp.meansd(x)

  return out_mean,out_sigma
