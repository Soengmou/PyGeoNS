#!/usr/bin/env python
from __future__ import division
import numpy as np
from pygeons.smooth import network_smoother
from pygeons.view import InteractiveViewer
from pygeons.view import without_interactivity
from pygeons.downsample import weighted_mean
import matplotlib.pyplot as plt
import pygeons.diff
import pygeons.cuts
from scipy.spatial import cKDTree
import warnings
import h5py

def most(a,axis=None,cutoff=0.5):
  ''' 
  behaves like np.all but returns True if the percentage of Trues
  is greater than or equal to cutoff
  '''
  a = np.asarray(a,dtype=bool)
  if axis is None:
    b = np.prod(a.shape)
  else:
    b = a.shape[axis]

  asum = np.sum(a,axis=axis)
  return asum >= b*cutoff


def outliers(u,t,x,sigma=None,
             time_scale=None,time_cuts=None,tol=3.0,
             **kwargs):
  ''' 
  returns indices of time series outliers
  
  An observation is an outlier if the residual between an observation 
  and a smoothed prediction to that observation exceeds tol times the 
  standard deviation of all residuals for the station.  If sigma is 
  given then the residuals are first weighted by sigma. This function 
  removes outliers iteratively, where smoothed curves and residual 
  standard deviations are recomputed after each outlier is removed.
  
  Parameters
  ----------
    u : (Nt,Nx) array

    t : (Nt,) array
    
    x : (Nx,2) array
      this is only used when time_cuts has spatial dependence
      
    sigma : (Nt,Nx) array, optional
    
    time_scale : float, optional
    
    time_cuts : TimeCuts instance, optional
    
    tol : float, optional
    
  Returns
  -------
    row_idx : (K,) int array
      row indices of outliers 
    
    col_idx : (L,) int array
      column indices of outliers

  Note
  ----
    masked data needs to be indicated by setting sigma to np.inf.  
    Values where sigma is set to np.inf are explicitly ignored when 
    computing the residual standard deviation. Simply setting sigma 
    equal to a very large number will produce incorrect results.
  '''
  u = np.asarray(u)
  t = np.asarray(t)
  x = np.asarray(x)
    
  if not (tol > 0.0):
    raise ValueError('tol must be greater than zero')
    
  if sigma is None:
    sigma = np.ones(u.shape)
  else:
    # elements in sigma will be changed and so a copy is needed
    sigma = np.array(sigma,copy=True)
    
  rout = np.zeros((0,),dtype=int)
  cout = np.zeros((0,),dtype=int)
  itr = 0  
  while True:
    ri,ci = _outliers(u,t,x,sigma,
                      time_scale,time_cuts,tol,
                      **kwargs)
    print('removed %s outliers on iteration %s' % (ri.shape[0],itr))
    if ri.shape[0] == 0:
      break

    # mark the points as outliers before the next iteration
    sigma[ri,ci] = np.inf
    rout = np.concatenate((rout,ri))      
    cout = np.concatenate((cout,ci))      
    itr += 1
        
  return rout,cout  
  

def _outliers(u,t,x,sigma,
              time_scale,time_cuts,tol,
              **kwargs):
  ''' 
  single iteration of outliers 
  '''
  zero_tol = 1e-10
  Nt,Nx = u.shape
    
  ds = pygeons.diff.acc()
  ds['time']['cuts'] = time_cuts
  upred,upert = network_smoother(
                  u,t,x,sigma=sigma,
                  diff_specs=[ds],
                  time_scale=time_scale,
                  perts=0,**kwargs)
  res = u - upred
  # it is possible that there are not enough observations to make the 
  # problem overdetermined. In such case the solution should be exact. 
  # If the residual is less than zero tol then we can assume the 
  # solution is supposed to be exact and any errors are due to 
  # numerical rounding. 
  res[np.abs(res) < zero_tol] = 0.0
  if sigma is None:
    sigma = np.ones((Nt,Nx))

  # normalize data by weight
  res /= sigma

  # compute standard deviation of weighted residuals for each station 
  # and ignore missing data marked with sigma=np.inf. 
  res[np.isinf(sigma)] = np.nan
  with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    std = np.nanstd(res,axis=0)[None,:].repeat(Nt,axis=0)
    # if there are too few degrees of freedom then make std 0
    std[np.isnan(std)] = 0.0
    
  res[np.isinf(sigma)] = 0.0
  # remove all outliers 
  absres = np.abs(res)
  idx_row,idx_col = np.nonzero((absres > tol*std) & 
                               (absres == np.max(absres,axis=0)))

  return idx_row,idx_col


def common_mode(u,t,x,sigma=None,
                time_scale=None,time_cuts=None,
                **kwargs):  
  ''' 
  returns common mode time series. Common mode is a weighted mean 
  residual time series between all stations
  
  Parameters
  ----------
    u : (Nt,Nx) array

    t : (Nt,) array
    
    x : (Nx,2) array
    
    sigma : (Nt,Nx) array, optional
    
    time_scale : float, optional
    
    time_cuts : TimeCuts instance, optional
    
    plot : bool, optional

  Returns
  -------
    u_comm : (Nt,1) array

    sigma_comm : (Nt,1) array
  '''
  u = np.asarray(u)
  t = np.asarray(t)
  x = np.asarray(x)
  if sigma is None:
    sigma = np.ones(u.shape)
  else:
    sigma = np.asarray(sigma)

  Nt,Nx = u.shape
    
  ds = pygeons.diff.acc()
  ds['time']['cuts'] = time_cuts
  upred,upert = network_smoother(
                  u,t,x,sigma=sigma,
                  diff_specs=[ds],
                  time_scale=time_scale,
                  perts=0,**kwargs)
  res = u - upred
  u_comm,sigma_comm = weighted_mean(res,sigma,axis=1)    
                          
  u_comm = u_comm[:,None]
  sigma_comm = sigma_comm[:,None]
  return u_comm,sigma_comm
  

def baseline(u,t,x,sigma=None,time_scale=None,
             time_cuts=None,zero_time=None,perts=20,
             **kwargs):
  ''' 
  Returns a baseline displacement vector, u_base.  When subtracting 
  u_base from u, the resulting displacements are zeroed at the same 
  time for each station. The zero time is in the middle of the time 
  series by default.  

  Parameters
  ----------
    u : (Nt,Nx) array
 
    t : (Nt,) array
 
    x : (Nx,2) array

    sigma : (Nt,Nx) array, optional
    
    zero_time : int, optional

    time_cuts : TimeCuts instance, optional

  Returns 
  -------
    u_out : (1,Nx) array

    sigma_out : (1,Nx) array
  '''
  u = np.asarray(u)
  t = np.asarray(t)
  x = np.asarray(x)
  Nt,Nx = u.shape
  if sigma is None:
    sigma = np.ones(u.shape)
  else:
    sigma = np.asarray(sigma)

  if zero_time is None:
    zero_idx = Nt//2
  else:
    zero_idx = np.argmin(np.abs(t - zero_time))  
    
  ds = pygeons.diff.acc()
  ds['time']['cuts'] = time_cuts
  pred,pert = network_smoother(
                u,t,x,sigma=sigma,
                diff_specs=[ds],
                time_scale=time_scale,
                perts=perts,**kwargs)

  pred_sigma = np.std(pert,axis=0)                  
  out = pred[[zero_idx],:]   
  out_sigma = pred_sigma[[zero_idx],:]
  # is the input data was masked then make sure the output data is 
  # also masked. This prevents unwanted extrapolation
  out_sigma[np.isinf(sigma[[zero_idx],:])] = np.inf

  return out,out_sigma


def time_lacks_data(sigma,cutoff=0.5):
  ''' 
  returns true for each time where sigma is np.inf for most of the stations.
  The percentage of infs must exceed cutoff in order to return True.
  '''
  out = most(np.isinf(sigma),axis=1,cutoff=cutoff)
  return out


def station_lacks_data(sigma,cutoff=0.5):
  ''' 
  returns true for each station where sigma is np.inf for most of the times.
  The percentage of infs must exceed cutoff in order to return True.
  '''
  out = most(np.isinf(sigma),axis=0,cutoff=cutoff)
  return out


def station_is_duplicate(sigma,x,tol=4.0):
  ''' 
  returns the indices for a set of nonduplicate stations. if duplicate 
  stations are found then the one that has the most observations is 
  retained
  '''
  x = np.asarray(x)
  # if there is zero or one station then dont run this check

  is_duplicate = np.zeros(x.shape[0],dtype=bool)
  while True:
    xi = x[~is_duplicate]
    sigmai = sigma[:,~is_duplicate]
    idx = _identify_duplicate_station(sigmai,xi,tol=tol) 
    if idx is None:
      break
    else:  
      global_idx = np.nonzero(~is_duplicate)[0][idx]
      logger.info('identified station %s as a duplicate' % global_idx)
      is_duplicate[global_idx] = True

  return is_duplicate      


def _identify_duplicate_station(sigma,x,tol=3.0):
  ''' 
  returns the index of the station which is likely to be a duplicate 
  due to its proximity to another station.  The station which has the 
  least amount of data is identified as the duplicate
  '''
  # if there is zero or one station then dont run this check
  if x.shape[0] <= 1:
    return None
    
  T = cKDTree(x)
  dist,idx = T.query(x,2)
  r = dist[:,1]
  ri = idx[:,1]
  logr = np.log10(r)
  cutoff = np.mean(logr) - tol*np.std(logr)
  if not np.any(logr < cutoff):
    # if no duplicates were found then return nothing
    return None

  else:
    # otherwise return the index of the least useful of the two 
    # nearest stations
    idx1 = np.argmin(logr)    
    idx2 = ri[idx1]
    count1 = np.sum(~np.isinf(sigma[:,idx1]))
    count2 = np.sum(~np.isinf(sigma[:,idx2]))
    count,out = min((count1,idx1),(count2,idx2))
    return out
  

class InteractiveCleaner(InteractiveViewer):
  ''' 
               ---------------------------------
               PyGeoNS Interactive Cleaner (PIC)
               ---------------------------------

Controls
--------
    Enter : edit the configurable parameters through the command line. 
        Variables can be defined using any functions in the numpy, 
        matplotlib, or base python namespace

    Left : move back 1 time step (Ctrl-Left and Alt-Left move back 10 
        and 100 respectively)

    Right : move forward 1 time step (Ctrl-Right and Alt-Right move 
        forward 10 and 100 respectively)

    Up : move forward 1 station (Ctrl-Left and Alt-Left move back 10 
        and 100 respectively)
          
    Down : move back 1 station (Ctrl-Right and Alt-Right move forward 
        10 and 100 respectively)
          
    R : redraw figures

    H : hide station marker

    D : remove data within a time interval for the current station. On 
        the time series figure, press *d* with the cursor over the 
        start of the time interval. With d still pressed down, move 
        the cursor to the end of the time interval.  Release *d* to 
        remove the data

    J : estimate and remove time series jumps for the current station. 
        The jump is estimated by taking a weighted mean of the data 
        over some time interval before and after the jump. On the time 
        series fugure, press *j* with the cursor over the jump time. 
        With j still pressed down, move the cursor to the left or 
        right by desired time interval. Release *j* to remove the 
        jump.
        
    K : keep new changes
    
    U : undo new changes
    
    W : write kept changes to an hdf5 file
    
Notes
-----
    Stations may also be selected by clicking on them 

    Exit PIC by closing the figures

    Key bindings only work when the active window is one of the PIC
    figures   

---------------------------------------------------------------------     
  '''
  def __init__(self,t,x,
               u=None,v=None,z=None,
               su=None,sv=None,sz=None,
               **kwargs):
    if u is not None:
      u = [u,np.copy(u)]                
    if v is not None:
      v = [v,np.copy(v)]                
    if z is not None:
      z = [z,np.copy(z)]                
    if su is not None:
      su = [su,np.copy(su)]                
    if sv is not None:
      sv = [sv,np.copy(sv)]                
    if sz is not None:
      sz = [sz,np.copy(sz)]                
      
    InteractiveViewer.__init__(self,t,x,
                               u=u,v=v,z=z,
                               su=su,sv=sv,sz=sz,
                               **kwargs)

  def connect(self):
    self.ts_fig.canvas.mpl_connect('key_release_event',self._onkey)
    InteractiveViewer.connect(self)
        
  def keep_changes(self):
    print('keeping changes\n')
    self.data_sets[1] = np.copy(self.data_sets[0])
    self.sigma_sets[1] = np.copy(self.sigma_sets[0])
    self.update_data()

  def undo_changes(self):
    print('undoing changes\n')
    self.data_sets[0] = np.copy(self.data_sets[1])
    self.sigma_sets[0] = np.copy(self.sigma_sets[1])
    self.update_data()

  @without_interactivity
  def write_to_file(self):
    self.keep_changes()
    print('writing data to file\n')
    file_name = raw_input('output file name ["exit" to cancel] >>> ')
    print('')
    if file_name == 'exit':
      return
    
    data = self.data_sets[0]
    sigma = self.sigma_sets[0]

    f = h5py.File(file_name,'w')     
    f['time'] = self.t 
    f['position'] = self.x
    f['names'] = self.station_names
    f['easting'] = data[:,:,0]
    f['northing'] = data[:,:,1]
    f['vertical'] = data[:,:,2]
    f['easting_sigma'] = np.nan_to_num(sigma[:,:,0])
    f['northing_sigma'] = np.nan_to_num(sigma[:,:,1])
    f['vertical_sigma'] = np.nan_to_num(sigma[:,:,2])
    f['mask'] = np.any(np.isinf(sigma),axis=2)
    f.close()
    return
  
  def remove_jump(self,jump_time,radius):
    data = self.data_sets[0]
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
    
    # remove jump from values make after the jump 
    new_pos = data[all_tidx_right,xidx,:] - jump
    
    # increase uncertainty 
    new_var = sigma[all_tidx_right,xidx,:]**2 + jump_sigma**2
    new_sigma = np.sqrt(new_var)
    
    self.data_sets[0][all_tidx_right,xidx,:] = new_pos
    self.sigma_sets[0][all_tidx_right,xidx,:] = new_sigma
    
    # turn the new data sets into masked arrays
    self.update_data()
      
  def remove_outliers(self,start_time,end_time):
    # this function masks data for the current station which ranges 
    # from start_time to end_time
    xidx = self.config['xidx']
    tidx, = np.nonzero((self.t >= start_time) & (self.t <= end_time))
    self.data_sets[0][tidx,xidx] = 0.0
    self.sigma_sets[0][tidx,xidx] = np.inf

    # turn the new data sets into masked arrays
    self.update_data()

  def _on_d_press(self,event):
    self._d_pressed_in_ax = False
    if event.inaxes is not None:
      if event.inaxes.figure is self.ts_fig:
        self._d_pressed_in_ax = True
        self._d_start = event.xdata
        print('drag cursor over the time interval containing the outliers\n') 
  
  def _on_d_release(self,event):
    # in order for anything to happen, the key press and release need 
    # to have been in a ts_ax
    if self._d_pressed_in_ax:
      if event.inaxes is not None:
        if event.inaxes.figure is self.ts_fig:
          d_start = self._d_start 
          d_stop = event.xdata
          print('removing data over the time interval %s - %s\n' % (d_start,d_stop))
          self.remove_outliers(d_start,d_stop) 
          self.update()   

  def _on_j_press(self,event):
    self._j_pressed_in_ax = False
    if event.inaxes is not None:
      if event.inaxes.figure is self.ts_fig:
        self._j_pressed_in_ax = True
        self._j_start = event.xdata        
        print('drag cursor over the time radius used to estimate the jump\n') 

  def _on_j_release(self,event):
    if self._j_pressed_in_ax:
      if event.inaxes is not None:
        if event.inaxes.figure is self.ts_fig:
          j_start = self._j_start
          j_stop = event.xdata
          print('removing jump at time %s with time radius %s\n' % (j_start,abs(j_stop-j_start)))
          self.remove_jump(j_start,abs(j_stop-j_start))
          self.update()   
          
  def _onkey(self,event):
    if event.name == 'key_press_event':
      # disable c
      if event.key == 'c':
        return
              
      if event.key == 'k':
        self.keep_changes()
        self.update()   

      elif event.key == 'u':
        self.undo_changes()
        self.update()   

      elif event.key == 'w':
        self.write_to_file()
        self.update()   
        
      elif event.key == 'd':
        self._on_d_press(event)

      elif event.key == 'j':
        self._on_j_press(event)

      else:
        InteractiveViewer._onkey(self,event)
        
    elif event.name == 'key_release_event':   
      if event.key == 'd':
        self._on_d_release(event)

      elif event.key == 'j':
        self._on_j_release(event)
      
  
def interactive_cleaner(*args,**kwargs):
  ''' 
  interactively clean GPS data
  '''
  ic = InteractiveCleaner(*args,**kwargs)
  ic.connect()
  plt.show()
                                      
