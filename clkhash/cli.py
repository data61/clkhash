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
from clkhash.schema import SchemaError, validate_schema_dict, convert_to_latest_version
from clkhash.backports import raise_from

from typing import List, Callable

DEFAULT_SERVICE_URL = 'https://testing.es.data61.xyz'

# Labels for some options. If changed here, the name of the corresponding attributes MUST be changed in the methods
# using them.
VERBOSE_LABEL = 'verbose'
REST_CLIENT_LABEL = 'rest_client'
SERVER_LABEL = 'server'
RETRY_MULTIPLIER_LABEL = 'retry_multiplier'
RETRY_MAX_EXP_LABEL = 'retry_max_exp'
RETRY_STOP_LABEL = 'retry_stop'


def log(m, color='red'):
    click.echo(click.style(m, fg=color), err=True)


def set_verbosity(ctx, param, value):
    """
    verbose_option callback

    Set the script verbosity in the click context object which is assumed to be a dictionary.
    Note that if the verbosity is set to true, it cannot be brought back to false in the current context.
    """
    if ctx.obj is None or not ctx.obj.get(VERBOSE_LABEL):
        ctx.obj = {VERBOSE_LABEL: value}
    verbosity = ctx.obj.get(VERBOSE_LABEL)
    return verbosity


# This option will be used as an annotation of a command. If used, the command will have this option, which will
# automatically set the verbosity of the script. Note that the verbosity is global (set in the context), so the commands
#     clkutil -v status [...]
# is equivalent to
#     clkutil status -v [...]
verbose_option = click.option('-v', '--verbose', VERBOSE_LABEL, default=False, is_flag=True,
                              help="Script is more talkative", callback=set_verbosity)

# Set of options required for all the commands sending a request to the entity service server.
rest_client_option = [
    click.option('--server', SERVER_LABEL, type=str, default=DEFAULT_SERVICE_URL,
                 help="Server address including protocol. Default {}.".format(DEFAULT_SERVICE_URL)),
    click.option('--retry-multiplier', RETRY_MULTIPLIER_LABEL,
                 default=ClientWaitingConfiguration.DEFAULT_WAIT_EXPONENTIAL_MULTIPLIER_MS,
                 type=int, help="<milliseconds> If receives a 503 from server, minimum waiting time before retrying. "
                                "Default {}.".format(ClientWaitingConfiguration.DEFAULT_WAIT_EXPONENTIAL_MULTIPLIER_MS)),
    click.option('--retry-exponential-max', RETRY_MAX_EXP_LABEL,
                 default=ClientWaitingConfiguration.DEFAULT_WAIT_EXPONENTIAL_MAX_MS,
                 type=int, help="<milliseconds> If receives a 503 from server, maximum time interval between retries. "
                                "Default {}.".format(ClientWaitingConfiguration.DEFAULT_WAIT_EXPONENTIAL_MAX_MS)),
    click.option('--retry-max-time', RETRY_STOP_LABEL,
                 default=ClientWaitingConfiguration.DEFAULT_STOP_MAX_DELAY_MS,
                 type=int, help="<milliseconds> If receives a 503 from server, retry only within this period. "
                                "Default {}.".format(ClientWaitingConfiguration.DEFAULT_STOP_MAX_DELAY_MS))
]


def add_options(options):
    # type: (List[Callable]) -> Callable
    """
    Used as an annotation for click commands.
    Allow to add a list of options to the command
    From https://stackoverflow.com/questions/40182157/python-click-shared-options-and-flags-between-commands

    :param options: List of options to add to the command
    """
    def _add_options(func):
        for option in reversed(options):
            func = option(func)
        return func

    return _add_options


def is_verbose(ctx):
    """
    Use the click context to get the verbosity of the script.
    Should have been set by the method set_verbosity.
    :param ctx:
    :return: None if not set, otherwise a boolean.
    """
    return ctx.obj.get(VERBOSE_LABEL)


def create_rest_client(server, retry_multiplier, retry_max_exp, retry_stop, verbose):
    """
    Create a RestClient with retry config set from command line options.
    """
    if verbose:
        log("Connecting to Entity Matching Server: {}".format(server))
    retry_config = ClientWaitingConfiguration(retry_multiplier, retry_max_exp, retry_stop)
    return RestClient(server, retry_config)


@click.group("clkutil")
@click.version_option(clkhash.__version__)
@verbose_option
def cli(verbose):
    """
    This command line application allows a user to hash their
    data into cryptographic longterm keys for use in
    private comparison.

    This tool can also interact with a entity matching service;
    creating new mappings, uploading locally hashed data,
    watching progress, and retrieving results.

    Example:

        clkutil hash private_data.csv secret schema.json output-clks.json


    All rights reserved Confidential Computing 2016.
    """


@cli.command('hash', short_help="generate hashes from local PII data")
@click.argument('pii_csv', type=click.File('r'))
@click.argument('secret', type=str)
@click.argument('schema', type=click.File('r', lazy=True))
@click.argument('clk_json', type=click.File('w'))
@click.option('--no-header', default=False, is_flag=True, help="Don't skip the first row")
@click.option('--check-header', default=True, type=bool, help="If true, check the header against the schema")
@click.option('--validate', default=True, type=bool, help="If true, validate the entries against the schema")
@verbose_option
def hash(pii_csv, secret, schema, clk_json, no_header, check_header, validate, verbose):
    """Process data to create CLKs

    Given a file containing CSV data as PII_CSV, and a JSON
    document defining the expected schema, verify the schema, then
    hash the data to create CLKs writing them as JSON to CLK_JSON. Note the CSV
    file should contain a header row - however this row is not used
    by this tool.

    It is important that the secret is only known by the two data providers. One word must be provided. For example:

    $clkutil hash pii.csv horse-staple pii-schema.json clk.json

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
            pii_csv, secret, schema_object,
            validate=validate,
            header=header,
            progress_bar=verbose)
    except (validate_data.EntryError, validate_data.FormatError) as e:
        msg, = e.args
        log(msg)
        log('Hashing failed.')
    else:
        json.dump({'clks': clk_data}, clk_json)
        if hasattr(clk_json, 'name'):
            log("CLK data written to {}".format(clk_json.name))


@cli.command('status', short_help='get status of entity service')
@click.option('-o', '--output', type=click.File('w'), default='-')
@add_options(rest_client_option)
@verbose_option
def status(output, server, retry_multiplier, retry_max_exp, retry_stop, verbose):
    """Connect to an entity matching server and check the service status.

    Use "-" to output status to stdout.
    """
    rest_client = create_rest_client(server, retry_multiplier, retry_max_exp, retry_stop, verbose)
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
              type=click.Choice(['permutations',
                                 'similarity_scores', 'groups']),
              help='Protocol/view type for the project.')
@click.option('--schema', type=click.File('r'), help="Schema to publicly share with participating parties.")
@click.option('--name', type=str, help="Name to give this project")
@click.option('--parties', default=2, type=int,
              help="Number of parties in the project")
@click.option('-o', '--output', type=click.File('w'), default='-')
@add_options(rest_client_option)
@verbose_option
def create_project(type, schema, name, parties, output, server, retry_multiplier, retry_max_exp,
                   retry_stop, verbose):
    """Create a new project on an entity matching server.

    See entity matching service documentation for details on mapping type and schema
    Returns authentication details for the created project.
    """

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
        rest_client = create_rest_client(server, retry_multiplier, retry_max_exp, retry_stop, verbose)
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
@click.option('--name', type=str, help="Name to give this run", default='')
@click.option('--project', help='Project identifier')
@click.option('--apikey', type=str, help="Project Authorization Token")
@click.option('-o', '--output', type=click.File('w'), default='-')
@click.option('-t', '--threshold', type=float)
@add_options(rest_client_option)
@verbose_option
def create(name, project, apikey, output, threshold, server, retry_multiplier, retry_max_exp, retry_stop, verbose):
    """Create a new run on an entity matching server.

    See entity matching service documentation for details on threshold.

    Returns details for the created run.
    """
    if threshold is None:
        raise ValueError("Please provide a threshold")

    # Create a new run
    try:
        rest_client = create_rest_client(server, retry_multiplier, retry_max_exp, retry_stop, verbose)
        response = rest_client.run_create(project, apikey, threshold, name)
    except ServiceError as e:
        log("Unexpected response with status {}".format(e.status_code))
        log(e.text)
    else:
        json.dump(response, output)


@cli.command('upload', short_help='upload hashes to entity service')
@click.argument('clk_json', type=click.File('rb'))
@click.option('--project', help='Project identifier')
@click.option('--apikey', help='Authentication API key for the server.')
@click.option('-o', '--output', type=click.File('w'), default='-')
@add_options(rest_client_option)
@verbose_option
def upload(clk_json, project, apikey, output, server, retry_multiplier, retry_max_exp, retry_stop, verbose):
    """Upload CLK data to entity matching server.

    Given a json file containing hashed clk data as CLK_JSON, upload to
    the entity resolution service.

    Use "-" to read from stdin.
    """
    if verbose:
        log("Uploading CLK data from {}".format(clk_json.name))
        log("Project ID: {}".format(project))
        log("Uploading CLK data to the server")
    rest_client = create_rest_client(server, retry_multiplier, retry_max_exp, retry_stop, verbose)
    response = rest_client.project_upload_clks(project, apikey, clk_json)

    if verbose:
        log(response)

    json.dump(response, output)


@cli.command('results', short_help="fetch results from entity service")
@click.option('--project', help='Project identifier')
@click.option('--apikey', help='Authentication API key for the server.')
@click.option('--run', help='Run ID to get results for')
@click.option('-w', '--watch', help='Follow/wait until results are available', is_flag=True)
@click.option('-o', '--output', type=click.File('w'), default='-')
@add_options(rest_client_option)
@verbose_option
def results(project, apikey, run, watch, output, server, retry_multiplier, retry_max_exp, retry_stop, verbose):
    """
    Check to see if results are available for a particular run
    and if so download.

    Authentication is carried out using the --apikey option which
    must be provided. Depending on the server operating mode this
    may return a mask, a linkage table, or a permutation. Consult
    the entity service documentation for details.
    """
    rest_client = create_rest_client(server, retry_multiplier, retry_max_exp, retry_stop, verbose)
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
@click.option('--project', help='Project identifier')
@click.option('--run', help='Run ID to delete')
@click.option('--apikey', type=str, help="Project Authorization Token")
@add_options(rest_client_option)
@verbose_option
def delete(project, run, apikey, server, retry_multiplier, retry_max_exp, retry_stop, verbose):
    """Delete a run on an entity matching server.
    """
    # Delete a run
    try:
        rest_client = create_rest_client(server, retry_multiplier, retry_max_exp, retry_stop, verbose)
        msg = rest_client.run_delete(project, run, apikey)
        if verbose:
            log(msg)
    except ServiceError as e:
        log("Unexpected response with status {}".format(e.status_code))
        log(e.text)
    else:
        log("Run deleted")


@cli.command('delete-project', short_help="delete a project on the anonlink entity service")
@click.option('--project', help='Project identifier')
@click.option('--apikey', type=str, help="Project Authorization Token")
@add_options(rest_client_option)
@verbose_option
def delete_project(project, apikey, server, retry_multiplier, retry_max_exp, retry_stop, verbose):
    """Delete a project on an entity matching server.
    """
    try:
        rest_client = create_rest_client(server, retry_multiplier, retry_max_exp, retry_stop, verbose)
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


@cli.command('convert-schema', short_help='converts schema file to latest version')
@click.argument('schema_json', type=click.File('r'))
@click.argument('output', type=click.File('w'))
def convert_schema(schema_json, output):
    """convert the given schema file to the latest version.
    """
    try:
        schema_dict = json.load(schema_json)
    except ValueError as e:  # In Python 3 we can be more specific
        # with json.decoder.JSONDecodeError,
        # but that doesn't exist in Python 2.
        msg = 'The provided schema is not a valid JSON file.'
        raise_from(SchemaError(msg), e)
    validate_schema_dict(schema_dict)
    new_schema_dict = convert_to_latest_version(schema_dict, validate_result=True)
    json.dump(new_schema_dict, output)


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
