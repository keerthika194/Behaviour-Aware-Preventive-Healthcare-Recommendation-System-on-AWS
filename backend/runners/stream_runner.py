"""
Decoupled DynamoDB Stream / Table Runner (Pattern B Development Mode Fallback)
==============================================================================
Operational local/development daemon that continuously processes unprocessed
smartwatch sensor records from DynamoDB 'activity_events' using the exact same
production inference logic as the 'health-adherence-ml-engine' Lambda handler.

Features:
1. Ingests records where status is 'received' or pending.
2. Extracts the 30 statistical time-domain features across accelerometer and gyroscope.
3. Loads and caches Random Forest and XGBoost model artifacts across iterations.
4. Retrieves user clinical baseline profiles from DynamoDB 'profiles'.
5. Runs dual inference (< 50ms) to predict activity and chronic disease risk.
6. Writes output recommendations to DynamoDB 'recommendations' with 24-hr TTL ('expire_at').
7. Atomically updates source 'activity_events' record status to 'processed'.
8. Provides graceful shutdown, batch size bounding (1-5), and rich operational metrics.
"""

import os
import sys
import time
import signal
import logging
import argparse
from pathlib import Path
from decimal import Decimal
import boto3
from boto3.dynamodb.conditions import Attr

# Ensure backend/functions is in PYTHONPATH for importing ml_engine_lambda
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FUNCTIONS_DIR = PROJECT_ROOT / "backend" / "functions"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(FUNCTIONS_DIR) not in sys.path:
    sys.path.insert(0, str(FUNCTIONS_DIR))

try:
    import ml_engine_lambda
except ImportError as err:
    # Fallback to direct import if path setup differs
    from backend.functions import ml_engine_lambda

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [STREAM_RUNNER] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("stream_runner")


class StreamRunner:
    """
    Continuous or single-pass runner for Pattern B event processing.
    """

    def __init__(
        self,
        region_name="ap-south-1",
        activity_table_name="activity_events",
        recommendations_table_name="recommendations",
        profiles_table_name="profiles",
        batch_size=5,
        poll_interval=2.0,
        include_failed=False
    ):
        self.region_name = region_name
        self.activity_table_name = activity_table_name
        self.recommendations_table_name = recommendations_table_name
        self.profiles_table_name = profiles_table_name
        self.batch_size = max(1, min(batch_size, 5))
        self.poll_interval = poll_interval
        self.include_failed = include_failed
        self._running = True

        # Initialize boto3 DynamoDB resource
        self.dynamodb = boto3.resource("dynamodb", region_name=self.region_name)
        self.activity_table = self.dynamodb.Table(self.activity_table_name)
        self.recommendations_table = self.dynamodb.Table(self.recommendations_table_name)
        self.profiles_table = self.dynamodb.Table(self.profiles_table_name)

        # Pre-warm ML models once at initialization
        logger.info("Initializing ML model artifacts and warming cache...")
        ml_engine_lambda.load_models()
        logger.info("ML Models initialized successfully.")

        # Performance tracking metrics
        self.stats = {
            "polled_count": 0,
            "processed_count": 0,
            "skipped_count": 0,
            "failed_count": 0,
            "latencies_ms": []
        }

    def stop(self):
        """Signals the runner to stop after finishing current batch."""
        self._running = False
        logger.info("Termination signal received. Gracefully stopping stream runner...")

    def fetch_unprocessed_records(self, limit=5, include_failed=False):
        """
        Scans DynamoDB activity_events for records that have not yet been processed.
        Paginates properly through DynamoDB until 'limit' items are matched or
        the table is exhausted, preventing the DynamoDB scan Limit pre-filter trap.
        Targets items where status is 'received', 'pending', or missing.
        """
        if include_failed:
            filter_expr = Attr("status").ne("processed") & Attr("status").ne("archived")
        else:
            filter_expr = (
                Attr("status").eq("received")
                | Attr("status").eq("pending")
                | Attr("status").not_exists()
            )
        matched_items = []
        scan_kwargs = {"FilterExpression": filter_expr}

        try:
            while len(matched_items) < limit:
                response = self.activity_table.scan(**scan_kwargs)
                items = response.get("Items", [])
                matched_items.extend(items)

                lek = response.get("LastEvaluatedKey")
                if not lek or len(matched_items) >= limit:
                    break
                scan_kwargs["ExclusiveStartKey"] = lek

            # Prioritize items chronologically by timestamp
            matched_items.sort(key=lambda x: str(x.get("timestamp", "")), reverse=False)
            return matched_items[:limit]
        except Exception as exc:
            logger.error(f"Error scanning {self.activity_table_name} for unprocessed records: {exc}")
            return []

    def process_record(self, raw_item):
        """
        Passes a single unprocessed item to the production ml_engine_lambda processor.
        """
        event_id = raw_item.get("event_id", "unknown")
        try:
            start_t = time.perf_counter()
            result = ml_engine_lambda.process_single_event(raw_item)
            duration_ms = (time.perf_counter() - start_t) * 1000.0

            self.stats["processed_count"] += 1
            self.stats["latencies_ms"].append(duration_ms)

            logger.info(
                f"[SUCCESS] event_id={event_id} -> "
                f"RecID={result.get('recommendation_id')} | "
                f"Activity={result.get('activity')} (conf={result.get('activity_confidence')}) | "
                f"Risk={result.get('risk_score')} ({result.get('risk_band')}) | "
                f"TTL={result.get('expire_at')} | "
                f"Latency={duration_ms:.2f}ms"
            )
            return result

        except Exception as exc:
            self.stats["failed_count"] += 1
            logger.error(f"[FAILED] Error processing event_id={event_id}: {exc}")
            # Mark failed status in DynamoDB so broken items don't loop endlessly
            if event_id != "unknown":
                try:
                    self.activity_table.update_item(
                        Key={"event_id": str(event_id)},
                        UpdateExpression="SET #s = :status, error_message = :err",
                        ExpressionAttributeNames={"#s": "status"},
                        ExpressionAttributeValues={":status": "failed", ":err": str(exc)[:250]}
                    )
                except Exception:
                    pass
            return None

    def run_batch(self):
        """
        Fetches and processes one batch of unprocessed events.
        Returns the number of records successfully processed.
        """
        items = self.fetch_unprocessed_records(limit=self.batch_size, include_failed=self.include_failed)
        if not items:
            return 0

        self.stats["polled_count"] += len(items)
        logger.info(f"Discovered {len(items)} unprocessed event(s) in {self.activity_table_name}. Ingesting...")

        batch_success = 0
        for item in items:
            res = self.process_record(item)
            if res:
                batch_success += 1

        return batch_success

    def run(self, once=False, max_batches=None):
        """
        Main execution loop.
        """
        logger.info("==================================================================")
        logger.info("  HEALTH ADHERENCE STREAM RUNNER (Pattern B Fallback)")
        logger.info("==================================================================")
        logger.info(f"Region              : {self.region_name}")
        logger.info(f"Activity Table      : {self.activity_table_name}")
        logger.info(f"Recommendations Table: {self.recommendations_table_name}")
        logger.info(f"Batch Size          : {self.batch_size}")
        logger.info(f"Poll Interval       : {self.poll_interval}s")
        logger.info(f"Single-Pass Mode    : {once}")
        logger.info(f"Include Failed      : {self.include_failed}")
        logger.info("==================================================================")

        batch_count = 0

        while self._running:
            processed = self.run_batch()

            batch_count += 1
            if max_batches and batch_count >= max_batches:
                logger.info(f"Reached maximum requested batches ({max_batches}). Stopping.")
                break

            if once:
                # If single-pass, check if there are remaining unprocessed records
                remaining = self.fetch_unprocessed_records(limit=1, include_failed=self.include_failed)
                if not remaining:
                    logger.info("Single-pass completed. No further unprocessed records found.")
                    break
                # If there are still items remaining in once mode, continue processing until all are handled
                continue

            time.sleep(self.poll_interval)

        self._print_summary()

    def _print_summary(self):
        """Prints diagnostic and throughput summary."""
        avg_latency = (
            sum(self.stats["latencies_ms"]) / len(self.stats["latencies_ms"])
            if self.stats["latencies_ms"]
            else 0.0
        )
        logger.info("==================================================================")
        logger.info("  STREAM RUNNER EXECUTION SUMMARY")
        logger.info("==================================================================")
        logger.info(f"Total Polled Records : {self.stats['polled_count']}")
        logger.info(f"Successfully Processed: {self.stats['processed_count']}")
        logger.info(f"Failed Records       : {self.stats['failed_count']}")
        logger.info(f"Average Dual Latency : {avg_latency:.2f}ms")
        logger.info("==================================================================")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Health Adherence Serverless ML Engine Development Runner"
    )
    parser.add_argument(
        "--region",
        default=os.environ.get("AWS_REGION", "ap-south-1"),
        help="AWS Region (default: ap-south-1)"
    )
    parser.add_argument(
        "--table",
        default="activity_events",
        help="DynamoDB activity events table (default: activity_events)"
    )
    parser.add_argument(
        "--recommendations-table",
        default="recommendations",
        help="DynamoDB recommendations table (default: recommendations)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5,
        help="Batch size (1 to 5, default: 5)"
    )
    parser.add_argument(
        "--interval",
        "--poll-interval",
        type=float,
        default=2.0,
        dest="poll_interval",
        help="Poll interval in seconds (default: 2.0)"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run single-pass processing until all pending events are cleared, then exit"
    )
    parser.add_argument(
        "--max-batches",
        type=int,
        default=None,
        help="Maximum number of polling batches to execute before stopping"
    )
    parser.add_argument(
        "--include-failed",
        action="store_true",
        help="Include records previously marked as failed for reprocessing"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    runner = StreamRunner(
        region_name=args.region,
        activity_table_name=args.table,
        recommendations_table_name=args.recommendations_table,
        batch_size=args.batch_size,
        poll_interval=args.poll_interval,
        include_failed=args.include_failed
    )

    def handle_signal(sig, frame):
        runner.stop()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    runner.run(once=args.once, max_batches=args.max_batches)


if __name__ == "__main__":
    main()
