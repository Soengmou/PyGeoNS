#!/usr/bin/env python
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from dislocation.source import rectangular
from myplot.cm import viridis
import rbf.halton
import pygeons.smooth
import logging
logger = logging.basicConfig(level=logging.INFO)
np.random.seed(1)

def correlated_noise(var,decay,times):
  N = len(times)
  mean = np.zeros(N)
  t1,t2 = np.meshgrid(times,times)
  cov = var*np.exp(-np.abs(t1 - t2)/decay)
  noise = np.random.multivariate_normal(mean,cov,1)
  return noise[0]

def animate_it(u,t,x):
  fig,ax = plt.subplots()
  c = ax.scatter(x[:,0],x[:,1],
                s=200,c=0.0*u[0,:],
                cmap=viridis,edgecolor='k',
                vmin=np.min(u),vmax=np.max(u))
  fig.colorbar(c)

  def animate(i):
    ax.clear()
    ax.scatter(x[:,0],x[:,1],s=200,c=u[i,:],
    cmap=viridis,edgecolor='k',
    vmin=np.min(u),vmax=np.max(u))
    ax.text(np.min(x[:,0])-0.4*np.std(x[:,0]),
            np.min(x[:,1])-0.4*np.std(x[:,1]),
            'time: ' + str(np.round(t[i],2)))
    return ()

  def init():
    ax.clear()
    return ()

  ani = animation.FuncAnimation(fig, animate,len(t),init_func=init,
                                interval=100, blit=True)

  return ani

# number of stations
Ns = 50
# number of time steps
Nt = 100

# fault geometry
strike = 0.0
dip = 90.0
top_center = [0.0,0.0,0.0]
width  = 1.0
length = 1.0
slip = [1.0,0.0,0.0]



# create synthetic data
#####################################################################
pnts = 3*(rbf.halton.halton(Ns,2) - 0.51251241124) 
# add z component, which is zero
pnts = np.hstack((pnts,np.zeros((Ns,1))))

# coseismic displacements
cdisp,cderr = rectangular(pnts,slip,top_center,length,width,strike,dip)
# interseismic velocities
idisp,cderr = rectangular(pnts,slip,[0.0,0.0,-1.0],1000.0,1000.0,strike,90.0)

t = np.linspace(0.0,5.0,Nt) 

# interseismic displacement 
disp = 0.1*t[:,None,None]*idisp
# dislocation at t=0.5
disp[t>2.5,:,:] += cdisp

# add noise
#disp += np.random.normal(0.0,0.01,disp.shape)

# add correlated noise to each station
print('adding noise')
for n in range(Ns):
  for j in range(3):
    disp[:,n,j] += correlated_noise(0.05**2,0.5,t)

print('finished')


# smooth displacement
pred,sigma_pred = pygeons.smooth.network_smoother(
                    disp[:,:,1],t,pnts[:,[0,1]],#x_damping=10.0,t_damping=100.0,
                    x_log_bounds=[-4.0,0.0],t_log_bounds=[-4.0,0.0],sigma=0.05*np.ones((Nt,Ns)),
                    cv_itr=100,bs_itr=10,plot=True,fold=10,
                    t_smp=[[0]],t_vert=[[2.5]],x_smp=[[0,1]],x_vert=[[0.0,-0.5],[0.0,0.5]],
                    solver='petsc',ksp='lgmres',pc='icc',maxiter=1000,view=False,atol=1e-3,rtol=1e-8)

#fig,ax = plt.subplots()
#ax.quiver(pnts[:,0],pnts[:,1],cdisp[:,0],cdisp[:,1],color='r',scale=10.0)
#ax.quiver(pnts[:,0],pnts[:,1],idisp[:,0],idisp[:,1],color='k',scale=10.0)
#a1 = animate_it(disp[:,:,0],t,pnts)
a1 = animate_it(disp[:,:,1],t,pnts)
a2 = animate_it(pred,t,pnts)
#a3 = animate_it(disp[:,:,2],t,pnts)
idx = 5
fig,ax = plt.subplots()
ax.plot(t,disp[:,idx,1],'k.')
ax.fill_between(t,pred[:,idx]+sigma_pred[:,idx],pred[:,idx]-sigma_pred[:,idx],color='b',alpha=0.3,edgecolor='none')
ax.plot(t,pred[:,idx],'b-')

plt.show()
print(pnts.shape)





