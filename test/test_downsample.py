#!/usr/bin/env python
import numpy as np
import matplotlib.pyplot as plt
from gps.station import MeanInterpolant
from pygeons.smooth import network_smoother
from pygeons.diff import ACCELERATION

N = 10000
dt = 0.1/10
T = 0.1
S = 1.0
P = [(T/2.0)**2/S]

t = np.linspace(0.0,1.0,N)
x = np.array([[0.0,0.0]])
u = np.random.normal(0.0,S,N)
I = MeanInterpolant(t[:,None],u)

tds = np.arange(0.0,1.0,dt)
print(len(tds))
uds = I(tds[:,None],dt/2.0)

us,perts = network_smoother(u[:,None],t,x,diff_specs=[ACCELERATION],penalties=P)

udss,perts = network_smoother(uds[:,None],tds,x,diff_specs=[ACCELERATION],penalties=P)

fig,ax = plt.subplots()
#ax.plot(t,u,'k.')
ax.plot(t,us,'k-')
#ax.plot(tds,uds,'b.')
ax.plot(tds,udss,'b-')
plt.show()