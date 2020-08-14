import json
import os
from time import sleep, strptime

import click
from pathlib import Path

import requests

URL = "https://www.skatteetaten.no/api/kontantstotteForNaeringRegister/process?skip={skip}&take={take}&order%5Bcolumn%5D=sakId&order%5Bdir%5D=asc&search=&dateFilter%5BfromDate%5D={from_date}&dateFilter%5BtoDate%5D={to_date}"

# Limited by Skatteetaten
MAX_PER_REQUEST = 1000
# Pause between each request for courtesy's sake
REQUEST_DELAY = 0.1


def download(output_directory, output_filename, from_date, to_date):
    """
    Download corona support grants from Skatteetaten

    :param output_directory: Directory to which the corona data file will be downloaded
    :param output_filename: Filename to which the corona data file will be downloaded
    :param from_date: Start date ('%Y-%m-%d') of range from which to download data
    :param to_date: End of date ('%Y-%m-%d') of range from which to download data
    :return: posix return code for success or failure
    """
    # Get the total number of registrations; only relevant if downloading everything
    summary = requests.get(
        URL.format(skip=0, take=1, from_date=from_date, to_date=to_date)
    )
    if summary.status_code == 200:
        total = summary.json()["recordsFiltered"]
    else:
        print(f"ERROR: Got status code {summary.status_code}")
        return 1

    support_entries = []
    counter = 0

    while counter < total:
        print(f"Downloading {counter} of {total}")
        # TODO: Use more idiomatic parameter building from request library
        req = requests.get(
            URL.format(
                skip=counter, take=MAX_PER_REQUEST, from_date=from_date, to_date=to_date
            )
        )
        if req.status_code == 200:
            part = req.json()["data"]
        else:
            print(
                f"ERROR: Got to {counter} of {total}, then received a {req.status_code} response"
            )
            return 1
        support_entries.extend(part)
        counter += MAX_PER_REQUEST
        sleep(REQUEST_DELAY)  # lets be courteous...
    print(f"Downloaded {len(support_entries)} of {total}\nDONE")

    dump(
        support_entries,
        output_directory=output_directory,
        output_filename=output_filename,
    )

    return 0


# TODO: Implement error handling in case one can't write to file, etc.
def dump(data, output_directory, output_filename):
    """
    Dumps the data (of type string) into output_filename within output_directory

    :param data: String to write (of type string)
    :param output_directory: Directory to which the data file will be written
    :param output_filename: Filename to which the data file will be written
    :return:
    """
    with open(output_directory + os.sep + output_filename, "w") as output_file:
        output_file.write(json.dumps(data))


@click.command()
@click.option(
    "--output-directory",
    default=str(os.path.join(Path.home(), "Downloads")),
    help="Directory to which the data will be downloaded (default: 'Downloads' directory under user's $HOME)",
)
@click.option(
    "--output-filename",
    default="corona.json",
    help="Filename to which the data will be downloaded (default: 'corona.json')",
)
@click.option(
    "--from-date",
    default=None,
    help="From date in ISO 8601-ish format (%Y-m%-%d: 2020-08-01)",
)
@click.option(
    "--to-date",
    default=None,
    help="To date in ISO 8601-ish format (%Y-m%-%d: 2020-08-01)",
)
def app(output_directory, output_filename, from_date, to_date):
    if not os.path.isdir(output_directory):
        click.echo(f"{output_directory} is not a valid output directory")
        return 1

    try:
        if from_date:
            strptime(from_date, "%Y-%m-%d")
    except ValueError:
        print(f"--from-date ({from_date}) does not match format '%Y-%m-%d'")
        return 1
    try:
        if to_date:
            strptime(to_date, "%Y-%m-%d")
    except ValueError:
        print(f"--to-date ({to_date}) does not match format '%Y-%m-%d'")
        return 1

    return download(output_directory, output_filename, from_date, to_date)
