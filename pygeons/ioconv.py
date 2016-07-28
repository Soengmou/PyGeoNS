''' 
module for converting between the three input/output data formats
'''
from pygeons.downsample import MeanInterpolant
import numpy as np
from pygeons.dateconv import decday,decday_inv
import logging
import h5py
logger = logging.getLogger(__name__)
  

def _get_line_with(sub,master):
  ''' 
  gets line with the first occurrence of sub
  '''
  idx = master.find(sub)
  if idx == -1:
    raise ValueError('Cannot find substring "%s"' % sub)

  line_start = master.rfind('\n',0,idx)
  if line_start == -1:
    # this is if sub is on the first line
    line_start = 0
  else:
    line_start += 1

  line_end = master.find('\n',line_start)
  if line_end == -1:
    # this is if sub is on the last line
    line_end = len(master)

  return master[line_start:line_end]


def _get_field(field,master,delim=':'):
  ''' 
  finds the first line containing *field*, splits the line by *delim*, 
  then returns the list element which follows the one containing 
  *field*
  '''
  if delim in field:
    raise ValueError('Field "%s" contains the delimiter "%s"' % (field,delim))

  # first line containing field
  line = _get_line_with(field,master)
  # split by delimiter
  lst = [i for i in line.split(delim)]
  # find the index containing field
  for i,j in enumerate(lst): 
    if field in j: 
      field_idx = i
      break

  # entry after the one containing field
  if (field_idx + 1) >= len(lst):
    raise ValueError(
      'No value associated with the field "%s". Make sure the '
      'correct delimiter is being used' % field)    

  out = lst[field_idx + 1]
  # remove white space
  out = out.strip()
  return out


def _parse_csv(file_str):
  ''' 
  returns a data dictionary for one station
  '''
  fmt = '%Y-%m-%d'
  delim = ','

  # date_converter 
  def date_conv(date_str): 
    return decday(date_str,fmt)

  # make everything lowercase so that field searches are not case 
  # sensitive
  file_str = file_str.lower()
  id = _get_field('4-character id',file_str,delim=delim)
  logger.debug('reading csv data for station %s' % id) 

  start = _get_field('begin date',file_str,delim=delim)
  pos = _get_line_with('reference position',file_str)
  lon,lat = pos.split()[5],pos.split()[2]

  data_start_idx = file_str.rfind(start)
  data = file_str[data_start_idx:]
  data = np.genfromtxt(data.split('\n'),
                       converters={0:date_conv},
                       delimiter=delim,
                       usecols=(0,1,2,3,4,5,6))
  output = {}
  output['id'] = id.upper()
  output['longitude'] = np.float(lon)
  output['latitude'] = np.float(lat)
  output['time'] = data[:,0].astype(int)
  output['north'] = data[:,1].astype(float)
  output['east'] = data[:,2].astype(float)
  output['vertical'] = data[:,3].astype(float)
  output['north_std'] = data[:,4].astype(float)
  output['east_std'] = data[:,5].astype(float)
  output['vertical_std'] = data[:,6].astype(float)
  return output 


def _parse_pos(file_str):
  ''' 
  reads data from a pos file. Note that the output displacements are 
  converted to mm.  This is to be consistent with the csv format
  '''
  fmt = '%Y%m%d'

  # date_converter 
  def date_conv(date_str): 
    return decday(date_str,fmt)

  # make everything lowercase so that field searches are not case 
  # sensitive
  file_str = file_str.lower()
  id = _get_field('4-character id',file_str,delim=':')
  logger.debug('reading pos data for station %s' % id) 

  start = _get_field('first epoch',file_str,delim=':')
  pos = _get_field('neu reference position',file_str,delim=':')
  lon,lat = pos.split()[1],pos.split()[0]

  data_start_idx = file_str.rfind(start)
  data = file_str[data_start_idx:]
  data = np.genfromtxt(data.split('\n'),
                       converters={0:date_conv},
                       usecols=(0,15,16,17,18,19,20))
  output = {}
  output['id'] = id.upper()
  output['longitude'] = np.float(lon)
  output['latitude'] = np.float(lat)
  output['time'] = data[:,0].astype(int)
  output['north'] = data[:,1].astype(float)*1000
  output['east'] = data[:,2].astype(float)*1000
  output['vertical'] = data[:,3].astype(float)*1000
  output['north_std'] = data[:,4].astype(float)*1000
  output['east_std'] = data[:,5].astype(float)*1000
  output['vertical_std'] = data[:,6].astype(float)*1000
  return output 
  

def _write_csv(data_dict):
  time = data_dict['time']
  out  = '4-character ID, %s\n' % data_dict['id']
  out += 'Begin Date, %s\n' % decday_inv(time[0],'%Y-%m-%d')
  out += 'End Date, %s\n' % decday_inv(time[-1],'%Y-%m-%d')
  out += 'Reference position, %s North Latitude, %s East Longitude\n' % (data_dict['latitude'],data_dict['longitude'])   
  out += 'Date, North, East, Vertical, North Std. Deviation, East Std. Deviation, Vertical Std. Deviation\n'
  # convert displacements and uncertainties to strings
  for i in range(len(data_dict['time'])):
    date_str = decday_inv(time[i],'%Y-%m-%d')
    out += ('%s, %.5f, %.5f, %.5f, %.5f, %.5f, %.5f\n' % 
            (date_str,data_dict['north'][i],data_dict['east'][i],data_dict['vertical'][i],
             data_dict['north_std'][i],data_dict['east_std'][i],data_dict['vertical_std'][i]))

  return out             
  
  
def _dict_from_text(infile,file_type,perts):
  ''' 
  loads a data dictionary from a text file. 
  '''
  buff = open(infile,'r')
  strs = buff.read().split('***')
  buff.close()

  # dictionaries of data for each station
  if file_type == 'csv':
    dicts = [_parse_csv(s) for s in strs]
  elif file_type == 'pos':
    dicts = [_parse_pos(s) for s in strs]
    
  # find the start and end time
  start_time = np.inf
  stop_time = -np.inf
  for d in dicts:
    if np.min(d['time']) < start_time:
      start_time = np.min(d['time'])
    if np.max(d['time']) > stop_time:
      stop_time = np.max(d['time'])
  
  # interpolation times, make sure that the stop_time is included
  time = np.arange(start_time,stop_time+1,1)
  
  longitude = np.array([d['longitude'] for d in dicts])
  latitude = np.array([d['latitude'] for d in dicts])
  id = np.array([d['id'] for d in dicts])
  Nt,Nx = len(time),len(id)
  east = np.zeros((Nt,Nx))
  north = np.zeros((Nt,Nx))
  vertical = np.zeros((Nt,Nx))
  east_std = np.zeros((Nt,Nx))
  north_std = np.zeros((Nt,Nx))
  vertical_std = np.zeros((Nt,Nx))
  # interpolate data onto the interpolation times for each station
  for i,d in enumerate(dicts):
    logger.debug('interpolating data for station %s onto grid times' % d['id']) 
    data_i = np.concatenate((d['east'][None,:],
                             d['north'][None,:],
                             d['vertical'][None,:]),axis=0)
    sigma_i = np.concatenate((d['east_std'][None,:],
                              d['north_std'][None,:],
                              d['vertical_std'][None,:]),axis=0)
    itp = MeanInterpolant(d['time'][:,None],data_i,sigma_i)    
    data_itp,sigma_itp = itp(time[:,None])
    east[:,i] = data_itp[0,:] 
    north[:,i] = data_itp[1,:] 
    vertical[:,i] = data_itp[2,:] 
    east_std[:,i] = sigma_itp[0,:] 
    north_std[:,i] = sigma_itp[1,:] 
    vertical_std[:,i] = sigma_itp[2,:] 
  
  out = {}
  out['time'] = time
  out['longitude'] = longitude    
  out['latitude'] = latitude    
  out['id'] = id
  out['east'] = east
  out['north'] = north
  out['vertical'] = vertical
  out['east_std'] = east_std
  out['north_std'] = north_std
  out['vertical_std'] = vertical_std
  east_noise = np.random.normal(0.0,east_std[None,:,:].repeat(perts,axis=0))
  out['east_pert'] = east + east_noise
  north_noise = np.random.normal(0.0,north_std[None,:,:].repeat(perts,axis=0))
  out['north_pert'] = north + north_noise
  vertical_noise = np.random.normal(0.0,vertical_std[None,:,:].repeat(perts,axis=0))
  out['vertical_pert'] = vertical + vertical_noise
  return out
  

def dict_from_csv(infile,perts=20):
  ''' 
  loads a data dictionary from a csv file. The data in the csv file 
  needs to be resampled with the same frequency and duration for each 
  station. This resampling could potentially cause data loss. By 
  default the data is resampled daily from the earliest to the latest 
  observation time for the network
  '''
  return _dict_from_text(infile,'csv',perts)


def dict_from_pos(infile,perts=20):
  ''' 
  loads a data dictionary from a pos file. The data in the pos file 
  needs to be resampled with the same frequency and duration for each 
  station. This resampling could potentially cause data loss. By 
  default the data is resampled daily from the earliest to the latest 
  observation time for the network
  '''
  return _dict_from_text(infile,'pos',perts)


def csv_from_dict(outfile,data_dict):
  ''' 
  loads a data dictionary from a csv file
  '''
  Nx = len(data_dict['id'])
  strs = []
  for i in range(Nx):
    # create a subdictionary for each station
    dict_i = {}
    mask = np.isinf(data_dict['north_std'][:,i])
    # do not write data for this station if the station has no data
    if np.all(mask):
      continue

    dict_i['id'] = data_dict['id'][i]
    dict_i['longitude'] = data_dict['longitude'][i]
    dict_i['latitude'] = data_dict['latitude'][i]
    dict_i['time'] = data_dict['time'][~mask]
    dict_i['east'] = data_dict['east'][~mask,i]
    dict_i['north'] = data_dict['north'][~mask,i]
    dict_i['vertical'] = data_dict['vertical'][~mask,i]
    dict_i['east_std'] = data_dict['east_std'][~mask,i]
    dict_i['north_std'] = data_dict['north_std'][~mask,i]
    dict_i['vertical_std'] = data_dict['vertical_std'][~mask,i]
    strs += [_write_csv(dict_i)]
    
  out = '***\n'.join(strs)
  fout = open(outfile,'w')
  fout.write(out)
  fout.close()
  return
  

def dict_from_hdf5(infile):
  ''' 
  loads a data dictionary from an hdf5 file
  '''
  out = {}
  fin = h5py.File(infile,'r')
  for k in fin.keys():
    out[k] = fin[k][...]

  fin.close()
  return out  


def hdf5_from_dict(outfile,data_dict):
  ''' 
  writes an hdf5 file from the data dictionary
  '''
  fout = h5py.File(outfile,'w') 
  for k in data_dict.keys():
    fout[k] = data_dict[k]
    
  fout.close()
  return
  

def file_from_dict(outfile,data_dict):  
  ''' 
  outputs data dictionary to either a csv or hdf5 file. The file type 
  is inferred from the extension
  ''' 
  ext = outfile.split('.')[-1]
  if ext in ['hdf','h5','hdf5','he5']: 
    hdf5_from_dict(outfile,data_dict)

  elif ext in ['csv']:
    csv_from_dict(outfile,data_dict)
      
  else:
    raise ValueError('cannot infer file type with extension *%s*' % ext)

  return


def dict_from_file(infile,perts=20):  
  ''' 
  loads a data dictionary from either a pos, csv, or hdf5 file. The file 
  type is inferred from the extension
  '''
  ext = infile.split('.')[-1]
  if ext in ['hdf','h5','hdf5','he5']: 
    out = dict_from_hdf5(infile)

  elif ext in ['pos']:
    out = dict_from_pos(infile,perts=perts)

  elif ext in ['csv']:
    out = dict_from_csv(infile,perts=perts)
    
  else:
    raise ValueError('cannot infer file type with extension *%s*' % ext)
  
  return out
  
    
                  

