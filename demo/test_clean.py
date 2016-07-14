#!/usr/bin/env python
import numpy as np
import pygeons.clean
import matplotlib.pyplot as plt
import logging
import pygeons.diff
import pygeons.cuts
logging.basicConfig(level=logging.INFO)

Nt = 1000
Nx = 1
S = 0.1
t = np.linspace(0.0,5.0,Nt)
x = np.random.random((Nx,2))
u = 1*np.sin(2*t)[:,None]
u = u.repeat(Nx,axis=1)
u += np.random.normal(0.0,S,(Nt,Nx))
sigma = S*np.ones((Nt,Nx))

tc = pygeons.cuts.TimeCuts([1.6])
ds = pygeons.diff.acc()
ds['time']['cuts'] = tc
sigma[t > 1.5] = np.inf
us,perts = pygeons.smooth.network_smoother(u,t,x,sigma=sigma,time_scale=0.01,diff_specs=[ds])

plt.plot(t,u[:,0],'ko')
plt.plot(t,us[:,0],'b-')
plt.show()

