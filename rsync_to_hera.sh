#!/bin/bash

# Do not use --delete, because of the log files are sitting in subdirectory 'logs'
rsync -av -e 'ssh -l Dom.Heinzeller -p 65252' ./ Dom.Heinzeller@localhost:/home/Dom.Heinzeller/autoregtest/ufs-weather-model/
