#!/usr/bin/env python
import matplotlib.pyplot as plt
import numpy as np
import rbf.halton
import matplotlib
from rbf.interpolant import RBFInterpolant
from matplotlib.cm import ScalarMappable
import pygeons.quiver
import rbf.basis
import modest

# change behavior of mpl.quiver. this is necessary for error 
# ellipses but may lead to insidious bugs
matplotlib.quiver.Quiver = pygeons.quiver.Quiver

def _roll(lst):
  # rolls elements by 1 to the right. does not convert lst to an array
  out = [lst[-1]] + lst[:-1]
  return out
  
def _merge_masks(data_set,sigma_set):
  ''' 
  returns a masked array for data_set and sigma_set where the masks for 
  u,v,z,su,sv, and sz are all the same. If one of the input components is masked
  then all components get masked 
  '''
  if not np.ma.isMA(data_set):
    data_set = np.ma.masked_array(data_set)
  if not np.ma.isMA(sigma_set):
    sigma_set = np.ma.masked_array(sigma_set)
    
  # make sure mask is the same size as the array
  if len(data_set.mask.shape) == 0:
    data_set.mask = data_set.mask*np.ones(data_set.shape,dtype=bool)

  if len(sigma_set.mask.shape) == 0:
    sigma_set.mask = sigma_set.mask*np.ones(sigma_set.shape,dtype=bool)
    
  mask = np.any(data_set.mask,axis=-1) | np.any(sigma_set.mask,axis=-1) 
  mask = mask[:,None].repeat(3)
  data_set.mask = mask
  sigma_set.mask = mask
  return data_set,sigma_set

@modest.funtime
def _grid_interp_data(u,pnts,x,y):
  if np.ma.isMaskedArray(u):
    pnts = pnts[~u.mask]
    u = u[~u.mask] 

  u = np.asarray(u)
  pnts = np.asarray(pnts)
  x = np.asarray(x)  
  y = np.asarray(y)
  
  xg,yg = np.meshgrid(x,y)
  xf,yf = xg.flatten(),yg.flatten()
  pnts_itp = np.array([xf,yf]).T
  I = RBFInterpolant(pnts,u,penalty=0.0,
                     order=1,basis=rbf.basis.phs1)
  uitp = I(pnts_itp)
  uitp = uitp.reshape((x.shape[0],y.shape[0]))                   
  return uitp
  

class InteractiveView:
  def __init__(self,data_sets,t,x,
               sigma_sets=None,
               cmap=None,
               quiver_key_label=None,
               quiver_key_length=1.0,
               quiver_scale=10.0,
               quiver_key_pos=None,
               station_names=None,
               data_set_names=None,
               vmin=None,
               vmax=None,
               time_series_axs=None,
               map_ax=None,
               ylabel='displacement [m]',
               xlabel='time [years]',
               clabel='vertical displacement [m]'):
    ''' 

    interactively views vector valued data which is time and space 
    dependent
    
    Parameters
    ----------
      data : (Nt,Nx,3) array (can me masked)

      t : (Nt,) array

      x : (Nx,2) array
      
    '''
    if time_series_axs is None:
      fig1,ax1 = plt.subplots(3,1,sharex=True)
      self.fig1 = fig1
      self.ax1 = ax1
    else:
      self.fig1 = time_series_axs[0].get_figure()
      self.ax1 = time_series_axs
      
    if map_ax is None:
      fig2,ax2 = plt.subplots()
      self.fig2 = fig2
      self.ax2 = ax2
    else:
      self.fig2 = map_ax.get_figure()  
      self.ax2 = map_ax
      
    self.highlight = True
    self.tidx,self.xidx = 0,0
    if sigma_sets is None:
      sigma_sets = [np.ones(d.shape) for d in data_sets]

    self.data_sets = []
    self.sigma_sets = []
    for d,s in zip(data_sets,sigma_sets):      
      dout,sout = _merge_masks(d,s)
      self.data_sets += [dout]
      self.sigma_sets += [sout]

    self.t = t
    self.x = x
    self.cmap = cmap
    self.vmin = vmin
    self.vmax = vmax
    self.quiver_scale = quiver_scale
    self.xlabel = xlabel # xlabel for time series plot
    self.ylabel = ylabel # ylabel for time series plots
    self.clabel = clabel
    self.color_cycle = ['k','b','r','g','c','m','y']
    if station_names is None:
      station_names = np.arange(len(self.x)).astype(str)
    if data_set_names is None:
      data_set_names = np.arange(len(self.data_sets)).astype(str)

    self.station_names = list(station_names)
    self.data_set_names = list(data_set_names)
    
    if quiver_key_pos is None:
      quiver_key_pos = (0.1,0.1)

    if quiver_key_label is None:   
      quiver_key_label = str(quiver_key_length) + ' [m]'

    self.quiver_key_pos = quiver_key_pos
    self.quiver_key_label = quiver_key_label
    self.quiver_key_length = quiver_key_length

    self._init_draw()

  def connect(self):
    self.fig1.canvas.mpl_connect('key_press_event',self._onkey)
    self.fig2.canvas.mpl_connect('key_press_event',self._onkey)
    self.fig2.canvas.mpl_connect('pick_event',self._onpick)


  def _init_draw(self):
    ''' 
      creates the following artists
        D : marker for current station
        P : station pickers
        L1-L3 : list of time series for each data_set
        F1-F3 : list of fill between series for each data_set
        Q : list of quiver instances for each data_set
        K : quiver key for first element in Q
        I : interpolated image of z component for first data_set
        S : scatter plot where color is z component for second data_set

    '''
    self.ax1[0].set_title('station %s' % self.station_names[self.xidx])
    self.ax1[2].set_xlabel(self.xlabel)
    self.ax1[0].set_ylabel(self.ylabel)
    self.ax1[1].set_ylabel(self.ylabel)
    self.ax1[2].set_ylabel(self.ylabel)
    # dont convert to exponential form
    self.ax1[0].get_xaxis().get_major_formatter().set_useOffset(False)
    self.ax1[1].get_xaxis().get_major_formatter().set_useOffset(False)
    self.ax1[2].get_xaxis().get_major_formatter().set_useOffset(False)
    self.ax2.set_title('time %g' % self.t[self.tidx])
    self.ax2.set_aspect('equal')

    # highlighted point
    self.D = self.ax2.plot(self.x[self.xidx,0],
                           self.x[self.xidx,1],'ko',
                           markersize=20*self.highlight)[0]
    # pickable artists
    self.P = []
    for xi in self.x:
      self.P += self.ax2.plot(xi[0],xi[1],'.',
                              picker=10,
                              markersize=0)
    self.Q = []
    self.L1,self.L2,self.L3 = [],[],[]
    self.F1,self.F2,self.F3 = [],[],[]
    for si in range(len(self.data_sets)):
      self.Q += [self.ax2.quiver(self.x[:,0],self.x[:,1],
                        self.data_sets[si][self.tidx,:,0],
                        self.data_sets[si][self.tidx,:,1],
                        scale=self.quiver_scale,  
                        sigma=(self.sigma_sets[si][self.tidx,:,0],
                               self.sigma_sets[si][self.tidx,:,1],
                               0.0*self.sigma_sets[si][self.tidx,:,0]),
                        color=self.color_cycle[si],
                        ellipse_edgecolors=self.color_cycle[si],
                        zorder=2)]

      # time series instances
      self.L1 += self.ax1[0].plot(self.t,
                                  self.data_sets[si][:,self.xidx,0],
                                  color=self.color_cycle[si])
      self.F1 += [self.ax1[0].fill_between(self.t,
                                  self.data_sets[si][:,self.xidx,0] -
                                  self.sigma_sets[si][:,self.xidx,0],
                                  self.data_sets[si][:,self.xidx,0] +
                                  self.sigma_sets[si][:,self.xidx,0],
                                  color=self.color_cycle[si],alpha=0.5)]

      self.L2 += self.ax1[1].plot(self.t,
                                  self.data_sets[si][:,self.xidx,1],
                                  color=self.color_cycle[si])
      self.F2 += [self.ax1[1].fill_between(self.t,
                                  self.data_sets[si][:,self.xidx,1] -
                                  self.sigma_sets[si][:,self.xidx,1],
                                  self.data_sets[si][:,self.xidx,1] +
                                  self.sigma_sets[si][:,self.xidx,1],
                                  color=self.color_cycle[si],alpha=0.5)]

      self.L3 += self.ax1[2].plot(self.t,
                                  self.data_sets[si][:,self.xidx,2],
                                  color=self.color_cycle[si])
      self.F3 += [self.ax1[2].fill_between(self.t,
                                  self.data_sets[si][:,self.xidx,2] -
                                  self.sigma_sets[si][:,self.xidx,2],
                                  self.data_sets[si][:,self.xidx,2] +
                                  self.sigma_sets[si][:,self.xidx,2],
                                  color=self.color_cycle[si],alpha=0.5)]

      # quiver key
      if si == 0:
        self.K = self.ax2.quiverkey(self.Q[si],
                                    self.quiver_key_pos[0],
                                    self.quiver_key_pos[1],
                                    self.quiver_key_length,
                                    self.quiver_key_label,zorder=2)

      if si == 0:
        # interpolate z value for first data set
        xlim = self.ax2.get_xlim()
        ylim = self.ax2.get_ylim()
        
        self.x_itp = [np.linspace(xlim[0],xlim[1],100),
                      np.linspace(ylim[0],ylim[1],100)]
        data_itp = _grid_interp_data(self.data_sets[si][self.tidx,:,2],
                                    self.x,
                                    self.x_itp[0],self.x_itp[1])
        
        if self.vmin is None:
          # self.vmin and self.vmax are the user specified color 
          # bounds. if they are None then the color bounds will be 
          # updated each time the artists are redrawn
          vmin = data_itp.min()
        else:  
          vmin = self.vmin

        if self.vmax is None:
          vmax = data_itp.max()
        else:
          vmax = self.vmax
          
        self.I = self.ax2.imshow(data_itp,extent=(xlim+ylim),
                                 interpolation='none',
                                 origin='lower',
                                 vmin=vmin,
                                 vmax=vmax,
                                 cmap=self.cmap,zorder=0)
        self.I.set_clim((vmin,vmax))

        self.cbar = self.fig2.colorbar(self.I)  
        self.cbar.set_clim((vmin,vmax))
        self.cbar.set_label(self.clabel)
        self.ax2.set_xlim(xlim)
        self.ax2.set_ylim(ylim)

      if si == 1:  
        ylim = self.ax2.get_ylim()  
        xlim = self.ax2.get_xlim()  
        sm = ScalarMappable(norm=self.cbar.norm,cmap=self.cmap)
        # use scatter points to show z for second data set 
        colors = sm.to_rgba(self.data_sets[si][self.tidx,:,2])
        self.S = self.ax2.scatter(self.x[:,0],self.x[:,1],
                                  c=colors,
                                  s=200,zorder=1,
                                  edgecolor=self.color_cycle[si])
        self.ax2.set_ylim(ylim)
        self.ax2.set_xlim(xlim)
      
    self.ax1[0].legend(self.data_set_names,frameon=False)
    self.fig1.tight_layout()
    self.fig2.tight_layout()
    self.fig1.canvas.draw()
    self.fig2.canvas.draw()


  def _draw(self):
    # make sure the ylim and xlim are not changed after this call
    ylim = self.ax2.get_ylim()  
    xlim = self.ax2.get_xlim()  
    
    self.tidx = self.tidx%self.data_sets[0].shape[0]
    self.xidx = self.xidx%self.data_sets[0].shape[1]

    self.ax1[0].set_title('station %s' % self.station_names[self.xidx])
    self.ax2.set_title('time %g' % self.t[self.tidx])

    self.D.set_data(self.x[self.xidx,0],
                    self.x[self.xidx,1])
    self.D.set_markersize(20*self.highlight)

    # unfortunately there is no option to update the fill between instances
    # and so they must be deleted and redrawn
    [self.ax1[0].collections.remove(f) for f in self.F1]
    [self.ax1[1].collections.remove(f) for f in self.F2]
    [self.ax1[2].collections.remove(f) for f in self.F3]
    self.F1,self.F2,self.F3 = [],[],[]
      
    for si in range(len(self.data_sets)):
      self.Q[si].set_UVC(self.data_sets[si][self.tidx,:,0],
                         self.data_sets[si][self.tidx,:,1],
                         sigma=(self.sigma_sets[si][self.tidx,:,0],
                                self.sigma_sets[si][self.tidx,:,1],
                                0.0*self.sigma_sets[si][self.tidx,:,0]))

      self.L1[si].set_data(self.t,
                           self.data_sets[si][:,self.xidx,0])
      self.F1 += [self.ax1[0].fill_between(self.t,
                                  self.data_sets[si][:,self.xidx,0] -
                                  self.sigma_sets[si][:,self.xidx,0],
                                  self.data_sets[si][:,self.xidx,0] +
                                  self.sigma_sets[si][:,self.xidx,0],
                                  color=self.color_cycle[si],alpha=0.5)]

      self.L2[si].set_data(self.t,
                           self.data_sets[si][:,self.xidx,1])
      self.F2 += [self.ax1[1].fill_between(self.t,
                                  self.data_sets[si][:,self.xidx,1] -
                                  self.sigma_sets[si][:,self.xidx,1],
                                  self.data_sets[si][:,self.xidx,1] +
                                  self.sigma_sets[si][:,self.xidx,1],
                                  color=self.color_cycle[si],alpha=0.5)]

      self.L3[si].set_data(self.t,
                           self.data_sets[si][:,self.xidx,2])
      self.F3 += [self.ax1[2].fill_between(self.t,
                                  self.data_sets[si][:,self.xidx,2] -
                                  self.sigma_sets[si][:,self.xidx,2],
                                  self.data_sets[si][:,self.xidx,2] +
                                  self.sigma_sets[si][:,self.xidx,2],
                                  color=self.color_cycle[si],alpha=0.5)]

      if si == 0:
        data_itp = _grid_interp_data(self.data_sets[si][self.tidx,:,2],
                                    self.x,
                                    self.x_itp[0],self.x_itp[1])
        self.I.set_data(data_itp)

        if self.vmin is None:
          # self.vmin and self.vmax are the user specified color 
          # bounds. if they are None then the color bounds will be 
          # updated each time the artists are redrawn
          vmin = data_itp.min()
        else:  
          vmin = self.vmin

        if self.vmax is None:
          vmax = data_itp.max()
        else:
          vmax = self.vmax

        self.I.set_clim((vmin,vmax))
        self.cbar.set_clim((vmin,vmax))

      if si == 1:
        # set new colors for scatter plot. use the same colormap as 
        # the one used for data set 1
        sm = ScalarMappable(norm=self.cbar.norm,cmap=self.cmap)
        colors = sm.to_rgba(self.data_sets[si][self.tidx,:,2])
        self.S.set_facecolors(colors)
        

    self.ax1[0].legend(self.data_set_names,frameon=False)
    self.ax2.set_ylim(ylim)
    self.ax2.set_xlim(xlim)
    self.ax1[0].relim()
    self.ax1[1].relim()
    self.ax1[2].relim()
    self.ax1[0].autoscale_view()
    self.ax1[1].autoscale_view()
    self.ax1[2].autoscale_view()

    self.fig1.canvas.draw()
    self.fig2.canvas.draw()


  def _onpick(self,event):
    for i,v in enumerate(self.P):
      if event.artist == v:
        self.xidx = i
        break

    self._draw()    


  def _onkey(self,event):
    if event.key == 'right':
      self.tidx += 1

    elif event.key == 'ctrl+right':
      self.tidx += 10

    elif event.key == 'alt+right':
      self.tidx += 100

    elif event.key == 'left':
      self.tidx -= 1

    elif event.key == 'ctrl+left':
      self.tidx -= 10

    elif event.key == 'alt+left':
      self.tidx -= 100

    elif event.key == 'up':
      self.xidx += 1

    elif event.key == 'ctrl+up':
      self.xidx += 10

    elif event.key == 'alt+up':
      self.xidx += 100

    elif event.key == 'down':
      self.xidx -= 1

    elif event.key == 'ctrl+down':
      self.xidx -= 10

    elif event.key == 'alt+down':
      self.xidx -= 100

    elif event.key == 'c':
      self.highlight = not self.highlight

    elif event.key == 'r':
      # roll order of data arrays 
      self.data_sets = _roll(self.data_sets)
      self.data_set_names = _roll(self.data_set_names)
      self.sigma_sets = _roll(self.sigma_sets)

    else:
      # do nothing
      return

    self._draw()    
    
def network_viewer(t,x,u=None,v=None,z=None,
                   su=None,sv=None,sz=None,
                   **kwargs):
  ''' 
  Parameters
  ----------
    t : (Nt,) array
    x : (Nx,2) array
    
    u,v,z : (Nt,Nx) array
    
    su,sv,sz : (Nt,Nx) array
      uncertainties in u,v, and z. data with uncertainties of np.inf will be 
      treated as masked data
    
    **kwargs : arguments passed to InteractiveViewer  
  '''
  x = np.asarray(x)
  t = np.asarray(t)
  Nx = x.shape[0]
  Nt = t.shape[0]
  # find the number of data sets
  if u is not None:
    Ns = len(u)
  elif v is not None:
    Ns = len(v)
  elif z is not None:
    Ns = len(z)
  else:
    raise ValueError('one of u,v, or z must be specified')  
      
  if u is None:
    u = Ns*[np.zeros((Nt,Nx))]
  if v is None:
    v = Ns*[np.zeros((Nt,Nx))]
  if z is None:
    z = Ns*[np.zeros((Nt,Nx))]
  if su is None:
    su = Ns*[np.zeros((Nt,Nx))]
  if sv is None:
    sv = Ns*[np.zeros((Nt,Nx))]
  if sz is None:
    sz = Ns*[np.zeros((Nt,Nx))]
    
  su = [np.ma.masked_array(i,mask=np.isinf(i)) for i in su]
  sv = [np.ma.masked_array(i,mask=np.isinf(i)) for i in sv]
  sz = [np.ma.masked_array(i,mask=np.isinf(i)) for i in sz]
  
  data_sets = []
  sigma_sets = []
  for i in range(Ns):
    data_sets += [np.concatenate((u[i][:,:,None],v[i][:,:,None],z[i][:,:,None]),axis=2)]
    sigma_sets += [np.concatenate((su[i][:,:,None],sv[i][:,:,None],sz[i][:,:,None]),axis=2)]
  
  iv = InteractiveView(data_sets,t,x,sigma_sets=sigma_sets,**kwargs)
  iv.connect()
  plt.show()
    

if __name__ == '__main__':
  Nt = 10
  Nx = 50
  t = 2010 + np.linspace(0.0,1.0,Nt)
  x = rbf.halton.halton(Nx,2)
  data = (np.cos(2*np.pi*t[:,None,None]) *
          np.sin(2*np.pi*x[:,0])[None,:,None] *
          np.cos(2*np.pi*x[:,1])[None,:,None])
  data = data.repeat(3,axis=2)
  data[:,:,[0,1]] = 0.0

  network_viewer(t,x,z=[data[:,:,2],data[:,:,0]],vmin=-1,vmax=1)
  quit()
