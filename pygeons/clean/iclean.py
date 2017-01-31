from __future__ import division
import numpy as np
from pygeons.plot.iview import InteractiveViewer
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import logging
import warnings
logger = logging.getLogger(__name__)


def weighted_mean(x,sigma,axis=None):
  ''' 
  Computes the weighted mean of *x* with uncertainties *sigma*
  
  Parameters
  ----------
    x : (..., N,...) array
    
    sigma : (..., N,...) array

    axis : int, optional
    
  Notes
  -----
  If all uncertainties along the axis are np.inf then then the
  returned mean is np.nan with uncertainty is np.inf
    
  If there are 0 entries along the axis then the returned mean is
  np.nan with uncertainty np.inf
    
  zero uncertainties will raise an error
    
  '''
  x = np.array(x,copy=True)
  sigma = np.asarray(sigma)
  # convert any nans to zeros
  x[np.isnan(x)] = 0.0
  if x.shape != sigma.shape:
    raise ValueError('x and sigma must have the same shape')

  # make sure uncertainties are positive
  if np.any(sigma <= 0.0):
    raise ValueError('uncertainties must be positive and nonzero')

  numer = np.sum(x/sigma**2,axis=axis)
  denom = np.sum(1.0/sigma**2,axis=axis)
  with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    # out_value can be nan if the arrays have zero length along axis 
    # or if sigma is inf. out_sigma will be inf in that case 
    out_value = numer/denom
    out_sigma = np.sqrt(1.0/denom)

  return out_value,out_sigma



class InteractiveCleaner(InteractiveViewer):
  ''' 
                  ---------------------------------
                  PyGeoNS Interactive Cleaner (PIC)
                  ---------------------------------

An interactive figure for removing outliers and time series jumps

Controls
--------
Enter : Edit the configurable parameters through the command line.
  Variables can be defined using any functions in the numpy, 
  matplotlib, or base python namespace.

Left : Move back 1 time step (Ctrl-Left and Alt-Left move back 10 and 
  100 respectively).

Right : Move forward 1 time step (Ctrl-Right and Alt-Right move 
forward 10 and 100 respectively).

Up : Move forward 1 station (Ctrl-Left and Alt-Left move back 10 and 
  100 respectively).
          
Down : Move back 1 station (Ctrl-Right and Alt-Right move forward 10 
  and 100 respectively).
          
R : Redraw figures.

V : Toggle whether to hide the vertical deformation.

H : Toggle whether to hide the station marker.

D : Enables outlier removal mode while pressed.  Click and drag on the
  time series axes to remove outliers within a time interval.

J : Enables jump removal mode while pressed. Jumps are estimated by
  taking a weighted mean of the data over a time interval before and 
  after the jump. Click on the time series axes to identify a jump and 
  drag the cursor over the desired time interval.

A : If pressed while holding down D or J, then jumps or outliers are 
  removed for all stations.
    
Notes
-----
Stations may also be selected by clicking on them.

Exit PIC by closing the figures.

Key bindings only work when the active window is one of the PIC 
figures

---------------------------------------------------------------------     
  '''
  def __init__(self,t,x,
               u=None,v=None,z=None,
               su=None,sv=None,sz=None,
               **kwargs):
    ''' 
    Parameters
    ----------
      t : (Nt,) array
        observation times
        
      x : (Nx,2) array
        observation positions
        
      u : (Nt,Nx) array
        east component

      v : (Nt,Nx) array
        north component

      z : (Nt,Nx) array
        vertical component

      su : (Nt,Nx) array, optional
        standard deviation of east component

      sv : (Nt,Nx) array, optional
        standard deviation of north component

      sz : (Nt,Nx) array, optional
        standard deviation of vertical component
        
    Note
    ----
      only one of u, v, and z need to be specified
    '''
    data_set_labels = kwargs.pop('data_set_labels',['edited data'])
    color_cycle = kwargs.pop('color_cycle',['k'])
    InteractiveViewer.__init__(self,t,x,
                               u=[u],v=[v],z=[z],
                               su=[su],sv=[sv],sz=[sz],
                               color_cycle=color_cycle,
                               data_set_labels=data_set_labels,
                               **kwargs)
    self._mode = None
    self._apply_to_all = False
    self._mouse_is_pressed = False

  def get_data(self):
    u = self.data_sets[0][:,:,0]
    v = self.data_sets[0][:,:,1]
    z = self.data_sets[0][:,:,2]
    su = self.sigma_sets[0][:,:,0]
    sv = self.sigma_sets[0][:,:,1]
    sz = self.sigma_sets[0][:,:,2]
    return (u,v,z,su,sv,sz)
    
  def connect(self):
    self.ts_fig.canvas.mpl_connect('button_press_event',self.on_mouse_press)
    self.ts_fig.canvas.mpl_connect('motion_notify_event',self.on_mouse_move)
    self.ts_fig.canvas.mpl_connect('button_release_event',self.on_mouse_release)
    self.ts_fig.canvas.mpl_connect('key_release_event',self.on_key_release)
    self.map_fig.canvas.mpl_connect('key_release_event',self.on_key_release)
    InteractiveViewer.connect(self)
        
  def remove_jump(self,jump_time,radius):
    data = self.data_sets[0]
    # expand sigma to the size of data
    sigma = self.sigma_sets[0]

    xidx = self.config['xidx']
    tidx_right, = np.nonzero((self.t > jump_time) & 
                             (self.t <= (jump_time+radius)))
    tidx_left, = np.nonzero((self.t < jump_time) & 
                            (self.t >= (jump_time-radius)))

    mean_right,sigma_right = weighted_mean(data[tidx_right,xidx],
                                           sigma[tidx_right,xidx],
                                           axis=0)
    mean_left,sigma_left = weighted_mean(data[tidx_left,xidx],
                                         sigma[tidx_left,xidx],
                                         axis=0)
    # jump for each component
    jump = mean_right - mean_left
    # uncertainty in the jump estimate
    jump_sigma = np.sqrt(sigma_right**2 + sigma_left**2)
    # find indices of all times after the jump
    all_tidx_right, = np.nonzero(self.t > jump_time)
    # remove jump from observations made after the jump 
    new_pos = data[all_tidx_right,xidx] - jump[None]
    # increase uncertainty 
    new_var = sigma[all_tidx_right,xidx]**2 + jump_sigma[None]**2
    new_sigma = np.sqrt(new_var)
    self.data_sets[0][all_tidx_right,xidx] = new_pos
    self.sigma_sets[0][all_tidx_right,xidx] = new_sigma
    name = self.station_labels[xidx]
    logger.info('removed jump at time %g for station %s using data from time %g to %g\n' % 
                (jump_time,name,jump_time-radius,jump_time+radius))
      
    
  def remove_outliers(self,start_time,end_time):
    xidx = self.config['xidx']
    tidx, = np.nonzero((self.t >= start_time) & (self.t <= end_time))
    self.data_sets[0][tidx,xidx] = np.nan
    self.sigma_sets[0][tidx,xidx] = np.inf
    name = self.station_labels[xidx]
    logger.info('removed data from time %g to %g for station %s\n' % (start_time,end_time,name))
          

  def remove_jump_all(self,jump_time,radius):
    xidx = self.config['xidx']
    N = self.data_sets[0].shape[1]
    for i in range(N):
      self.config['xidx'] = i
      self.remove_jump(jump_time,radius)

    self.config['xidx'] = xidx


  def remove_outliers_all(self,start_time,end_time):
    xidx = self.config['xidx']
    N = self.data_sets[0].shape[1]
    for i in range(N):
      self.config['xidx'] = i
      self.remove_outliers(start_time,end_time)

    self.config['xidx'] = xidx
     
  def on_mouse_press(self,event):
    # ignore if not the left button
    if event.button != 1: return
    # ignore if the event was not in an axis
    if event.inaxes is None: return
    # ignore if the event was not in the time series figure
    if not event.inaxes.figure is self.ts_fig: return
    self._mouse_is_pressed = True
    self._t1 = event.xdata
    self.rects = []
    self.vlines = []
    for ax in self.ts_ax:
      ymin,ymax = ax.get_ylim()
      r = Rectangle((self._t1,ymin),0.0,ymax-ymin,color='none',alpha=0.5,edgecolor=None)
      self.rects += [r]
      self.vlines += [ax.vlines(self._t1,ymin,ymax,color='none')]
      ax.add_patch(r)
          
    self.ts_fig.canvas.draw()  
        
  def on_mouse_move(self,event):
    # do nothing is a mouse button is not being held down
    if not self._mouse_is_pressed: return
    # ignore if the event was not in an axis
    if event.inaxes is None: return
    # ignore if the event was not in the time series figure
    if not event.inaxes.figure is self.ts_fig: return

    self._t2 = event.xdata
    for r,v in zip(self.rects,self.vlines):
      if self._mode == 'OUTLIER_REMOVAL':
        r.set_width(self._t2 - self._t1) 
        r.set_x(self._t1)
        r.set_color('r')
        v.set_color('k')
        
      elif self._mode == 'JUMP_REMOVAL':
        r.set_width(2*(self._t2 - self._t1))
        r.set_x(self._t1 - (self._t2 - self._t1))
        r.set_color('b')
        v.set_color('k')
       
      else:
        r.set_width(0.0)
        r.set_color('none')
        v.set_color('none')
            
    self.ts_fig.canvas.draw()  

  def on_mouse_release(self,event):
    # ignore if not the left button
    if event.button != 1: return
    # do nothing is a mouse button was not clicked in the axis
    if not self._mouse_is_pressed: return
    self._mouse_is_pressed = False
    # remove the rectangles no matter where the button was released
    for r,v in zip(self.rects,self.vlines):
      r.remove()
      v.remove()

    self.ts_fig.canvas.draw()  
    # only act on this event if the following conditions are met
    # ignore if the event was not in an axis
    if event.inaxes is None: return
    # ignore if the event was not in the time series figure
    if not event.inaxes.figure is self.ts_fig: return
    self._t2 = event.xdata
    # act according to self._mode at the time of release
    if self._mode == 'OUTLIER_REMOVAL':
      mint = min(self._t1,self._t2)
      maxt = max(self._t1,self._t2)
      if self._apply_to_all:
        self.remove_outliers_all(mint,maxt) 
      else:
        self.remove_outliers(mint,maxt) 
        
      # keep the time series axis limits fixed
      xlims = [i.get_xlim() for i in self.ts_ax]      
      ylims = [i.get_ylim() for i in self.ts_ax]      
      self.update()   
      for i,j in zip(self.ts_ax,xlims): i.set_xlim(j)
      for i,j in zip(self.ts_ax,ylims): i.set_ylim(j)
      self.ts_fig.canvas.draw()  

    elif self._mode == 'JUMP_REMOVAL':
      if self._apply_to_all:
        self.remove_jump_all(self._t1,abs(self._t2-self._t1))
      else:
        self.remove_jump(self._t1,abs(self._t2-self._t1))
        
      # keep the time series axis limits fixed
      xlims = [i.get_xlim() for i in self.ts_ax]      
      ylims = [i.get_ylim() for i in self.ts_ax]      
      self.update()   
      for i,j in zip(self.ts_ax,xlims): i.set_xlim(j)
      for i,j in zip(self.ts_ax,ylims): i.set_ylim(j)
      self.ts_fig.canvas.draw()  
    
    else: 
      return

  def _set_mode(self,name):
    if self._mode is None:
      self._mode = name
      logger.info('enabled %s mode\n' % name) 

  def _unset_mode(self,name):
    if self._mode is name:
      self._mode = None
      logger.info('disabled %s mode\n' % name) 
  
  def on_key_press(self,event):
    # disable c
    if event.key == 'c':
      return
              
    elif event.key == 'd':
      self._set_mode('OUTLIER_REMOVAL')
      self.on_mouse_move(event)

    elif event.key == 'j':
      self._set_mode('JUMP_REMOVAL')
      self.on_mouse_move(event)

    elif event.key == 'a':
      logger.info('cleaning operations will be applied to all stations\n')
      self._apply_to_all = True
      
    else:
      InteractiveViewer.on_key_press(self,event)
        
  def on_key_release(self,event):
    if event.key == 'd':
      self._unset_mode('OUTLIER_REMOVAL')
      self.on_mouse_move(event)

    elif event.key == 'j':
      self._unset_mode('JUMP_REMOVAL')
      self.on_mouse_move(event)

    elif event.key == 'a':
      logger.info('cleaning operations will be applied to the current station\n')
      self._apply_to_all = False
  

def interactive_cleaner(*args,**kwargs):
  ''' 
  Runs InteractiveCleaner and returns the kept data
  '''
  ic = InteractiveCleaner(*args,**kwargs)
  ic.connect()
  plt.show()
  return ic.get_data()
  
                                      
