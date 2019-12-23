#!/bin/bash

set -ex

. /etc/profile.d/modules.sh
. /etc/profile.d/pbs.sh
module load python/3.6.8

cd /glade/u/home/heinzell/autoregtest/ufs-weather-model/log

# EMC: ufs_public_release
now=$(date "+%Y%m%dT%H%M%S")
nohup ../autoregtest.py -f emc -b ufs_public_release -r rt.conf -s cheyenne -c gnu > autoregtest_gnu_ufs_public_release_${now}.log 2>&1 &
