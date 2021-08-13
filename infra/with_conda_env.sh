#!/bin/bash

# Just a little script that executes a command inside the thor_py38 conda
# environment.
#
# This is used by Dockerfiles to make sure any code executes with conda set up
# properly.

source /opt/miniconda3/bin/activate thor_py38

exec $@
