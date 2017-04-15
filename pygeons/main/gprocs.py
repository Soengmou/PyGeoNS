''' 

module of functions that construct *GaussianProcess* instances. The
domain of each GaussianProcess consists of time and two-dimensional
space. 


'''
import numpy as np
import rbf.basis
import rbf.poly
from rbf import gauss


def set_units(units):
  ''' 
  Wrapper for specifying the hyperparameter units for each
  GaussianProcess constructor. This is only used for creating the
  header of the output file from pygeons_treml and pygeons_sreml.
  Units can be written in terms of '{0}' and '{1}' which are
  placeholders for the data units (mm, mm/yr, etc.) and the
  observation space units (km or yr), respectively.
  '''
  def decorator(fin):
    def fout(*args,**kwargs):
      return fin(*args,**kwargs)

    fout.units = units
    fout.n = gauss._get_arg_count(fin)
    if fout.n != len(fout.units):
      raise ValueError(
        'the number of arguments must be equal to the number of unit '
        'specifications') 
    
    return fout  

  return decorator  


# 1D GaussianProcess constructors
#####################################################################
def per_1d():
  ''' 
  Returns a *GaussianProcess* with annual and semiannual sinusoid
  basis functions. The coefficients have zero mean and unit std. dev.
  '''
  def basis(x):
    # no derivatives because im lazy
    out = np.array([np.sin(2*np.pi*x[:,0]/365.25),
                    np.cos(2*np.pi*x[:,0]/365.25),
                    np.sin(4*np.pi*x[:,0]/365.25),
                    np.cos(4*np.pi*x[:,0]/365.25)]).T
    return out

  mu = np.zeros(4)
  sigma = np.ones(4)
  return gauss.gpbfc(basis,mu,sigma,dim=1)


def step_1d(t0):
  ''' 
  Returns a *GaussianProcess* with a heaviside function centered at
  *t0*. The size of the step has zero mean and unit std. dev.
  '''
  def basis(x,diff):
    if diff == (0,):
      out = (x[:,0] >= t0).astype(float)
    else:
      # derivative is zero everywhere (ignore the step at t0)
      out = np.zeros(x.shape[0],dtype=float)  
    
    # turn into an (N,1) array
    out = out[:,None]
    return out

  mu = np.zeros(1)
  sigma = np.ones(1)
  return gauss.gpbfc(basis,mu,sigma,dim=1)


def ramp_1d(t0):
  ''' 
  Returns a *GaussianProcess* with a ramp function centered at
  *t0*. The slope of the ramp is unconstrained
  '''
  def basis(x,diff):
    if diff == (0,):
      out = (x[:,0] - t0)*((x[:,0] >= t0).astype(float))
    elif diff == (1,):
      out = (x[:,0] >= t0).astype(float)
    else:
      # derivative is zero everywhere (ignore the step at t0)
      out = np.zeros(x.shape[0],dtype=float)  
    
    # turn into an (N,1) array
    out = out[:,None]
    return out

  mu = np.zeros(1)
  sigma = np.ones(1)
  return gauss.gpbfc(basis,mu,sigma,dim=1)


def mat32_1d(sigma,cls):
  ''' 
  Returns a *GaussianProcess* with zero mean and a squared exponential
  covariance
  '''
  return gauss.gpiso(rbf.basis.mat32,(0.0,sigma**2,cls),dim=1)


def mat52_1d(sigma,cls):
  ''' 
  Returns a *GaussianProcess* with zero mean and a squared exponential
  covariance
  '''
  return gauss.gpse(rbf.basis.mat52,(0.0,sigma**2,cls),dim=1)


def se_1d(sigma,cls):
  ''' 
  Returns a *GaussianProcess* with zero mean and a squared exponential
  covariance
  '''
  return gauss.gpse((0.0,sigma**2,cls),dim=1)


def exp_1d(sigma,cls):
  ''' 
  Returns a *GaussianProcess* with zero mean and a squared exponential
  covariance
  '''
  return gauss.gpse((0.0,sigma**2,cls),dim=1)


def fogm_1d(s,fc):
  ''' 
  Returns a *GaussianProcess* describing an first-order Gauss-Markov
  process. The autocovariance function is
    
     K(t) = s^2/(4*pi*fc) * exp(-2*pi*fc*|t|)  
   
  which has the corresponding power spectrum 
  
     P(f) = s^2/(4*pi^2 * (f^2 + fc^2))
  
  *fc* can be interpretted as a cutoff frequency which marks the
  transition to a flat power spectrum and a power spectrum that decays
  with a spectral index of two. Thus, when *fc* is close to zero, the
  power spectrum resembles that of Brownian motion.
  '''
  coeff = s**2/(4*np.pi*fc)
  cls   = 1.0/(2*np.pi*fc)
  return gauss.gpexp((0.0,coeff,cls),dim=1)


def bm_1d(w,t0):
  ''' 
  Returns brownian motion with scale parameter *w* and reference time
  *t0*
  '''
  def mean(x):
    out = np.zeros(x.shape[0])  
    return out 

  def cov(x1,x2):
    x1,x2 = np.meshgrid(x1[:,0]-t0,x2[:,0]-t0,indexing='ij')
    x1[x1<0.0] = 0.0
    x2[x2<0.0] = 0.0
    out = np.min([x1,x2],axis=0)
    return w**2*out
  
  return gauss.GaussianProcess(mean,cov,dim=1)  


def ibm_1d(w,t0):
  ''' 
  Returns integrated brownian motion with scale parameter *w* and
  reference time *t0*.
  '''
  def mean(x,diff):
    '''mean function which is zero for all derivatives'''
    out = np.zeros(x.shape[0])
    return out
  
  def cov(x1,x2,diff1,diff2):
    '''covariance function and its derivatives'''
    x1,x2 = np.meshgrid(x1[:,0]-t0,x2[:,0]-t0,indexing='ij')
    x1[x1<0.0] = 0.0
    x2[x2<0.0] = 0.0
    if (diff1 == (0,)) & (diff2 == (0,)):
      # integrated brownian motion
      out = (0.5*np.min([x1,x2],axis=0)**2*
             (np.max([x1,x2],axis=0) -
              np.min([x1,x2],axis=0)/3.0))
  
    elif (diff1 == (1,)) & (diff2 == (1,)):
      # brownian motion
      out = np.min([x1,x2],axis=0)
  
    elif (diff1 == (1,)) & (diff2 == (0,)):
      # derivative w.r.t x1
      out = np.zeros_like(x1)
      idx1 = x1 >= x2
      idx2 = x1 <  x2
      out[idx1] = 0.5*x2[idx1]**2
      out[idx2] = x1[idx2]*x2[idx2] - 0.5*x1[idx2]**2
  
    elif (diff1 == (0,)) & (diff2 == (1,)):
      # derivative w.r.t x2
      out = np.zeros_like(x1)
      idx1 = x2 >= x1
      idx2 = x2 <  x1
      out[idx1] = 0.5*x1[idx1]**2
      out[idx2] = x2[idx2]*x1[idx2] - 0.5*x2[idx2]**2
  
    else:
      raise ValueError(
        'The *GaussianProcess* is not sufficiently differentiable')
  
    return w**2*out

  return gauss.GaussianProcess(mean,cov,dim=1)  

# 2D GaussianProcess constructors
#####################################################################
def se_2d(sigma,cls):
  ''' 
  Returns a *GaussianProcess* with zero mean and a squared exponential
  covariance
  '''
  return gauss.gpse((0.0,sigma**2,cls),dim=2)

def exp_2d(sigma,cls):
  ''' 
  Returns a *GaussianProcess* with zero mean and a squared exponential
  covariance
  '''
  return gauss.gpse((0.0,sigma**2,cls),dim=2)

def mat32_2d(sigma,cls):
  ''' 
  Returns a *GaussianProcess* with zero mean and a squared exponential
  covariance
  '''
  return gauss.gpiso(rbf.basis.mat32,(0.0,sigma**2,cls),dim=2)


def mat52_2d(sigma,cls):
  ''' 
  Returns a *GaussianProcess* with zero mean and a squared exponential
  covariance
  '''
  return gauss.gpse(rbf.basis.mat52,(0.0,sigma**2,cls),dim=2)


# 3D GaussianProcess constructors
#####################################################################
# GaussianProcesses constructors for strain calculation
def kernel_product(gp1,gp2):
  def mean(x,diff):
    return np.zeros(x.shape[0])

  def covariance(x1,x2,diff1,diff2):
    out  = gp1._covariance(x1[:,[0]],x2[:,[0]],
                           diff1[[0]],diff2[[0]])
    out *= gp2._covariance(x1[:,[1,2]],x2[:,[1,2]],
                           diff1[[1,2]],diff2[[1,2]])
    return out
  
  return gauss.GaussianProcess(mean,covariance)  


@set_units([])
def null():
  '''Null GaussianProcess'''
  return gauss.GaussianProcess(gauss._zero_mean,
                               gauss._zero_covariance,
                               basis=gauss._empty_basis,
                               dim=3)
                               

@set_units([])
def p11():
  ''' 
  Gaussian process with polynomial basis functions (1,0,0), (1,1,0),
  and (1,0,1)
  '''
  def basis(x,diff):
    powers = np.array([[1,0,0],[1,1,0],[1,0,1]])
    out = rbf.poly.mvmonos(x,powers,diff)
    return out

  return gauss.gpbfci(basis,dim=3)  


@set_units([])
def p21():
  ''' 
  Gaussian process with polynomial basis functions (1,0,0), (1,1,0),
  (1,0,1), (2,0,0), (2,1,0), and (2,0,1).
  '''
  def basis(x,diff):
    powers = np.array([[1,0,0],[1,1,0],[1,0,1],
                       [2,0,0],[2,1,0],[2,0,1]])
    out = rbf.poly.mvmonos(x,powers,diff)
    return out
  
  return gauss.gpbfci(basis,dim=3)  
  

@set_units(['mm','yr','km'])
def se_se(a,b,c):
  tgp = se_1d(a,b)
  sgp = se_2d(1.0,c)
  return kernel_product(tgp,sgp)


@set_units(['mm*yr^-0.5','yr^-1','km'])
def fogm_se(a,b,c):
  tgp = fogm_1d(a,b)
  sgp = se_2d(1.0,c)
  return kernel_product(tgp,sgp)


@set_units(['mm*yr^-0.5','mjd','km'])
def bm_se(a,b,c):
  tgp = bm_1d(a,b)
  sgp = se_2d(1.0,c)
  return kernel_product(tgp,sgp)


@set_units(['mm*yr^-1.5','mjd','km'])
def ibm_se(a,b,c):
  tgp = ibm_1d(a,b)
  sgp = se_2d(1.0,c)
  return kernel_product(tgp,sgp)


@set_units(['mm','yr','km'])
def mat32_se(a,b,c):
  tgp = mat32_1d(a,b)
  sgp = se_2d(1.0,c)
  return kernel_product(tgp,sgp)


@set_units(['mm','yr','km'])
def gpmat52_se(a,b,c):
  tgp = mat52_1d(a,b)
  sgp = se_1d(1.0,c)
  return kernel_product(tgp,sgp)


@set_units(['mm','km'])
def per_se(a,b):
  tgp = per_1d()
  sgp = se_1d(a,c)
  return kernel_product(tgp,sgp)


@set_units(['mm','km'])
def step_se(a,b):
  tgp = step_1d()
  sgp = se_1d(a,c)
  return kernel_product(tgp,sgp)


@set_units(['mm','km'])
def ramp_se(a,b):
  tgp = ramp_1d()
  sgp = se_1d(a,c)
  return kernel_product(tgp,sgp)
    

# create a dictionary of all Gaussian process constructors in this
# module
CONSTRUCTORS = {'null':gpnull,
                'seasonal':gpseasonal,
                'const':gpconst,
                'linear':gplinear,
                'quad':gpquad,
                'step':gpstep,
                'ramp':gpramp,
                'mat32':gpmat32,
                'mat52':gpmat52,
                'se':gpse,
                'fogm':gpfogm,
                'bm':gpbm,
                'ibm':gpibm}
  
def gpcomp(model,args):
  ''' 
  Returns a composite Gaussian process. The components are specified
  with the *model* string, and the arguments for each component are
  specied with *args*. For example,
  
  >>> gpcomp('fogm+se',(1.0,2.0,3.0,4.0)) 
  
  creates a GaussianProcess composed of a FOGM and an SE model. The
  first two arguments are passed to *gpfogm* and the second two
  arguments are passed to *se*
  '''
  args = list(args)
  models = model.strip().split('+')
  cs = [CONSTRUCTORS[m] for m in models] # constructor for each component
  n  = sum(ci.n for ci in cs)
  if len(args) != n:
    raise ValueError(
      '%s parameters were specified for the model "%s", but it '
      'requires %s parameters.\n' %(len(args),model,n))
  
  gp = gpnull()
  for ci in cs:
    gp += ci(*(args.pop(0) for i in range(ci.n)))
  
  return gp
  

def get_units(model):
  ''' 
  returns the units for the GaussianProcess parameters
  '''
  models = model.strip().split('+')
  cs = [CONSTRUCTORS[m] for m in models]
  units = []
  for ci in cs:
    units += ci.units
  
  return units  
