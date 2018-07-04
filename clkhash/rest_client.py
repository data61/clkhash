import time

import requests
import clkhash
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


def _handle_json_response(response, failure_message, expected_status_code=200):
    if response.status_code == 503:
        raise ServiceError('Client is rate limited. Try requesting less frequently.', response)
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


def wait_for_run(server, project, run, apikey, timeout=300):
    start_time = time.time()
    status = run_get_status(server, project, run, apikey)
    while status['state'] not in {'error', 'completed'} and time.time() - start_time < timeout:
        time.sleep(1)
        status = run_get_status(server, project, run, apikey)
    return status


def watch_run_status(server, project, run, apikey, timeout=300):
    start_time = time.time()
    status = run_get_status(server, project, run, apikey)
    while status['state'] not in {'error', 'completed'} and time.time() - start_time < timeout:
        time.sleep(1)
        status = run_get_status(server, project, run, apikey)
        yield status

    raise StopIteration


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
        status_lines.append("Progress: {:.3f}%".format(status['current_stage']['progress']['relative']))

    return '\n'.join(status_lines)
