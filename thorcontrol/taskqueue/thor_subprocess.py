# Module for running THOR in a subprocess.
import logging
import os.path
import subprocess
import sys
from typing import List

logger = logging.getLogger("thor")


def run_thor_subprocess(input_dir: str, output_dir: str):
    cfg_path = os.path.join(input_dir, "config.yml")
    obs_path = os.path.join(input_dir, "observations.csv")
    orbit_path = os.path.join(input_dir, "orbit.csv")

    args = _thor_invocation(cfg_path, obs_path, orbit_path, output_dir)

    # Use subprocess.Popen rathen than subprocess.run just so we get a
    # bit more control on output. Doing things carefully lets us stream
    # the process's output through, which lets it appear in logs.
    process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # TODO: Would be nice to set a timeout. But it's trickier than it
    # might appear, if we also want to capture output, since that
    # blocks on the read call. We need to do something like
    # select.poll() to get that right.

    output = b""
    for line in process.stdout:  # type:ignore
        sys.stdout.write(line.decode("utf8"))
        output += line

    return_code = process.wait()
    with open(os.path.join(output_dir, "captured_output.txt"), "wb") as f:
        f.write(output)

    if return_code != 0:
        raise THORExecutionFailure()


def _thor_invocation(
    cfg_path: str, obs_path: str, orbit_path: str, output_dir: str
) -> List[str]:
    """
    Returns the command line arguments used to run THOR.
    """
    script = f"""
    import pandas as pd
    import logging
    from thor import runTHOR
    from thor.orbits import Orbits
    from thor.config import Config

    observations = pd.read_csv(
        "{obs_path}",
        index_col=False,
        dtype={{"obs_id": str}},
    )

    test_orbits = Orbits.from_csv("{orbit_path}")

    config = Config.fromYaml("{cfg_path}")

    runTHOR(
        observations,
        test_orbits,
        range_shift_config=config.RANGE_SHIFT_CONFIG,
        cluster_link_config=config.CLUSTER_LINK_CONFIG,
        iod_config=config.IOD_CONFIG,
        od_config=config.OD_CONFIG,
        odp_config=config.ODP_CONFIG,
        out_dir="{output_dir}",
        logging_level=logging.INFO,
    )
    """
    return ["python", "-c", script]


class THORExecutionFailure(Exception):
    def __init__(self):
        pass
