#!/bin/bash
# coordinates of first endpoint of dislocation
lons1="-120.566"
lats1="36.0"
# coordinates of second endpoint of dislocation
lons2="-120.357"
lats2="35.8349"

#pygeons-downsample data.csv 1 \
#  --start_date 2004-07-01 --stop_date 2005-07-01 \
#  --cut_dates 2004-09-29 -vv

pygeons-zero data.downsample.h5 2004-09-01 7

pygeons-smooth data.downsample.zero.h5 --time_scale 0.2 --length_scale 10000 \
  --cut_dates 2004-09-29 \
  --cut_endpoint1_lons $lons1 \
  --cut_endpoint1_lats $lats1 \
  --cut_endpoint2_lons $lons2 \
  --cut_endpoint2_lats $lats2 -vv

#pygeons-view data.downsample.tsmooth.h5 -vv

pygeons-diff data.downsample.zero.smooth.h5 --dt 1 \
  --cut_dates 2004-09-29 -vv

pygeons-view data.downsample.tsmooth.diff.h5 data.downsample.zero.smooth.diff.h5 -vv

#pygeons-zero data.csv 2005-01-01 10 -vv


#pygeons-downsample data.zero.h5 7 \
#  --start_date 2004-07-01 --stop_date 2005-07-01 \
#  --cut_dates 2004-09-29 -vv

#pygeons-view data.zero.downsample.h5 -vv

#pygeons-smooth data.zero.downsample.h5 --time_scale 0.2 --length_scale 10000.0 \
#  --cut_dates 2004-09-29 \
#  --cut_endpoint1_lons $lons1 \
#  --cut_endpoint1_lats $lats1 \
#  --cut_endpoint2_lons $lons2 \
#  --cut_endpoint2_lats $lats2 -vv

#pygeons-view data.zero.downsample.h5 data.zero.downsample.smooth.h5 \
#  --cut_endpoint1_lons $lons1 \
#  --cut_endpoint1_lats $lats1 \
#  --cut_endpoint2_lons $lons2 \
#  --cut_endpoint2_lats $lats2 -vv
