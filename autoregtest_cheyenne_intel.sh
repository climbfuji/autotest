#!/bin/bash

set -ex

. /etc/profile.d/modules.sh
. /etc/profile.d/pbs.sh
module load python/3.6.8

cd /glade/u/home/heinzell/autoregtest/ufs-weather-model/log

# DTC: dtc/develop
now=$(date "+%Y%m%dT%H%M%S")
nohup ../autoregtest.py -f dtc -b dtc/develop -s cheyenne -c intel > autoregtest_intel_dtc_develop_${now}.log 2>&1 &
