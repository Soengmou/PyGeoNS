# This script demonstrates using several of the pygeons executables on 
# a small, human-readable csv data file. More information can be found 
# for each of these executables by calling them with a -h flag

mkdir -p work

# convert the csv file to a hdf5 file.
pygeons-toh5 data.csv --file_type csv --output_file work/data.h5 -vv
# view the new hdf5 file
pygeons-view work/data.h5 -vv

# temporally smooth the data set, this effectivly fits a straight line to the data
pygeons-tgpr work/data.h5 0.0 10.0 --output_file work/tsmooth.h5 -vv
pygeons-view work/data.h5 work/tsmooth.h5 -vv

# temporally differentiate the data 
pygeons-tgpr work/data.h5 0.0 10.0 --output_file work/tdiff.h5 --diff 1 -vv
pygeons-view work/tdiff.h5

# spatially smooth the data
pygeons-sgpr work/tdiff.h5 0.0 500.0 --output_file work/xdiff.h5 --output_positions pos.txt -vv --diff 1 0
pygeons-sgpr work/tdiff.h5 0.0 500.0 --output_file work/ydiff.h5 --output_positions pos.txt -vv --diff 0 1 
pygeons-strain work/xdiff.h5 work/ydiff.h5 -vv


