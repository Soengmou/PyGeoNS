#!/usr/bin/env python
import matplotlib.pyplot as plt
import numpy as np
import rbf.halton
import rbf.basis
import modest
import gps.plot
from pygeons.view import network_viewer

t = np.linspace(0,1,100) # form observation times
x = np.random.normal(0.0,1.0,(20,2)) # form observation positions
x[:,0] += -84.0
x[:,1] += 43.0

fig,ax = plt.subplots()
bm = gps.plot.create_default_basemap(x[:,1],x[:,0])
bm.drawstates(ax=ax)
bm.drawcountries(ax=ax)
bm.drawcoastlines(ax=ax)
bm.drawparallels(np.arange(30,90),ax=ax)
bm.drawmeridians(np.arange(-100,-60),ax=ax)
#help(bm.drawmeridians)
pos_x,pos_y = bm(x[:,0],x[:,1])
pos = np.array([pos_x,pos_y]).T
u1,v1,z1 = np.cumsum(np.random.normal(0.0,0.1,(3,100,20)),axis=1)                   
u2,v2,z2 = np.cumsum(np.random.normal(0.0,0.1,(3,100,20)),axis=1)                   

print(u1.shape)
print(v1.shape)
print(z1.shape)
print(t.shape)
print(pos.shape)

network_viewer(t,x,u=[u1],v=[v1],z=[z1]) 
#network_viewer(t,pos,u=[u1,u2],v=[v1,v2],z=[z1,z2],map_ax=ax,quiver_scale=0.00001) 
