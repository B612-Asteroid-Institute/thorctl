import argparse
import logging
import os
import sys
from typing import List, Optional

import pika
from google.cloud.secretmanager_v1 import SecretManagerServiceClient
from google.cloud.storage import Client as GCSClient
from rich.console import Console
from rich.table import Table

from thorcontrol.taskqueue.client import Client as TaskQueueClient
from thorcontrol.taskqueue.queue import TaskQueueConnection
from thorcontrol.worker_pool import WorkerPoolManager, _get_external_ip

from .autoscaler import Autoscaler
from .sshconn import WorkerPoolSSHConnection

logger = logging.getLogger("thorctl")

# HACK: not settable currently
DEFAULT_PROJECT = "moeyens-thor-dev"


def dispatch(parser, args):
    if args.command == "size":
        check_size(args.queue)
    elif args.command == "scale-up":
        scale_up(args.queue, args.n_workers, args.machine_type)
    elif args.command == "destroy":
        destroy(args.queue)
    elif args.command == "logs":
        logs(args.queue)
    elif args.command == "autoscale":
        autoscale(
            args.queue,
            args.max_size,
            args.machine_type,
            args.poll_interval,
            args.rabbit_host,
            args.rabbit_port,
            args.rabbit_username,
            args.rabbit_password,
            args.rabbit_password_from_secret_manager,
        )
    elif args.command == "list-workers":
        list_workers(args.queue)
    elif args.command == "list-tasks":
        list_tasks(
            args.queue,
            args.rabbit_host,
            args.rabbit_port,
            args.rabbit_username,
            args.rabbit_password,
            args.rabbit_password_from_secret_manager,
        )
    elif args.command == "retry-task":
        retry_task(
            args.queue,
            args.bucket,
            args.job_id,
            args.task_id,
            args.rabbit_host,
            args.rabbit_port,
            args.rabbit_username,
            args.rabbit_password,
            args.rabbit_password_from_secret_manager,
        )

    elif args.command is None:
        parser.print_usage()
    else:
        raise parser.error("unknown command %s" % args.command)


def parse_args():
    parser = argparse.ArgumentParser("thorctl")

    subparsers = parser.add_subparsers(dest="command")

    scale_up = subparsers.add_parser("scale-up", help="add more workers")
    scale_up.add_argument("--n-workers", type=int, help="end size to arrive at")
    scale_up.add_argument(
        "--machine-type",
        type=str,
        default="e2-standard-8",
        help="Compute Engine machine type",
    )
    scale_up.add_argument(
        "queue", type=str, help="name of the queue that workers will listen to"
    )

    check_size = subparsers.add_parser(
        "size", help="look up the current number of workers"
    )
    check_size.add_argument(
        "queue",
        type=str,
        help="name of the queue that workers are listening to",
    )

    list_workers = subparsers.add_parser(
        "list-workers", help="list the workers in a queue and what they're doing"
    )
    list_workers.add_argument(
        "queue",
        type=str,
        help="name of the queue that workers are listening to",
    )

    destroy = subparsers.add_parser(
        "destroy", help="destroy all workers on a queue, even if they are doing work"
    )
    destroy.add_argument(
        "queue", type=str, help="name of the queue that workers are listening to"
    )

    logs = subparsers.add_parser("logs", help="stream logs from the workers")
    logs.add_argument("queue", type=str, help="name of the queue")

    autoscale = subparsers.add_parser(
        "autoscale", help="monitor a queue and automatically scale it up to handle load"
    )
    autoscale.add_argument(
        "queue",
        action="append",
        help="name of queue to monitor. Can be specified multiple times.",
    )
    autoscale.add_argument(
        "--max-size",
        type=int,
        default=16,
        help="maximum number of workers to run at once, per queue",
    )
    autoscale.add_argument(
        "--machine-type",
        type=str,
        default="e2-standard-8",
        help="Compute Engine machine type",
    )
    autoscale.add_argument(
        "--poll-interval",
        type=int,
        default=5,
        help="time interval in seconds to check sizes",
    )
    autoscale.add_argument(
        "--rabbit-host",
        type=str,
        default="rabbit.c.moeyens-thor-dev.internal",
        help="hostname of the rabbit broker",
    )
    autoscale.add_argument(
        "--rabbit-port", type=int, default=5672, help="port of the rabbit broker"
    )
    autoscale.add_argument(
        "--rabbit-username",
        type=str,
        default="thor",
        help="username to connect with to the rabbit broker",
    )
    autoscale.add_argument(
        "--rabbit-password",
        type=str,
        default="$RABBIT_PASSWORD env var",
        help="password to connect with to the rabbit broker",
    )
    autoscale.add_argument(
        "--rabbit-password-from-secret-manager",
        action="store_true",
        help="load rabbit password from google secret manager",
    )

    list_tasks = subparsers.add_parser(
        "list-tasks", help="list active and pending tasks in a queue"
    )
    list_tasks.add_argument(
        "queue",
        type=str,
        help="name of the queue",
    )
    list_tasks.add_argument(
        "--rabbit-host",
        type=str,
        default="rabbit.c.moeyens-thor-dev.internal",
        help="hostname of the rabbit broker",
    )
    list_tasks.add_argument(
        "--rabbit-port", type=int, default=5672, help="port of the rabbit broker"
    )
    list_tasks.add_argument(
        "--rabbit-username",
        type=str,
        default="thor",
        help="username to connect with to the rabbit broker",
    )
    list_tasks.add_argument(
        "--rabbit-password",
        type=str,
        default="$RABBIT_PASSWORD env var",
        help="password to connect with to the rabbit broker",
    )
    list_tasks.add_argument(
        "--rabbit-password-from-secret-manager",
        action="store_true",
        help="load rabbit password from google secret manager",
    )

    retry_task = subparsers.add_parser(
        "retry-task",
        help="retry a task that appears to be stuck",
    )
    retry_task.add_argument(
        "queue",
        type=str,
        help="name of the queue",
    )
    retry_task.add_argument(
        "bucket",
        type=str,
        help="name of the bucket holding the task's data",
    )
    retry_task.add_argument(
        "job_id",
        type=str,
        help="ID of the job holding the task",
    )
    retry_task.add_argument(
        "task_id",
        type=str,
        help="ID of the task to retry",
    )
    retry_task.add_argument(
        "--rabbit-host",
        type=str,
        default="rabbit.c.moeyens-thor-dev.internal",
        help="hostname of the rabbit broker",
    )
    retry_task.add_argument(
        "--rabbit-port", type=int, default=5672, help="port of the rabbit broker"
    )
    retry_task.add_argument(
        "--rabbit-username",
        type=str,
        default="thor",
        help="username to connect with to the rabbit broker",
    )
    retry_task.add_argument(
        "--rabbit-password",
        type=str,
        default="$RABBIT_PASSWORD env var",
        help="password to connect with to the rabbit broker",
    )
    retry_task.add_argument(
        "--rabbit-password-from-secret-manager",
        action="store_true",
        help="load rabbit password from google secret manager",
    )

    return parser, parser.parse_args()


def scale_up(queue_name: str, n_workers: int, instance_type: str):
    manager = WorkerPoolManager(queue_name)
    current_num = manager.current_num_workers()
    n_to_add = n_workers - current_num
    if n_to_add > 0:
        logger.info(
            "%s has %d workers, scaling up to %d", queue_name, current_num, n_workers
        )
        manager.launch_workers(n_to_add, instance_type)
    else:
        logger.warning(
            "%s has %d workers already, doing nothing", queue_name, current_num
        )


def check_size(queue_name: str):
    manager = WorkerPoolManager(queue_name)
    print(manager.current_num_workers())


def destroy(queue_name: str):
    manager = WorkerPoolManager(queue_name)
    current_num = manager.current_num_workers()
    if current_num == 0:
        logger.warning("queue has no workers")
        return
    response = input(
        f"{queue_name} has {current_num} workers. Really destroy them? (yes/no)"
    )
    if response != "yes":
        print("not proceeding, since you didn't say yes")
    manager.terminate_all_workers()


def logs(queue_name: str):
    manager = WorkerPoolManager(queue_name)
    current_num = manager.current_num_workers()
    if current_num == 0:
        logger.warning("queue has no workers currently")
    conn = WorkerPoolSSHConnection(manager)
    conn.stream_logs()


def autoscale(
    queues: List[str],
    max_size: int,
    machine_type: str,
    poll_interval: int,
    rabbit_host: str,
    rabbit_port: int,
    rabbit_username: str,
    rabbit_password: Optional[str],
    rabbit_password_from_secret_manager: bool,
):

    if rabbit_password == "$RABBIT_PASSWORD env var":
        rabbit_password = os.environ.get("RABBIT_PASSWORD")
    if rabbit_password is None and rabbit_password_from_secret_manager:
        client = SecretManagerServiceClient()
        response = client.access_secret_version(
            name="projects/moeyens-thor-dev/secrets/rabbitmq-password/versions/latest"
        )
        rabbit_password = response.payload.data.decode("utf8")

    rabbit_params = pika.ConnectionParameters(
        host=rabbit_host,
        port=rabbit_port,
        credentials=pika.PlainCredentials(
            username=rabbit_username,
            password=rabbit_password,
        ),
    )
    scaler = Autoscaler(rabbit_params, queues, max_size, machine_type)
    scaler.run(poll_interval)


def list_tasks(
    queue_name: str,
    rabbit_host: str,
    rabbit_port: int,
    rabbit_username: str,
    rabbit_password: Optional[str],
    rabbit_password_from_secret_manager: bool,
):
    """List all the tasks that are currently being handled, or unhandled so far, in the queue"""

    console = Console()

    table = Table(title=f"{queue_name} tasks")
    table.add_column("job-id")
    table.add_column("task-id")
    table.add_column("status")
    table.add_column("worker-name")
    if rabbit_password == "$RABBIT_PASSWORD env var":
        rabbit_password = os.environ.get("RABBIT_PASSWORD")
    if rabbit_password is None and rabbit_password_from_secret_manager:
        client = SecretManagerServiceClient()
        response = client.access_secret_version(
            name="projects/moeyens-thor-dev/secrets/rabbitmq-password/versions/latest"
        )
        rabbit_password = response.payload.data.decode("utf8")

    rabbit_params = pika.ConnectionParameters(
        host=rabbit_host,
        port=rabbit_port,
        credentials=pika.PlainCredentials(
            username=rabbit_username,
            password=rabbit_password,
        ),
    )

    # First, gather all the pending tasks. Then, gather all the in-progress
    # tasks. It's possible that a task moves from pending to in-progress while
    # we're executing. If this happens, we should only print the task once.
    with console.status("connecting to rabbitmq to peek at tasks..."):
        queue_conn = TaskQueueConnection(rabbit_params, queue_name)
        queue_conn.connect()
    with console.status("getting count of tasks in queue..."):
        n_tasks_pending = queue_conn.size()
    with console.status("peeking at tasks in queue..."):
        pending_tasks = queue_conn.peek(n_tasks_pending)
    with console.status("shutting down queue connection..."):
        queue_conn.close()

    manager = WorkerPoolManager(queue_name)
    with console.status("contacting gcloud to list instances handling active tasks..."):
        workers = manager.list_worker_instances()

    # Keep a set of the active task IDs, so we can avoid double-printing if
    # they also appear in the pending list.
    active_tasks = set()
    for w in workers:
        name = w["name"]
        current_job_id = manager.get_current_job(w)
        current_task_id = manager.get_current_task(w)

        if current_job_id == "none":
            # Worker is idle
            continue

        active_tasks.add((current_job_id, current_task_id))
        table.add_row(
            current_job_id,
            current_task_id,
            "IN_PROGRESS",
            name,
        )

    for task in pending_tasks:
        if (task.job_id, task.task_id) in active_tasks:
            continue
        table.add_row(task.job_id, task.task_id, "PENDING", "<none>")

    console.print(table)


def list_workers(queue_name: str):
    """List what all the workers are doing in a particular queue"""
    console = Console()

    manager = WorkerPoolManager(queue_name)
    table = Table(title=f"{queue_name} workers")
    table.add_column("name")
    table.add_column("ip")
    table.add_column("job")
    table.add_column("task")
    table.add_column("thor version")
    table.add_column("thorctl version")
    with console.status("contacting gcloud to list instances..."):
        workers = manager.list_worker_instances()

    if len(workers) == 0:
        print(f"queue {queue_name} has no workers currently running in gcloud")

    for w in workers:
        name = w["name"]
        with console.status("looking up status of {name}"):
            ip = _get_external_ip(w)
            current_job_id = manager.get_current_job(w)
            current_task_id = manager.get_current_task(w)
            thor_version = manager.get_thor_version(w)
            thorctl_version = manager.get_thorctl_version(w)
        table.add_row(
            name,
            ip,
            current_job_id,
            current_task_id,
            thor_version,
            thorctl_version,
        )

    console.print(table)


def retry_task(
    queue_name: str,
    bucket_name: str,
    job_id: str,
    task_id: str,
    rabbit_host: str,
    rabbit_port: int,
    rabbit_username: str,
    rabbit_password: Optional[str],
    rabbit_password_from_secret_manager: bool,
):
    console = Console()

    with console.status("connecting to rabbitmq..."):
        if rabbit_password == "$RABBIT_PASSWORD env var":
            rabbit_password = os.environ.get("RABBIT_PASSWORD")
        if rabbit_password is None and rabbit_password_from_secret_manager:
            secret_client = SecretManagerServiceClient()
            response = secret_client.access_secret_version(
                name="projects/moeyens-thor-dev/secrets/rabbitmq-password/versions/latest"
            )
            rabbit_password = response.payload.data.decode("utf8")
        rabbit_params = pika.ConnectionParameters(
            host=rabbit_host,
            port=rabbit_port,
            credentials=pika.PlainCredentials(
                username=rabbit_username,
                password=rabbit_password,
            ),
        )
        queue_conn = TaskQueueConnection(rabbit_params, queue_name)
        queue_conn.connect()

    with console.status("connecting to google storage bucket..."):
        gcs = GCSClient(project=DEFAULT_PROJECT)
        bucket = gcs.bucket(bucket_name)

    client = TaskQueueClient(bucket, queue_conn)

    with console.status("looking up job manifest..."):
        manifest = client.get_job_manifest(job_id)

    if task_id not in manifest.task_ids:
        console.print("error: task not found in job", style="bold red")
        console.print("task IDs in job:")
        console.print(manifest.task_ids)
        sys.exit(1)

    with console.status("relaunching task..."):
        client.relaunch_task(job_id, task_id)

    console.print("task relaunched")
