#!/usr/bin/env python
import numpy as np
import matplotlib.pyplot as plt
import pygeons.smooth
import pygeons.diff
import rbf.halton

def imbricate_list(lst,cuts,buffer=0.0):
  ''' 
  segments lst by cuts 
  '''
  lst = np.asarray(lst)
  cuts = np.asarray(cuts)
  cuts = np.sort(cuts)

  lbs = np.concatenate(([-np.inf],cuts))
  ubs = np.concatenate((cuts,[np.inf]))
  intervals = zip(lbs,ubs)
  out = []
  for lb,ub in intervals:
    idx_in_segment, = np.nonzero((lst >= lb-buffer) & (lst < ub+buffer))
    idx_in_segment = list(idx_in_segment)
    if len(idx_in_segment) > 0:
      out += [idx_in_segment]

  return out

Nb = 5
Nt = 2000
S = 1.0
T = 0.1
P = [(T/2)**2/S]

t = np.linspace(0.0,1.0,Nt)
#t = rbf.halton.halton(Nt,1)[:,0]
#t = np.random.random(Nt)
t_breaks = np.linspace(0.0,1.0,Nb+1)[1:-1]

x = np.array([[0.0,0.0]])
u = (10*np.sin(2*np.pi*t) + np.random.normal(0.0,S,Nt))[:,None] 

solve_indices = imbricate_list(t,t_breaks,buffer=1*T)
store_indices = imbricate_list(t,t_breaks,buffer=0.0)
#print(solve_indices)
#print(store_indices)

fig,ax = plt.subplots()
#ax.plot(t,u,'k.')                                        
u_total = np.zeros((Nt,1))
for solve_idx,store_idx in zip(solve_indices,store_indices):
  us,up = pygeons.smooth.network_smoother(u[solve_idx,:],t[solve_idx],x,penalties=P,
                                          diff_specs=[pygeons.diff.ACCELERATION])
  ax.plot(t[solve_idx],us,'b.')                                        
  #idx = [i for i,k in enumerate(solve_idx) if k in store_idx]
  idx = [solve_idx.index(i) for i in store_idx]
  u_total[store_idx] = us[idx]

us,up = pygeons.smooth.network_smoother(u,t,x,penalties=P,
                                        diff_specs=[pygeons.diff.ACCELERATION])
ax.plot(t,us,'r.')           
ax.plot(t,u_total,'k.')           
plt.show()


