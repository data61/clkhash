#!/usr/bin/env python3.6
from __future__ import print_function

import json
import time

import click
import requests

import clkhash
from clkhash import clk
from clkhash import benchmark as bench
from clkhash import randomnames
from clkhash.schema import get_schema_types, load_schema


DEFAULT_SERVICE_URL = 'https://es.data61.xyz'


def log(m, color='red'):
    click.echo(click.style(m, fg=color), err=True)


@click.group("clkutil")
@click.version_option(clkhash.__version__)
@click.option('--verbose', '-v', is_flag=True,
              help='Enables verbose mode.')
def cli(verbose=False):
    """
    This command line application allows a user to hash their
    data into cryptographic longterm keys for use in
    private comparison.

    This tool can also interact with a entity matching service;
    creating new mappings, uploading locally hashed data,
    watching progress, and retrieving results.

    Example:

        clkutil hash private_data.csv secretkey1 secretkey2 output-clks.json


    All rights reserved Confidential Computing 2016.
    """



@cli.command('hash', short_help="generate hashes from local PII data")
@click.argument('input', type=click.File('r'))
@click.argument('keys', nargs=2, type=click.Tuple([str, str]))
@click.option('--schema', '-s', type=click.File('r'), default=None)
@click.argument('output', type=click.File('w'))
@click.option('-q', '--quiet', default=False, is_flag=True, help="Quiet any progress messaging")
@click.option('--no-header', default=False, is_flag=True, help="Don't skip the first row")
@click.option('--xor-folds', default=0, type=click.IntRange(0, None))
def hash(input, output, schema, keys, quiet, no_header, xor_folds):
    """Process data to create CLKs

    Given a file containing CSV data as INPUT, and optionally a json
    document defining the expected schema, verify the schema, then
    hash the data to create CLKs writing to OUTPUT. Note the CSV
    file should contain a header row - however this row is not used
    by this tool.

    It is important that the keys are only known by the two data providers. Two words should be provided. For example:

    $clkutil hash input.txt horse staple output.txt

    Use "-" to output to stdout.
    """

    schema_types = get_schema_types(load_schema(schema))

    clk_data = clk.generate_clk_from_csv(input, keys, schema_types, no_header, not quiet, xor_folds)
    json.dump({'clks': clk_data}, output)
    if hasattr(output, 'name'):
        log("CLK data written to {}".format(output.name))


@cli.command('status', short_help='Get status of entity service')
@click.option('--server', type=str, default=DEFAULT_SERVICE_URL, help="Server address including protocol")
@click.option('-o','--output', type=click.File('w'), default='-')
@click.option('-v', '--verbose', default=False, is_flag=True, help="Script is more talkative")
def status(server, output, verbose):
    """Connect to an entity matching server and check the service status.

    Use "-" to output status to stdout.
    """
    log("Connecting to Entity Matching Server: {}".format(server))

    response = requests.get(server + "/api/v1/status")
    server_status = response.json()
    log("Response: {}".format(response.status_code))
    log("Status: {}".format(server_status['status']))
    print(json.dumps(server_status), file=output)


MAPPING_CREATED_MSG = """
The generated tokens can be used to upload hashed data and
fetch the resulting linkage table from the service.

To upload using the cli tool for entity A:

    clkutil hash a_people.csv A_HASHED_FILE.json
    clkutil upload --mapping="{resource_id}" --apikey="{update_tokens[0]}"  A_HASHED_FILE.json

To upload using the cli tool for entity B:

    clkutil hash b_people.csv B_HASHED_FILE.json
    clkutil upload --mapping="{resource_id}" --apikey="{update_tokens[1]}" B_HASHED_FILE.json

After both users have uploaded their data one can watch for and retrieve the results:

    clkutil results -w --mapping="{resource_id}" --apikey="{result_token}" --output results.txt

"""

@cli.command('create', short_help="create a mapping on the entity service")
@click.option('--type', default='permutation_unencrypted_mask',
              help='Alternative protocol/view type of the mapping. Default is unencrypted permutation and mask.')
@click.option('--schema', type=click.File('r'), help="Schema to publicly share with participating parties.")
@click.option('--server', type=str, default=DEFAULT_SERVICE_URL, help="Server address including protocol")
@click.option('-o','--output', type=click.File('w'), default='-')
@click.option('-t','--threshold', type=float, default=0.95)
@click.option('-v', '--verbose', default=False, is_flag=True, help="Script is more talkative")
def create(type, schema, server, output, threshold, verbose):
    """Create a new mapping on an entity matching server.

    See entity matching service documentation for details on mapping type, threshold
    and schema.

    Returns authentication details for the created mapping.
    """

    log("Entity Matching Server: {}".format(server))

    log("Checking server status")
    status = requests.get(server + "/api/v1/status").json()['status']
    log("Server Status: {}".format(status))

    if schema is not None:
        schema_object = load_schema(schema)
        schema_json = json.dumps(schema_object)
    else:
        schema_json = 'NOT PROVIDED'

    log("Schema: {}".format(schema_json))
    log("Type: {}".format(type))

    log("Creating new mapping")
    response = requests.post(
        "{}/api/v1/mappings".format(server),
        json={
            'schema': schema_json,
            'result_type': type,
            'threshold': threshold
        }
    )

    if response.status_code != 200:
        log("Unexpected response")
        log(response.text)
    else:
        log("Mapping created")
        if verbose:
            log(MAPPING_CREATED_MSG.format(**response.json()))
        print(response.text, file=output)


@cli.command('upload', short_help='upload hashes to entity service')
@click.argument('input', type=click.File('r'))
@click.option('--mapping', help='Server identifier of the mapping')
@click.option('--apikey', help='Authentication API key for the server.')
@click.option('--server', type=str, default=DEFAULT_SERVICE_URL, help="Server address including protocol")
@click.option('-o','--output', type=click.File('w'), default='-')
@click.option('-v', '--verbose', default=False, is_flag=True, help="Script is more talkative")
def upload(input, mapping, apikey, server, output, verbose):
    """Upload CLK data to entity matching server.

    Given a json file containing hashed clk data as INPUT, upload to
    the entity resolution service.

    Use "-" to read from stdin.
    """

    log("Uploading CLK data from {}".format(input.name))
    log("To Entity Matching Server: {}".format(server))
    log("Mapping ID: {}".format(mapping))

    log("Checking server status")
    status = requests.get(server + "/api/v1/status").json()['status']
    log("Status: {}".format(status))

    log("Uploading CLK data to the server")

    response = requests.put(
        '{}/api/v1/mappings/{}'.format(server, mapping),
        data=input,
        headers={
            "Authorization": apikey,
            'content-type': 'application/json'
        }
    )

    if verbose:
        log(response.text)
        log("When the other party has uploaded their CLKS, you should be able to watch for results")


    print(response.text, file=output)



@cli.command('results', short_help="fetch results from entity service")
@click.option('--mapping',
              help='Server identifier of the mapping')
@click.option('--apikey', help='Authentication API key for the server.')
@click.option('-w', '--watch', help='Follow/wait until results are available', is_flag=True)
@click.option('--server', type=str, default=DEFAULT_SERVICE_URL, help="Server address including protocol")
@click.option('-o','--output', type=click.File('w'), default='-')
def results(mapping, apikey, watch, server, output):
    """
    Check to see if results are available for a particular mapping
    and if so download.

    Authentication is carried out using the --apikey option which
    must be provided. Depending on the server operating mode this
    may return a mask, a linkage table, or a permutation. Consult
    the entity service documentation for details.
    """

    log("Checking server status")
    status = requests.get(server + "/api/v1/status").json()['status']
    log("Status: {}".format(status))

    def get_result():
        return requests.get(
            '{}/api/v1/mappings/{}'.format(server, mapping),
            headers={"Authorization": apikey}
        )

    response = get_result()
    log("Response code: {}".format(response.status_code))

    if watch:
        while response.status_code != 200:
            time.sleep(1)
            response = get_result()

    if response.status_code == 200:
        log("Received result")
        print(response.text, file=output)
    else:
        log("No result yet")
        log(response.text)


@cli.command('benchmark', short_help='carry out a local benchmark')
def benchmark():
    bench.compute_hash_speed(10000)


@cli.command('generate', short_help='generate random pii data for testing')
@click.argument('size', type=int, default=100)
@click.argument('output', type=click.File('w'))
@click.option('--schema', '-s', type=click.File('r'), default=None)
def generate(size, output, schema):
    """Generate fake PII data for testing"""
    pii_data = randomnames.NameList(size)

    if schema is not None:
        raise NotImplementedError

    randomnames.save_csv(pii_data.names, pii_data.schema, output)


if __name__ == "__main__":
    cli()
