#!/bin/bash

set -ex

ulimit -s 12000000

. /etc/profile.d/modules.sh
. /etc/profile.d/slurm.sh
module load intelpython/3.6.8

cd /home/Dom.Heinzeller/autoregtest/ufs-weather-model/log

# EMC: develop
now=$(date "+%Y%m%dT%H%M%S")
nohup ../autoregtest.py -f emc -b develop -s hera -c intel > autoregtest_intel_emc_develop_${now}.log 2>&1 &
