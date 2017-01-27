''' 
This module provides a quiver function which allows for error ellipses.
'''
import numpy as np
from matplotlib.quiver import Quiver as _Quiver
from matplotlib.collections import EllipseCollection
from matplotlib.backends import pylab_setup
from matplotlib.pyplot import sci
from matplotlib.pyplot import gca
from scipy.spatial import cKDTree
import warnings
_backend_mod, new_figure_manager, draw_if_interactive, _show = pylab_setup()


def _estimate_scale(x,y,u,v):
  pos = np.array([x,y]).T
  # return a scale of 1 if there is only one datum
  if pos.shape[0] == 0:
    return 1.0
                                
  T = cKDTree(pos)
  average_dist = np.mean(T.query(pos,2)[0][:,1])
  average_length = np.mean(np.sqrt(u**2 + v**2))
  return average_length/average_dist   


def compute_abphi(sigma_x,sigma_y,rho):
  n = len(sigma_x)
  a = []
  b = []
  phi = []
  for i in range(n):
    if ((not np.isfinite(sigma_x[i])) |
        (not np.isfinite(sigma_y[i])) | 
        (not np.isfinite(rho[i]))):
      # this block should run if the uncertainties or correlations are 
      # not finite or are masked
      a += [0.0]
      b += [0.0]
      phi += [0.0]
      continue

    sigma_xy = rho[i]*sigma_x[i]*sigma_y[i]
    cov_mat = np.array([[sigma_x[i]**2,sigma_xy],
                        [sigma_xy,sigma_y[i]**2]])
    val,vec = np.linalg.eig(cov_mat)
    maxidx = np.argmax(val)
    minidx = np.argmin(val)
    a += [np.sqrt(val[maxidx])]
    b += [np.sqrt(val[minidx])]
    phi += [np.arctan2(vec[:,maxidx][1],vec[:,maxidx][0])]
    
  a = np.array(a)
  b = np.array(b)
  phi = np.array(phi)*180/np.pi
  return a,b,phi


def quiver(*args, **kw):
    ax = gca()
    # allow callers to override the hold state by passing hold=True|False               
    washold = ax.ishold()
    hold = kw.pop('hold', None)
    if hold is not None:
        ax.hold(hold)

    try:
      if not ax._hold:
        ax.cla()

      q = Quiver(ax, *args, **kw)
      ax.add_collection(q, autolim=True)
      ax.autoscale_view()
      draw_if_interactive()

    finally:
      ax.hold(washold)

    sci(q)
    return q


class Quiver(_Quiver):
  def __init__(self,ax,*args,**kwargs):
    if 'sigma' in kwargs:
      scale_units = kwargs.get('scale_units','xy')
      kwargs['scale_units'] = scale_units
      if kwargs['scale_units'] != 'xy':
        raise ValueError('scale units must be "xy" when sigma is given')

      angles = kwargs.get('angles','xy')
      kwargs['angles'] = angles
      if kwargs['angles'] != 'xy':
        raise ValueError('angles must be "xy" when sigma is given')

    sigma = kwargs.pop('sigma',None)

    ellipse_kwargs = kwargs.pop('ellipse_kwargs',{})
    if 'offsets' in ellipse_kwargs:
      raise ValueError('cannot specify ellipse offsets')
    if 'units' in ellipse_kwargs:
      raise ValueError('cannot specify ellipse units')
    
    self.ellipse_kwargs = {'edgecolors':'k',
                           'facecolors':'none',
                           'linewidths':1.0}
    self.ellipse_kwargs.update(ellipse_kwargs)
    
    self.ellipsoids = None

    _Quiver.__init__(self,ax,*args,**kwargs)

    if sigma is not None:
      if self.scale is None:
        self.scale = _estimate_scale(self.X,self.Y,self.U,self.V)
        
      su,sv,rho = sigma[0],sigma[1],sigma[2]
      self._update_ellipsoids(su,sv,rho)


  def _update_ellipsoids(self,su,sv,rho):
    self.scale_units = 'xy'
    self.angles = 'xy'
    tips_x = self.X + self.U/self.scale
    tips_y = self.Y + self.V/self.scale
    tips = np.array([tips_x,tips_y]).transpose()
    a,b,angle = compute_abphi(su,sv,rho)
    width = 2.0*a/self.scale
    height = 2.0*b/self.scale
    if self.ellipsoids is not None: 
      self.ellipsoids.remove()

    # do not draw ellipses which are too small  
    too_small = 0.001
    length = np.sqrt((self.U/self.scale)**2 + (self.V/self.scale)**2)
    with warnings.catch_warnings():
      # do not print out zero division warning
      warnings.simplefilter("ignore")
      is_not_too_small = ((np.nan_to_num(width/length) > too_small) | 
                          (np.nan_to_num(height/length) > too_small))

    width = width[is_not_too_small]
    height = height[is_not_too_small]
    angle = angle[is_not_too_small]
    tips = tips[is_not_too_small]    
    
    # dont add ellipses if there are no ellipses to add
    if any(is_not_too_small):
      self.ellipsoids = EllipseCollection(width,height,angle,
                                          units=self.scale_units,
                                          offsets = tips,
                                          transOffset=self.ax.transData,
                                          **self.ellipse_kwargs)

      self.ax.add_collection(self.ellipsoids)

    else:
      self.ellipsoids = None      

  def set_UVC(self,u,v,C=None,sigma=None):
    if C is None:
      _Quiver.set_UVC(self,u,v)
    else:
      _Quiver.set_UVC(self,u,v,C)

    if sigma is not None:
      su,sv,rho = sigma[0],sigma[1],sigma[2]
      self._update_ellipsoids(su,sv,rho)
      
  def remove(self):  
    # remove the quiver and ellipsoid collection
    _Quiver.remove(self)    
    if self.ellipsoids is not None:
      self.ellipsoids.remove()

