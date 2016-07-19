#!/usr/bin/env python
import pygeons.ioconv
import numpy as np
import unittest
import datetime

class Test(unittest.TestCase):
  def test_csv_conversion(self):
    # make sure there is no loss of data when reading and writing csv files
    pygeons.ioconv.convert_file('data/CAND.pbo.nam08.csv','data/CAND.test.nam08.csv')        
    # make sure the two files have the same data
    data1 = pygeons.ioconv.dict_from_file('data/CAND.pbo.nam08.csv')
    data2 = pygeons.ioconv.dict_from_file('data/CAND.test.nam08.csv')
    for k in data1.keys():
      if k == 'id':
        self.assertTrue(np.all(data1[k]==data2[k]))
      else:
        self.assertTrue(np.all(np.isclose(data1[k],data2[k])))

    # do it again!
    pygeons.ioconv.convert_file('data/CAND.test.nam08.csv','data/CAND.test2.nam08.csv')        
    # make sure the two files have the same data
    data1 = pygeons.ioconv.dict_from_file('data/CAND.test.nam08.csv')
    data2 = pygeons.ioconv.dict_from_file('data/CAND.test2.nam08.csv')
    for k in data1.keys():
      if k == 'id':
        self.assertTrue(np.all(data1[k]==data2[k]))
      else:
        self.assertTrue(np.all(np.isclose(data1[k],data2[k])))
    
  def test_h5py_conversion(self):
    pygeons.ioconv.convert_file('data/CAND.pbo.nam08.csv','data/CAND.test.nam08.h5')        
    data1 = pygeons.ioconv.dict_from_file('data/CAND.pbo.nam08.csv')
    data2 = pygeons.ioconv.dict_from_file('data/CAND.test.nam08.h5')
    # the only difference should be that data2 is o
    for k in data1.keys():
      if k == 'id':
        self.assertTrue(np.all(data1[k]==data2[k]))
      else:
        self.assertTrue(np.all(np.isclose(data1[k],data2[k])))
    
    # try going the other way!
    pygeons.ioconv.convert_file('data/CAND.test.nam08.h5','data/CAND.test.nam08.csv')        
    data1 = pygeons.ioconv.dict_from_file('data/CAND.test.nam08.csv')
    data2 = pygeons.ioconv.dict_from_file('data/CAND.test.nam08.h5')
    # the only difference should be that data2 is o
    for k in data1.keys():
      if k == 'id':
        self.assertTrue(np.all(data1[k]==data2[k]))
      else:
        self.assertTrue(np.all(np.isclose(data1[k],data2[k])))
  
unittest.main()