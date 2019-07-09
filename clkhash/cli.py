#!/usr/bin/env python3.6
from __future__ import print_function

import json
import os
import shutil
from multiprocessing import freeze_support

import click

import clkhash
from clkhash import (benchmark as bench, clk, randomnames, validate_data,
                     describe as descr)
from clkhash.rest_client import (ClientWaitingConfiguration, ServiceError,
                                 format_run_status, RestClient)
from clkhash.schema import SchemaError

DEFAULT_SERVICE_URL = 'https://es.data61.xyz'


def log(m, color='red'):
    click.echo(click.style(m, fg=color), err=True)


@click.group("clkutil")
@click.version_option(clkhash.__version__)
def cli():
    """
    This command line application allows a user to hash their
    data into cryptographic longterm keys for use in
    private comparison.

    This tool can also interact with a entity matching service;
    creating new mappings, uploading locally hashed data,
    watching progress, and retrieving results.

    Example:

        clkutil hash private_data.csv secretkey1 secretkey2 schema.json output-clks.json


    All rights reserved Confidential Computing 2016.
    """


@cli.command('hash', short_help="generate hashes from local PII data")
@click.argument('pii_csv', type=click.File('r'))
@click.argument('keys', nargs=2, type=click.Tuple([str, str]))
@click.argument('schema', type=click.File('r', lazy=True))
@click.argument('clk_json', type=click.File('w'))
@click.option('-q', '--quiet', default=False, is_flag=True, help="Quiet any progress messaging")
@click.option('--no-header', default=False, is_flag=True, help="Don't skip the first row")
@click.option('--check-header', default=True, type=bool, help="If true, check the header against the schema")
@click.option('--validate', default=True, type=bool, help="If true, validate the entries against the schema")
def hash(pii_csv, keys, schema, clk_json, quiet, no_header, check_header, validate):
    """Process data to create CLKs

    Given a file containing CSV data as PII_CSV, and a JSON
    document defining the expected schema, verify the schema, then
    hash the data to create CLKs writing them as JSON to CLK_JSON. Note the CSV
    file should contain a header row - however this row is not used
    by this tool.

    It is important that the keys are only known by the two data providers. Two words should be provided. For example:

    $clkutil hash pii.csv horse staple pii-schema.json clk.json

    Use "-" for CLK_JSON to write JSON to stdout.
    """
    try:
        schema_object = clkhash.schema.from_json_file(schema_file=schema)
    except SchemaError as e:
        log(str(e))
        raise SystemExit(-1)
    header = True
    if not check_header:
        header = 'ignore'
    if no_header:
        header = False

    try:
        clk_data = clk.generate_clk_from_csv(
            pii_csv, keys, schema_object,
            validate=validate,
            header=header,
            progress_bar=not quiet)
    except (validate_data.EntryError, validate_data.FormatError) as e:
        msg, = e.args
        log(msg)
        log('Hashing failed.')
    else:
        json.dump({'clks': clk_data}, clk_json)
        if hasattr(clk_json, 'name'):
            log("CLK data written to {}".format(clk_json.name))


@cli.command('status', short_help='get status of entity service')
@click.option('--server', type=str, default=DEFAULT_SERVICE_URL, help="Server address including protocol")
@click.option('-o', '--output', type=click.File('w'), default='-')
@click.option('-v', '--verbose', default=False, is_flag=True, help="Script is more talkative")
@click.option('--client_retrying_wait_exponential_multiplier_ms',
              default=ClientWaitingConfiguration.DEFAULT_WAIT_EXPONENTIAL_MULTIPLIER_MS,
              type=int, help="Configuration about retrying a request if the client receives a 503 response."
                             " See https://pypi.org/project/retrying/ for more documentation.")
@click.option('--client_retrying_wait_exponential_max_ms',
              default=ClientWaitingConfiguration.DEFAULT_WAIT_EXPONENTIAL_MAX_MS,
              type=int, help="Configuration about retrying a request if the client receives a 503 response."
                             " See https://pypi.org/project/retrying/ for more documentation.")
@click.option('--client_retrying_stop_max_delay_ms',
              default=ClientWaitingConfiguration.DEFAULT_STOP_MAX_DELAY_MS,
              type=int, help="Configuration about retrying a request if the client receives a 503 response."
                             " See https://pypi.org/project/retrying/ for more documentation.")
def status(server, output, verbose, client_retrying_wait_exponential_multiplier_ms,
           client_retrying_wait_exponential_max_ms, client_retrying_stop_max_delay_ms):
    """Connect to an entity matching server and check the service status.

    Use "-" to output status to stdout.
    """
    if verbose:
        log("Connecting to Entity Matching Server: {}".format(server))

    client_waiting_configuration = ClientWaitingConfiguration(client_retrying_wait_exponential_multiplier_ms,
                                                              client_retrying_wait_exponential_max_ms,
                                                              client_retrying_stop_max_delay_ms)
    rest_client = RestClient(server, client_waiting_configuration)
    service_status = rest_client.server_get_status()
    if verbose:
        log("Status: {}".format(service_status['status']))
    print(json.dumps(service_status), file=output)


MAPPING_CREATED_MSG = """
The generated tokens can be used to upload hashed data and
fetch the resulting linkage table from the service.

To upload using the cli tool for entity A:

    clkutil hash a_people.csv key1 key2 schema.json A_HASHED_FILE.json
    clkutil upload --project="{project_id}" --apikey="{update_tokens[0]}"  A_HASHED_FILE.json

To upload using the cli tool for entity B:

    clkutil hash b_people.csv key1 key2 schema.json B_HASHED_FILE.json
    clkutil upload --project="{project_id}" --apikey="{update_tokens[1]}" B_HASHED_FILE.json

After both users have uploaded their data one can watch for and retrieve the results:

    clkutil results -w --project="{project_id}" --run="{run_id}" --apikey="{result_token}" --output results.txt

"""


@cli.command('create-project', short_help="create a linkage project on the entity service")
@click.option('--type', default='permutations',
              type=click.Choice(['mapping', 'permutations',
                                 'similarity_scores', 'groups']),
              help='Protocol/view type for the project.')
@click.option('--schema', type=click.File('r'), help="Schema to publicly share with participating parties.")
@click.option('--server', type=str, default=DEFAULT_SERVICE_URL, help="Server address including protocol")
@click.option('--name', type=str, help="Name to give this project")
@click.option('--parties', default=2, type=int,
              help="Number of parties in the project")
@click.option('-o', '--output', type=click.File('w'), default='-')
@click.option('-v', '--verbose', is_flag=True, help="Script is more talkative")
@click.option('--client_retrying_wait_exponential_multiplier_ms',
              default=ClientWaitingConfiguration.DEFAULT_WAIT_EXPONENTIAL_MULTIPLIER_MS,
              type=int, help="Configuration about retrying a request if the client receives a 503 response."
                             " See https://pypi.org/project/retrying/ for more documentation.")
@click.option('--client_retrying_wait_exponential_max_ms',
              default=ClientWaitingConfiguration.DEFAULT_WAIT_EXPONENTIAL_MAX_MS,
              type=int, help="Configuration about retrying a request if the client receives a 503 response."
                             " See https://pypi.org/project/retrying/ for more documentation.")
@click.option('--client_retrying_stop_max_delay_ms',
              default=ClientWaitingConfiguration.DEFAULT_STOP_MAX_DELAY_MS,
              type=int, help="Configuration about retrying a request if the client receives a 503 response."
                             " See https://pypi.org/project/retrying/ for more documentation.")
def create_project(type, schema, server, name, parties, output, verbose, client_retrying_wait_exponential_multiplier_ms,
                   client_retrying_wait_exponential_max_ms, client_retrying_stop_max_delay_ms):
    """Create a new project on an entity matching server.

    See entity matching service documentation for details on mapping type and schema
    Returns authentication details for the created project.
    """
    if verbose:
        log("Entity Matching Server: {}".format(server))

    if schema is not None:
        schema_json = json.load(schema)
        # Validate the schema
        clkhash.schema.validate_schema_dict(schema_json)
    else:
        raise ValueError("Schema must be provided when creating new linkage project")

    if parties > 2 and type != 'groups':
        raise ValueError("Multi-party linkage requires result type 'groups'")

    name = name if name is not None else ''

    # Creating new project
    try:
        client_waiting_configuration = ClientWaitingConfiguration(client_retrying_wait_exponential_multiplier_ms,
                                                                  client_retrying_wait_exponential_max_ms,
                                                                  client_retrying_stop_max_delay_ms)
        rest_client = RestClient(server, client_waiting_configuration)
        project_creation_reply = rest_client.project_create(
            schema_json, type, name, parties=parties)
    except ServiceError as e:
        log("Unexpected response - {}".format(e.status_code))
        log(e.text)
        raise SystemExit(-1)
    else:
        log("Project created")

    json.dump(project_creation_reply, output)


@cli.command('create', short_help="create a run on the entity service")
@click.option('--server', type=str, default=DEFAULT_SERVICE_URL, help="Server address including protocol")
@click.option('--name', type=str, help="Name to give this run", default='')
@click.option('--project', help='Project identifier')
@click.option('--apikey', type=str, help="Project Authorization Token")
@click.option('-o', '--output', type=click.File('w'), default='-')
@click.option('-t', '--threshold', type=float)
@click.option('-v', '--verbose', default=False, is_flag=True, help="Script is more talkative")
@click.option('--client_retrying_wait_exponential_multiplier_ms',
              default=ClientWaitingConfiguration.DEFAULT_WAIT_EXPONENTIAL_MULTIPLIER_MS,
              type=int, help="Configuration about retrying a request if the client receives a 503 response."
                             " See https://pypi.org/project/retrying/ for more documentation.")
@click.option('--client_retrying_wait_exponential_max_ms',
              default=ClientWaitingConfiguration.DEFAULT_WAIT_EXPONENTIAL_MAX_MS,
              type=int, help="Configuration about retrying a request if the client receives a 503 response."
                             " See https://pypi.org/project/retrying/ for more documentation.")
@click.option('--client_retrying_stop_max_delay_ms',
              default=ClientWaitingConfiguration.DEFAULT_STOP_MAX_DELAY_MS,
              type=int, help="Configuration about retrying a request if the client receives a 503 response."
                             " See https://pypi.org/project/retrying/ for more documentation.")
def create(server, name, project, apikey, output, threshold, verbose, client_retrying_wait_exponential_multiplier_ms,
           client_retrying_wait_exponential_max_ms, client_retrying_stop_max_delay_ms):
    """Create a new run on an entity matching server.

    See entity matching service documentation for details on threshold.

    Returns details for the created run.
    """
    if verbose:
        log("Entity Matching Server: {}".format(server))

    if threshold is None:
        raise ValueError("Please provide a threshold")

    # Create a new run
    try:
        client_waiting_configuration = ClientWaitingConfiguration(client_retrying_wait_exponential_multiplier_ms,
                                                                  client_retrying_wait_exponential_max_ms,
                                                                  client_retrying_stop_max_delay_ms)
        rest_client = RestClient(server, client_waiting_configuration)
        response = rest_client.run_create(project, apikey, threshold, name)
    except ServiceError as e:
        log("Unexpected response with status {}".format(e.status_code))
        log(e.text)
    else:
        json.dump(response, output)


@cli.command('upload', short_help='upload hashes to entity service')
@click.argument('clk_json', type=click.File('r'))
@click.option('--project', help='Project identifier')
@click.option('--apikey', help='Authentication API key for the server.')
@click.option('--server', type=str, default=DEFAULT_SERVICE_URL, help="Server address including protocol")
@click.option('-o', '--output', type=click.File('w'), default='-')
@click.option('-v', '--verbose', default=False, is_flag=True, help="Script is more talkative")
@click.option('--client_retrying_wait_exponential_multiplier_ms',
              default=ClientWaitingConfiguration.DEFAULT_WAIT_EXPONENTIAL_MULTIPLIER_MS,
              type=int, help="Configuration about retrying a request if the client receives a 503 response."
                             " See https://pypi.org/project/retrying/ for more documentation.")
@click.option('--client_retrying_wait_exponential_max_ms',
              default=ClientWaitingConfiguration.DEFAULT_WAIT_EXPONENTIAL_MAX_MS,
              type=int, help="Configuration about retrying a request if the client receives a 503 response."
                             " See https://pypi.org/project/retrying/ for more documentation.")
@click.option('--client_retrying_stop_max_delay_ms',
              default=ClientWaitingConfiguration.DEFAULT_STOP_MAX_DELAY_MS,
              type=int, help="Configuration about retrying a request if the client receives a 503 response."
                             " See https://pypi.org/project/retrying/ for more documentation.")
def upload(clk_json, project, apikey, server, output, verbose, client_retrying_wait_exponential_multiplier_ms,
           client_retrying_wait_exponential_max_ms, client_retrying_stop_max_delay_ms):
    """Upload CLK data to entity matching server.

    Given a json file containing hashed clk data as CLK_JSON, upload to
    the entity resolution service.

    Use "-" to read from stdin.
    """
    if verbose:
        log("Uploading CLK data from {}".format(clk_json.name))
        log("To Entity Matching Server: {}".format(server))
        log("Project ID: {}".format(project))
        log("Uploading CLK data to the server")

    client_waiting_configuration = ClientWaitingConfiguration(client_retrying_wait_exponential_multiplier_ms,
                                                              client_retrying_wait_exponential_max_ms,
                                                              client_retrying_stop_max_delay_ms)
    rest_client = RestClient(server, client_waiting_configuration)
    response = rest_client.project_upload_clks(project, apikey, clk_json)

    if verbose:
        log(response)

    json.dump(response, output)


@cli.command('results', short_help="fetch results from entity service")
@click.option('--project', help='Project identifier')
@click.option('--apikey', help='Authentication API key for the server.')
@click.option('--run', help='Run ID to get results for')
@click.option('-w', '--watch', help='Follow/wait until results are available', is_flag=True)
@click.option('--server', type=str, default=DEFAULT_SERVICE_URL, help="Server address including protocol")
@click.option('-o', '--output', type=click.File('w'), default='-')
@click.option('--client_retrying_wait_exponential_multiplier_ms',
              default=ClientWaitingConfiguration.DEFAULT_WAIT_EXPONENTIAL_MULTIPLIER_MS,
              type=int, help="Configuration about retrying a request if the client receives a 503 response."
                             " See https://pypi.org/project/retrying/ for more documentation.")
@click.option('--client_retrying_wait_exponential_max_ms',
              default=ClientWaitingConfiguration.DEFAULT_WAIT_EXPONENTIAL_MAX_MS,
              type=int, help="Configuration about retrying a request if the client receives a 503 response."
                             " See https://pypi.org/project/retrying/ for more documentation.")
@click.option('--client_retrying_stop_max_delay_ms',
              default=ClientWaitingConfiguration.DEFAULT_STOP_MAX_DELAY_MS,
              type=int, help="Configuration about retrying a request if the client receives a 503 response."
                             " See https://pypi.org/project/retrying/ for more documentation.")
def results(project, apikey, run, watch, server, output, client_retrying_wait_exponential_multiplier_ms,
            client_retrying_wait_exponential_max_ms, client_retrying_stop_max_delay_ms):
    """
    Check to see if results are available for a particular mapping
    and if so download.

    Authentication is carried out using the --apikey option which
    must be provided. Depending on the server operating mode this
    may return a mask, a linkage table, or a permutation. Consult
    the entity service documentation for details.
    """

    client_waiting_configuration = ClientWaitingConfiguration(client_retrying_wait_exponential_multiplier_ms,
                                                              client_retrying_wait_exponential_max_ms,
                                                              client_retrying_stop_max_delay_ms)
    rest_client = RestClient(server, client_waiting_configuration)
    status = rest_client.run_get_status(project, run, apikey)
    log(format_run_status(status))
    if watch:
        for status in rest_client.watch_run_status(project, run, apikey, 24*60*60):
            log(format_run_status(status))

    if status['state'] == 'completed':
        log("Downloading result")
        response = rest_client.run_get_result_text(project, run, apikey)
        log("Received result")
        print(response, file=output)
    elif status['state'] == 'error':
        log("There was an error")
        error_result = rest_client.run_get_result_text(project, run, apikey)
        print(error_result, file=output)
    else:
        log("No result yet")


@cli.command('delete', short_help="delete a run on the anonlink entity service")
@click.option('--server', type=str, default=DEFAULT_SERVICE_URL, help="Server address including protocol")
@click.option('--project', help='Project identifier')
@click.option('--run', help='Run ID to delete')
@click.option('--apikey', type=str, help="Project Authorization Token")
@click.option('-v', '--verbose', default=False, is_flag=True, help="Script is more talkative")
@click.option('--client_retrying_wait_exponential_multiplier_ms',
              default=ClientWaitingConfiguration.DEFAULT_WAIT_EXPONENTIAL_MULTIPLIER_MS,
              type=int, help="Configuration about retrying a request if the client receives a 503 response."
                             " See https://pypi.org/project/retrying/ for more documentation.")
@click.option('--client_retrying_wait_exponential_max_ms',
              default=ClientWaitingConfiguration.DEFAULT_WAIT_EXPONENTIAL_MAX_MS,
              type=int, help="Configuration about retrying a request if the client receives a 503 response."
                             " See https://pypi.org/project/retrying/ for more documentation.")
@click.option('--client_retrying_stop_max_delay_ms',
              default=ClientWaitingConfiguration.DEFAULT_STOP_MAX_DELAY_MS,
              type=int, help="Configuration about retrying a request if the client receives a 503 response."
                             " See https://pypi.org/project/retrying/ for more documentation.")
def delete(server, project, run, apikey, verbose, client_retrying_wait_exponential_multiplier_ms,
           client_retrying_wait_exponential_max_ms, client_retrying_stop_max_delay_ms):
    """Delete a run on an entity matching server.
    """
    if verbose:
        log("Entity Matching Server: {}".format(server))

    client_waiting_configuration = ClientWaitingConfiguration(client_retrying_wait_exponential_multiplier_ms,
                                                              client_retrying_wait_exponential_max_ms,
                                                              client_retrying_stop_max_delay_ms)
    rest_client = RestClient(server, client_waiting_configuration)

    # Delete a run
    try:
        msg = rest_client.run_delete(project, run, apikey)
        if verbose:
            log(msg)
    except ServiceError as e:
        log("Unexpected response with status {}".format(e.status_code))
        log(e.text)
    else:
        log("Run deleted")


@cli.command('delete-project', short_help="delete a project on the anonlink entity service")
@click.option('--server', type=str, default=DEFAULT_SERVICE_URL, help="Server address including protocol")
@click.option('--project', help='Project identifier')
@click.option('--apikey', type=str, help="Project Authorization Token")
@click.option('-v', '--verbose', default=False, is_flag=True, help="Script is more talkative")
@click.option('--client_retrying_wait_exponential_multiplier_ms',
              default=ClientWaitingConfiguration.DEFAULT_WAIT_EXPONENTIAL_MULTIPLIER_MS,
              type=int, help="Configuration about retrying a request if the client receives a 503 response."
                             " See https://pypi.org/project/retrying/ for more documentation.")
@click.option('--client_retrying_wait_exponential_max_ms',
              default=ClientWaitingConfiguration.DEFAULT_WAIT_EXPONENTIAL_MAX_MS,
              type=int, help="Configuration about retrying a request if the client receives a 503 response."
                             " See https://pypi.org/project/retrying/ for more documentation.")
@click.option('--client_retrying_stop_max_delay_ms',
              default=ClientWaitingConfiguration.DEFAULT_STOP_MAX_DELAY_MS,
              type=int, help="Configuration about retrying a request if the client receives a 503 response."
                             " See https://pypi.org/project/retrying/ for more documentation.")
def delete_project(server, project, apikey, verbose, client_retrying_wait_exponential_multiplier_ms,
                   client_retrying_wait_exponential_max_ms, client_retrying_stop_max_delay_ms):
    """Delete a project on an entity matching server.
    """
    if verbose:
        log("Entity Matching Server: {}".format(server))

    client_waiting_configuration = ClientWaitingConfiguration(client_retrying_wait_exponential_multiplier_ms,
                                                              client_retrying_wait_exponential_max_ms,
                                                              client_retrying_stop_max_delay_ms)
    rest_client = RestClient(server, client_waiting_configuration)

    try:
        rest_client.project_delete(project, apikey)
    except ServiceError as e:
        log("Unexpected response with status {}".format(e.status_code))
        log(e.text)
    else:
        log("Project deleted")


@cli.command('benchmark', short_help='carry out a local benchmark')
def benchmark():
    bench.compute_hash_speed(10000)


@cli.command('describe', short_help='show distribution of clk popcounts')
@click.argument('clk_json', type=click.File('r'))
def describe(clk_json):
    """show distribution of clk's popcounts
    """
    descr.plot(clk_json)


@cli.command('generate', short_help='generate random pii data for testing')
@click.argument('size', type=int, default=100)
@click.argument('output', type=click.File('w'))
@click.option('--schema', '-s', type=click.File('r'), default=None)
def generate(size, output, schema):
    """Generate fake PII data for testing"""
    pii_data = randomnames.NameList(size)

    if schema is not None:
        raise NotImplementedError

    randomnames.save_csv(
        pii_data.names,
        [f.identifier for f in pii_data.SCHEMA.fields],
        output)


@cli.command('generate-default-schema',
             short_help='get the default schema used in generated random PII')
@click.argument('output', type=click.Path(writable=True,
                                          readable=False,
                                          resolve_path=True))
def generate_default_schema(output):
    """Get default schema for fake PII"""
    original_path = os.path.join(os.path.dirname(__file__),
                                 'data',
                                 'randomnames-schema.json')
    shutil.copyfile(original_path, output)


@cli.command('validate-schema', short_help="validate linkage schema")
@click.argument('schema', type=click.File('r', lazy=True))
def validate_schema(schema):
    """Validate a linkage schema

    Given a file containing a linkage schema, verify the schema is valid otherwise
    print detailed errors.
    """

    try:
        clkhash.schema.from_json_file(
            schema_file=schema,
            validate=True
        )

        log("schema is valid", color='green')

    except SchemaError as e:
        log(str(e))
        raise SystemExit(-1)


if __name__ == "__main__":
    freeze_support()
    cli()
