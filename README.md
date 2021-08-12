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

Install THOR - you can either do a released version, via conda:
```
conda install -c conda-forge -c moeyensj thor
```

... or an unreleased version, via pip + git:
```
VERSION=v1.2  # or any git ref, like "main" or "7278ae1" or "some-other-branch"
pip install "thor @ git+ssh://git@github.com/moeyensj/thor@$VERSION#egg=thor"
```

... or a local version, via pip + path:
```
pip install --editable path/to/thor/repo
```
Install thorctl:

```
pip install -e .
```


## Developer Guide ##

### One-time developer environment setup ###

The developer environment is managed by Conda. First, create a conda
environment, and activate it:

```
conda create --name thorctl_py38 --channel defaults --channel conda-forge python=3.8
conda activate thorctl_py38
```

Next, use `conda` to install `openorb`:
```
conda install openorb
```

Then, install `thorctl`'s dependencies with pip:
```
pip install -r requirements.txt -r dev-requirements.txt
```

Install the [THOR](https://github.com/moeyensj/thor/) submodule and its
dependencies:

```
pip install --editable ./thor
```

Almost done! Now you can install the thorctl commands:

```
pip install --editable .
```

To verify that everything worked, try running the `thorctl` command:

```
-> % thorctl --help
usage: thorctl [-h] {scale-up,size,destroy,logs,autoscale} ...

positional arguments:
  {scale-up,size,destroy,logs,autoscale}
    scale-up            add more workers
    size                look up the current number of workers
    destroy             destroy all workers on a queue, even if they are doing work
    logs                stream logs from the workers
    autoscale           monitor a queue and automatically scale it up to handle load

optional arguments:
  -h, --help            show this help message and exit
(thorctl_py38_clean)
```

(note that this can take a while to run the first time because of aggressive
Numba compilation in THOR)

### Activating your developer environment ###

To return to working on thorctl, activate the conda environment:

```
conda activate thorctl_py38
```

You should be good to go.

### Updating dependencies

This project uses [pip-tools](https://github.com/jazzband/pip-tools) to manage
dependencies.

Dependencies are separated into two categories:
 - *runtime* dependencies are ones used by the thorctl code, like Google API
   clients.
 - *developer* dependencies are ones used when working on thorctl, like
   linters and test runners.

In addition, the `thor` dependency is treated specially and separately.

#### Adding a new runtime dependency ####

Add the dependency to `requirements.in`, and then run `pip-compile
requirements.in > requirements.txt`. Commit the result.

#### Adding a new developer dependency ####

Add the dependency to `dev-requirements.in`, and then run `pip-compile
dev-requirements.in > dev-requirements.txt`. Commit the result.

#### Updating verison of THOR that is used ####

THOR is installed as a git submodule. This means that it's another git repo
embedded within thorctl. You can treat it like a normal git repository: go in,
make changes, commit them, and push them.

You can make local changes inside the ./thor directory and they'll work in your
developer environment. If you enter the directory and commit the changes,
they'll be pushed up to the [main THOR repo](https://github.com/moeyensj/thor).

If you want to pull down recent changes, use `git pull` inside the `thor`
directory, or checkout a specific commit or branch or tag.

From time to time, you might need to run `pip install --editable ./thor` again
to freshen things up, like installing new or updated dependencies, or new
packages from thor.
