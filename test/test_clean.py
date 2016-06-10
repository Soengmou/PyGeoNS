#!/usr/bin/env python
import numpy as np
import pygeons.clean
import matplotlib.pyplot as plt
import logging
logging.basicConfig(level=logging.INFO)
Nt = 1000
Nx = 1
t = np.linspace(0.0,5.0,Nt)
x = np.zeros((Nx,2))
x = np.random.random((Nx,2))
u = np.sin(t)[:,None]
u = u.repeat(Nx,axis=1)
u += np.random.normal(0.0,0.1,(Nt,Nx))
sigma =np.ones((Nt,Nx))

ridx,cidx = pygeons.clean.outliers(u,t,x,tol=3.0,penalty=0.1,plot=True)
fig,ax = plt.subplots()
ax.plot(t,u,'ro')
plt.show()
u[ridx,cidx] = np.nan
sigma[ridx,cidx] = np.nan
ax.plot(t,u,'bo')
plt.show()
quit()


