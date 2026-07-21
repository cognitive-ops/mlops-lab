import argparse
import boto3
import time

sagemaker = boto3.client("sagemaker")
logs = boto3.client("logs")

LOG_GROUP = "/aws/sagemaker/TrainingJobs"


def list_jobs():
    """List current SageMaker training jobs."""
    response = sagemaker.list_training_jobs(
        SortBy="CreationTime", SortOrder="Descending")
    jobs = response.get("TrainingJobSummaries", [])
    for job in jobs:
        name = job["TrainingJobName"]
        status = job["TrainingJobStatus"]
        created = job["CreationTime"]
        print(f"{created} | {name} | {status}")


def stream_logs(job_name, poll_interval=10):
    """Stream logs of a specific training job."""
    # Find log stream
    streams = logs.describe_log_streams(
        logGroupName=LOG_GROUP,
        logStreamNamePrefix=job_name,
        # orderBy="LastEventTime",
        descending=True,
        limit=1,
    )
    if not streams["logStreams"]:
        print(f"No logs found yet for job {job_name}")
        return

    log_stream = streams["logStreams"][0]["logStreamName"]
    print(f"Streaming logs for {job_name} (log stream: {log_stream})...")

    next_token = None
    while True:
        kwargs = dict(logGroupName=LOG_GROUP,
                      logStreamName=log_stream, startFromHead=True)
        if next_token:
            kwargs["nextToken"] = next_token

        response = logs.get_log_events(**kwargs)
        for event in response["events"]:
            ts = time.strftime("%Y-%m-%d %H:%M:%S",
                               time.localtime(event["timestamp"] / 1000))
            print(f"[{ts}] {event['message'].rstrip()}")

        next_token = response["nextForwardToken"]

        # check if job is still running
        desc = sagemaker.describe_training_job(TrainingJobName=job_name)
        status = desc["TrainingJobStatus"]
        if status in ("Completed", "Failed", "Stopped"):
            print(f"\n[Done] Training job ended with status: {status}")
            break

        time.sleep(poll_interval)


def stop_job(job_name):
    """Terminate a SageMaker training job."""
    try:
        sagemaker.stop_training_job(TrainingJobName=job_name)
        print(f"Sent stop request for training job: {job_name}")
    except Exception as e:
        print(f"Error stopping job {job_name}: {e}")


def main():
    parser = argparse.ArgumentParser(description="SageMaker CLI Tool")
    subparsers = parser.add_subparsers(dest="command")

    # list
    subparsers.add_parser("list", help="List current training jobs")

    # logs
    logs_parser = subparsers.add_parser(
        "logs", help="Stream logs of a training job")
    logs_parser.add_argument(
        "--job-name", required=True, help="Training job name")

    # stop
    stop_parser = subparsers.add_parser(
        "stop", help="Terminate a training job")
    stop_parser.add_argument(
        "--job-name", required=True, help="Training job name")

    args = parser.parse_args()

    if args.command == "list":
        list_jobs()
    elif args.command == "logs":
        stream_logs(args.job_name)
    elif args.command == "stop":
        stop_job(args.job_name)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
