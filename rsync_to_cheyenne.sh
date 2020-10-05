#!/bin/bash

# Do not use --delete, because of the log files are sitting in subdirectory 'logs'
rsync -av ./ heinzell@cheyenne.ucar.edu:/glade/u/home/heinzell/autoregtest/ufs-weather-model/
