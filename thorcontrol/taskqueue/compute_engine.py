import json
import logging
import time
from typing import Any, Dict, List

import googleapiclient.discovery
import requests

logger = logging.getLogger("thor")


def terminate_self():
    """
    Terminate the Google Compute Engine VM that is running the current process.

    This will trigger shutdown of the current host, if it is on GCE..
    """

    logger.info("terminating running Google Compute Engine instance")
    logger.info("trying to infer the identity of the instance...")
    name = discover_instance_name()
    zone_url = discover_instance_zone()
    zone = zone_url.split("/")[-1]
    project = discover_project_id()
    logger.info(
        "identity inference done. name=%s  zone=%s  project=%s", name, zone, project
    )

    logger.info("sending DELETE request to terminate instance")
    compute_client = googleapiclient.discovery.build("compute", "v1")
    operation = (
        compute_client.instances()
        .delete(
            project=project,
            zone=zone,
            instance=name,
        )
        .execute()
    )

    logger.info("Blocking to wait for the delete to complete")
    compute_client.zoneOperations().wait(
        project=project, zone=zone, operation=operation["name"]
    ).execute()


def update_self_metadata(keyvals: Dict[str, str]):
    """Calls update_instance_metadata on the currently-running instance."""
    name = discover_instance_name()
    zone_url = discover_instance_zone()
    zone = zone_url.split("/")[-1]
    project = discover_project_id()
    logger.debug(
        "identity inference done. name=%s  zone=%s  project=%s", name, zone, project
    )
    update_instance_metadata(project, zone, name, keyvals)


def update_instance_metadata(
    project: str, zone: str, name: str, keyvals: Dict[str, str]
):
    """
    Updates a running instance's metadata, setting the given key-value pairs.

    If any of the keys are already present in the instance's metadata, they are
    modified. Any metadata not present in keyvals is left unchanged.
    """

    with googleapiclient.discovery.build("compute", "v1") as client:
        # Retrieve the current metadata so we only update the job, task and
        # status keys. Everything else should be left unchanged.
        instance = client.instances().get(project=project, zone=zone, instance=name)
        fingerprint = instance["metadata"]["fingerprint"]
        metadata = instance["metadata"]["items"]

        metadata = _update_metadata_list(metadata, keyvals)

        logger.info("updating instance metadata to %s", keyvals)
        operation = (
            client.instances()
            .setMetadata(
                project=project,
                zone=zone,
                instance=instance,
                fingerprint=fingerprint,
                items=metadata,
            )
            .execute()
        )

        logger.debug("waiting for instance metadata update to complete")
        client.zoneOperations().wait(
            project=project, zone=zone, operation=operation["name"]
        ).execute()


def _update_metadata_list(
    metadata: List[Dict[str, str]], updates: Dict[str, str]
) -> List[Dict[str, str]]:
    """
    Update a google instance metadata-style list of key-value pairs with the
    values in updates.
    """
    updated = set()
    for item in metadata:
        key = item["key"]
        if key in updates:
            item["value"] = updates[key]
            updated.add(key)

    for key, value in updates.items():
        if key not in updated:
            metadata.append({"key": key, "value": value})

    return metadata


def _google_metadata_request(path: str) -> Any:
    retry_limit = 30
    retry_count = 0
    while retry_count < retry_limit:
        response = requests.get(
            "http://metadata.google.internal" + path,
            headers={"Metadata-Flavor": "Google"},
            timeout=1.0,
        )
        if response.status_code == 503:
            # Indicates metadata server maintenance. Retry.
            retry_count += 1
            time.sleep(1)
            continue
        break
    response.raise_for_status()
    return response.content


def discover_running_on_compute_engine() -> bool:
    """
    Returns True if the current Python process is running on Google Compute
    Engine.

    Returns
    -------
    bool
        Whether the current process is running on GCE.
    """
    try:
        _google_metadata_request("")
        return True
    except (requests.ConnectionError, requests.HTTPError):
        return False


def discover_instance_name() -> str:
    """
    Query Google Compute Engine metadata to discover the host instance's name.

    If not running on Google Compute Engine, this function raises either a
    requests.HTTPError or a requests.ConnectionError.

    Returns
    -------
    bytes : The raw name of the running instance.

    Examples
    --------

    >>> discover_instance_name()
    'asgard'
    """
    return _google_metadata_request("/computeMetadata/v1/instance/name").decode()


def discover_instance_zone() -> str:
    """
    Query Google Compute Engine metadata to discover the host instance's zone.

    If not running on Google Compute Engine, this function raises either a
    requests.HTTPError or a requests.ConnectionError.

    Returns
    -------

    bytes : The URL of the running instance's zone.

    Examples
    --------

    >>> discover_instance_zone()
    'projects/492788363398/zones/us-west1-a'
    """
    return _google_metadata_request("/computeMetadata/v1/instance/zone").decode()


def discover_project_id() -> str:
    return _google_metadata_request("/computeMetadata/v1/project/project-id").decode()


def _get_access_token() -> str:
    raw = _google_metadata_request(
        "/computeMetadata/v1/instance/service-accounts/default/token"
    )
    parsed = json.loads(raw)
    return parsed["access_token"]
