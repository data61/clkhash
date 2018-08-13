import time

import requests
import clkhash
from clkhash.backports import TimeoutError
import logging

logger = logging.getLogger(__name__)


class ServiceError(Exception):
    """Problem with the upstream API"""
    def __init__(self, msg, response):
        self.status_code = response.status_code
        self.text = response.text
        super(ServiceError, self).__init__(msg)

    def __str__(self):
        return "{}\nStatus Code: {}\nServer Message:\n{}".format(self.args[0], self.status_code, self.text)


class RateLimitedClient(ServiceError):
    """Exception indicating client is asking for updates too frequently.
    """


def _handle_json_response(response, failure_message, expected_status_code=200):
    if response.status_code == 503:
        raise RateLimitedClient('Client is rate limited. Try requesting less frequently.', response)
    if response.status_code != expected_status_code:
        raise ServiceError(failure_message, response)
    try:
        return response.json()
    except ValueError:
        raise ServiceError(failure_message, response)


def server_get_status(server):
    response = requests.get(server + "/api/v1/status")
    return _handle_json_response(response, "Error with service status")


def project_create(server, schema, result_type, name, notes=None, parties=2):
    if notes is None:
        notes = 'Project created by clkhash version {}'.format(clkhash.__version__)

    response = requests.post(
        "{}/api/v1/projects".format(server),
        json={
            'schema': schema,
            'result_type': result_type,
            'number_parties': parties,
            'name': name,
            'notes': notes
        }
    )
    return _handle_json_response(response, "Error creating project", 201)


def project_delete(server, project, apikey):
    response = requests.delete(
        '{}/api/v1/projects/{}'.format(server, project),
        headers={"Authorization": apikey}
    )
    if response.status_code != 204:
        raise ServiceError("Error deleting project", response)


def project_get_description(server, project, apikey):
    response = requests.get(
        '{}/api/v1/projects/{}'.format(server, project),
        headers={
            "Authorization": apikey,
            'content-type': 'application/json'
        }
    )
    return _handle_json_response(response, "Error getting project description", 200)


def project_upload_clks(server, project, apikey, clk_data):
    response = requests.post(
        '{}/api/v1/projects/{}/clks'.format(server, project),
        data=clk_data,
        headers={
            "Authorization": apikey,
            'content-type': 'application/json'
        }
    )
    return _handle_json_response(response, "Error uploading CLKS to project", 201)


def run_create(server, project_id, apikey, threshold, name, notes=None):
    if notes is None:
        notes = 'Run created by clkhash {}'.format(clkhash.__version__)

    response = requests.post(
        "{}/api/v1/projects/{}/runs".format(server, project_id),
        headers={"Authorization": apikey},
        json={
            'threshold': threshold,
            'name': name,
            'notes': notes
        }
    )
    return _handle_json_response(response, "Unexpected response while creating run", 201)


def run_get_status(server, project, run, apikey):
    response = requests.get(
        '{}/api/v1/projects/{}/runs/{}/status'.format(server, project, run),
        headers={"Authorization": apikey}
    )
    return _handle_json_response(response, "Run Status Error", 200)


def wait_for_run(server, project, run, apikey, timeout=None, update_period=1):
    """
    Monitor a linkage run and return the final status updates. If a timeout is provided and the
    run hasn't entered a terminal state (error or completed) when the timeout is reached a
    TimeoutError will be raised.

    :param server: Base url of the upstream server.
    :param project:
    :param run:
    :param apikey:
    :param timeout: Stop waiting after this many seconds. The default (None) is to never give you up.
    :param update_period: Time in seconds between queries to the run's status.
    :raises TimeoutError
    """
    for status in watch_run_status(server, project, run, apikey, timeout, update_period):
        pass
    return status


def watch_run_status(server, project, run, apikey, timeout=None, update_period=1):
    """
    Monitor a linkage run and yield status updates. Will immediately yield an update and then
    only yield further updates when the status object changes. If a timeout is provided and the
    run hasn't entered a terminal state (error or completed) when the timeout is reached,
    updates will cease and a TimeoutError will be raised.

    :param server: Base url of the upstream server.
    :param project:
    :param run:
    :param apikey:
    :param timeout: Stop waiting after this many seconds. The default (None) is to never give you up.
    :param update_period: Time in seconds between queries to the run's status.
    :raises TimeoutError
    """
    start_time = time.time()
    status = old_status = run_get_status(server, project, run, apikey)
    yield status

    def time_not_up():
        return (
            (timeout is None) or
            (time.time() - start_time < timeout)
        )

    while time_not_up():

        if status['state'] in {'error', 'completed'}:
            # No point continuing as run has entered a terminal state
            yield status
            return

        if old_status != status:
            yield status

        time.sleep(update_period)
        old_status = status
        try:
            status = run_get_status(server, project, run, apikey)
        except RateLimitedClient:
            time.sleep(1)
    raise TimeoutError("Timeout exceeded before run {} terminated".format(run))


def run_get_result_text(server, project, run, apikey):
    response = requests.get(
        '{}/api/v1/projects/{}/runs/{}/result'.format(server, project, run),
        headers={"Authorization": apikey}
    )
    if response.status_code != 200:
        raise ServiceError("Error retrieving results", response)
    return response.text


def run_delete(server, project, run, apikey):
    response = requests.delete(
        '{}/api/v1/projects/{}/runs/{}'.format(server, project, run),
        headers={"Authorization": apikey}
    )
    if response.status_code != 200:
        raise ServiceError("Error deleting run", response)
    return response.text


def format_run_status(status):
    status_lines = [
        "State: {}".format(status['state']),
        "Stage ({}/{}): {}".format(
            status['current_stage']['number'],
            status['stages'],
            status['current_stage']['description'],
        )
    ]

    if 'progress' in status['current_stage']:
        status_lines.append("Progress: {:.2%}".format(status['current_stage']['progress']['relative']))

    return '\n'.join(status_lines)
