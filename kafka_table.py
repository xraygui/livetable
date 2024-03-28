import nslsii.kafka_utils
from bluesky_kafka import RemoteDispatcher
from bluesky.callbacks.best_effort import BestEffortCallback
from lessEffortCallback import LessEffortCallback
import uuid
import argparse


def kafka_table(beamline_acronym, config_file, topic_string="bluesky.documents", out=print):
    bec = LessEffortCallback(out=out)
    #bec = BestEffortCallback()
    kafka_config = nslsii.kafka_utils._read_bluesky_kafka_config_file(
        config_file_path=config_file
    )

    # this consumer should not be in a group with other consumers
    #   so generate a unique consumer group id for it
    unique_group_id = f"echo-{beamline_acronym}-{str(uuid.uuid4())[:8]}"

    kafka_dispatcher = RemoteDispatcher(
        topics=[f"{beamline_acronym}.{topic_string}"],
        bootstrap_servers=",".join(kafka_config["bootstrap_servers"]),
        group_id=unique_group_id,
        consumer_config=kafka_config["runengine_producer_config"],
    )

    kafka_dispatcher.subscribe(bec)
    kafka_dispatcher.start()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kafka LiveTable Monitor")
    parser.add_argument("--bl", required=True, help="Beamline acronym used for kafka topic")
    parser.add_argument("--config-file", default="/etc/bluesky/kafka.yml", help="kafka config file location")
    parser.add_argument("--topic-string", default="bluesky.runengine.documents", help="string to be combined with acronym to create topic")

    args = parser.parse_args()

    kafka_table(args.bl, args.config_file, args.topic_string)
