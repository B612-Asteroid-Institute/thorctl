# thorctl #

A tool for managing [THOR](https://github.com/moeyensj/thor) execution across a
parallel backend.

## Installation ##

### Using conda

Make a conda environment, and activate it:
```
conda create -n thorctl_py38 -c defaults -c conda-forge python=3.8
conda activate thorctl_py38
```

Install openorb:
```
conda install -c conda-forge -c moeyensj openorb
```

Install thorctl:

```
pip install -e .
```
