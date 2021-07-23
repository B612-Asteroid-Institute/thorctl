from typing import List, Optional, Dict, Mapping
import random
import logging
import string
import pika

import googleapiclient.discovery

SERVICE_ACCOUNT_EMAIL = "thor-worker@moeyens-thor-dev.iam.gserviceaccount.com"
DEFAULT_PROJECT = "moeyens-thor-dev"
DEFAULT_ZONES = ["us-west1-a", "us-west1-b", "us-west1-c"]

logger = logging.getLogger("thorctl")


class WorkerPoolManager:
    def __init__(
        self,
        queue_name: str,
        project: str = DEFAULT_PROJECT,
        zones: Optional[List[str]] = None,
    ):
        self.queue_name = queue_name
        self.project = project
        if zones is None:
            zones = DEFAULT_ZONES
        self.zones = zones
        self.compute_client = googleapiclient.discovery.build("compute", "v1")

    def current_num_workers(self) -> int:
        """
        Returns the current number of workers which are running to handle
        queue_name.
        """
        return len(self.list_worker_instances())

    def launch_workers(self, n_workers: int, machine_type: str):
        """
        Create n_workers instances to handle queue_name, spreading them across zones.
        """
        # Round-robin through the zones, starting from a random one.
        zone_offset = random.randint(0, len(self.zones) - 1)
        operations = []
        for i in range(n_workers):
            zone = self.zones[(i + zone_offset) % len(self.zones)]
            op = self.launch_single_worker(zone, machine_type, wait=False)
            operations.append(op)

        for op in operations:
            self.wait_until_complete(op)

    def launch_single_worker(self, zone: str, machine_type: str, wait: bool = True):
        """
        Create a worker instance to handle queue_name in given zone, using given
        machine type.
        """
        worker_name = self._worker_name()
        disk = {
            "boot": True,
            "diskSizeGb": "100",
            "initializeParams": {
                "sourceImage": "projects/cos-cloud/global/images/family/cos-stable",
                "labels": worker_labels(self.queue_name),
            },
            "autoDelete": True,
        }

        # Setting an access config guarantees that an ephemeral external IP will be
        # provisioned.
        network = {
            "accessConfigs": [{"type": "ONE_TO_ONE_NAT", "networkTier": "STANDARD"}]
        }

        # This service account has permission to use secretmanager and object storage.
        service_account = {
            "email": SERVICE_ACCOUNT_EMAIL,
            "scopes": ["https://www.googleapis.com/auth/cloud-platform"],
        }

        cloud_init_config = f"""#cloud-config

users:
- name: thor-worker
  uid: 2000

write_files:
- path: /etc/systemd/system/thor-worker.service
  permissions: 0644
  owner: root
  content: |
    [Unit]
    Description=THOR worker
    Wants=gcr-online.target
    After=gcr-online.target

    [Service]
    Restart=always
    Environment="HOME=/home/thor-worker"
    ExecStartPre=/usr/bin/docker-credential-gcr configure-docker && \
        docker pull gcr.io/moeyens-thor-dev/thor-worker
    ExecStart=/usr/bin/docker run --rm \
                        --name thor-worker \
                        --env THOR_QUEUE={self.queue_name} \
                        --net=host \
                        gcr.io/moeyens-thor-dev/thor-worker
    ExecStop=/usr/bin/docker stop thor-worker
    ExecStopPost=/usr/bin/docker rm thor-worker

runcmd:
- systemctl daemon-reload
- systemctl start thor-worker.service
"""
        metadata = {
            "items": [
                {
                    "key": "user-data",
                    "value": cloud_init_config
            ]
        }

        machine = f"zones/{zone}/machineTypes/{machine_type}"
        req = {
            "name": worker_name,
            "description": "generated by thorctl",
            "machineType": machine,
            "disks": [disk],
            "networkInterfaces": [network],
            "serviceAccounts": [service_account],
            "labels": worker_labels(self.queue_name),
            "metadata": metadata,
        }

        logger.info("creating worker %s in %s", worker_name, zone)
        op = (
            self.compute_client.instances()
            .insert(project=self.project, zone=zone, body=req)
            .execute()
        )
        if wait:
            op = self.wait_until_complete(op)
        return op

    def list_worker_instances(self) -> List[Dict]:
        filter_expr = worker_filter_by_labels(self.queue_name)
        instances = []
        for zone in self.zones:
            response = (
                self.compute_client.instances()
                .list(project=self.project, zone=zone, filter=filter_expr)
                .execute()
            )
            instances.extend(response.get("items", []))
        return instances

    def terminate_all_workers(self):
        workers = self.list_worker_instances()
        operations = []
        for w in workers:
            zone = self._parse_zone_url(w["zone"])
            op = self.terminate_worker_instance(w["name"], zone, False)
            operations.append(op)
        for op in operations:
            self.wait_until_complete(op)

    def terminate_worker_instance(
        self, instance_name: str, zone: str, wait: bool = True
    ):
        """Delete an instance by name."""
        logger.info("deleting instance %s in %s", instance_name, zone)
        op = (
            self.compute_client.instances()
            .delete(project=self.project, zone=zone, instance=instance_name)
            .execute()
        )
        if wait:
            self.wait_until_complete(op)
        return op

    def wait_until_complete(self, op):
        """
        Block until an operation completes.

        Returns an operation which should be DONE.
        """
        logger.info(
            "waiting for %s operation to complete", op.get("operationType", "UNKNOWN")
        )
        if op.get("zone", "") != "":
            zoc = self.compute_client.zoneOperations()
            zone = self._parse_zone_url(op["zone"])
            return zoc.wait(
                project=self.project, zone=zone, operation=op["name"]
            ).execute()

        elif op.get("region", "") != "":
            region = self._parse_region_url(op["region"])
            roc = self.compute_client.regionOperations()
            return roc.wait(
                project=self.project, region=region, operation=op["name"]
            ).execute()

        else:
            goc = self.compute_client.globalOperations()
            return goc.wait(project=self.project, operation=op["name"]).execute()

    def _worker_name(self):
        return f"{self.queue_name}-worker-{rand_str(6)}"

    def _parse_zone_url(self, s: str) -> str:
        prefix = f"https://www.googleapis.com/compute/v1/projects/{self.project}/zones/"
        return s[len(prefix) :]

    def _parse_region_url(self, s: str) -> str:
        prefix = (
            f"https://www.googleapis.com/compute/v1/projects/{self.project}/regions/"
        )
        return s[len(prefix) :]


def worker_labels(queue_name: str) -> Mapping[str, str]:
    return {
        "service": "thor-worker",
        "queue": queue_name,
    }


def worker_filter_by_labels(queue_name: str) -> str:
    labels = worker_labels(queue_name)
    return " AND ".join(f"(labels.{key} = {value})" for key, value in labels.items())


def rand_str(length: int) -> str:
    """Return a string of given length composed of lowercase ascii letters.

    Parameters
    ----------
    length : int
        Number of characters in the string

    Returns
    -------
    str
        A random string of lowercase ascii characters
    """

    return "".join(random.choices(string.ascii_lowercase, k=length))
