import os

import djclick as click
import subprocess

BASE_URL = "https://download.geofabrik.de/north-america/us/{}-latest.osm.pbf"


@click.command()
@click.option("--states-file", default="states")
def import_data(states_file):
    with open(states_file) as f:
        states = f.readlines()

    for state in states:
        try:
            print(f"Processing {state}")
            cleaned = state.strip().lower().replace(" ", "-")
            output = f"/osm/logs/{cleaned}.log"
            if os.path.exists(output):
                print(f"ignoring {cleaned}, a log file already exists")
                continue
            data_path = f"/osm/{cleaned}.osm.pbf"
            if not os.path.exists(data_path):
                subprocess.check_call(
                    ["curl", BASE_URL.format(cleaned), "-o", data_path]
                )
            with open(output, "w") as out:
                subprocess.run(
                    [
                        "python",
                        "manage.py",
                        "import_data",
                        "-p",
                        "16",
                        f"/osm/{cleaned}.osm.pbf",
                    ],
                    stdout=out,
                )
        except subprocess.CalledProcessError as ex:
            print(f"Failed processing {state}", ex)
