# Module for running THOR in a subprocess.
import asyncio
import io
import logging
import os.path
import sys
from typing import List

logger = logging.getLogger("thor")


async def run_thor_subprocess(input_dir: str, output_dir: str, timeout: int):
    cfg_path = os.path.join(input_dir, "config.yml")
    obs_path = os.path.join(input_dir, "observations.csv")
    orbit_path = os.path.join(input_dir, "orbit.csv")

    args = _thor_invocation(cfg_path, obs_path, orbit_path, output_dir)

    process = await asyncio.subprocess.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    captured_stdout = io.BytesIO()
    captured_stderr = io.BytesIO()

    async def copy_stdout():
        while True:
            line = await process.stdout.readline()
            if line == b"":
                return
            captured_stdout.write(line)
            sys.stdout.write(line.decode("utf8"))

    async def copy_stderr():
        while True:
            line = await process.stderr.readline()
            if line == b"":
                return
            captured_stderr.write(line)
            sys.stderr.write(line.decode("utf8"))

    all_done = asyncio.wait([copy_stderr(), copy_stdout(), process.wait()])
    try:
        await asyncio.wait_for(all_done, timeout=timeout)
    except asyncio.TimeoutError as e:
        process.kill()
        raise TimeoutExceeded() from e

    return_code = process.returncode
    assert return_code is not None

    with open(os.path.join(output_dir, "stdout.txt"), "wb") as f:
        f.write(captured_stdout.getvalue())
    with open(os.path.join(output_dir, "stderr.txt"), "wb") as f:
        f.write(captured_stderr.getvalue())
    with open(os.path.join(output_dir, "returncode.txt"), "wb") as f:
        code_txt = str(return_code).encode("utf8")
        f.write(code_txt)

    if return_code != 0:
        raise THORExecutionFailure(
            return_code, captured_stdout.getvalue(), captured_stderr.getvalue()
        )


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
    if_exists="erase",
)
    """
    return ["python", "-c", script]


class THORExecutionFailure(Exception):
    def __init__(self, retcode: int, stdout: bytes, stderr: bytes):
        self.retcode = retcode
        self.stdout = stdout
        self.stderr = stderr


class TimeoutExceeded(Exception):
    pass
