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

Then, install `thorctl`'s dependencies with pip. Make sure you have an up-to-date version of pip for this to work:
```
pip install pip --upgrade
pip install -r requirements.txt -r dev-requirements.txt
```

You now have all the developer requirements installed. You can now install the
pre-commit hooks for automating checks:

```
pre-commit install
```

Install the thorctl commands:

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

#### Adding a new runtime dependency ####

Add the dependency to `requirements.in`, and then run `pip-compile
requirements.in > requirements.txt`. Commit the result.

#### Adding a new developer dependency ####

Add the dependency to `dev-requirements.in`, and then run `pip-compile
dev-requirements.in > dev-requirements.txt`. Commit the result.

#### Updating version of THOR that is used ####

THOR is installed using `requirements.in`, but using the special syntax to
build it directly from a git repository. Update the git reference in that file
to update it.

You can also override this by installing a local copy of THOR, but beware -
your changes will not appear in deployed or released thorctl code.

### Running lint and tests

If you ran `pre-commit install`, which is part of the instructions, you should
automatically run linters, code formatters, and tests on every commit. You can
run them manually like this:

```
pre-commit run --all-files
```
