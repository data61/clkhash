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


def server_get_status(server):
    response = requests.get(server + "/api/v1/status")
    if response.status_code != 200:
        raise ServiceError("Service Status Error", response)

    return response.json()


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
    if response.status_code != 201:
        raise ServiceError("Error creating project", response)
    # Parse project created response
    return response.json()


def project_upload_clks(server, project, apikey, clk_data):
    response = requests.post(
        '{}/api/v1/projects/{}/clks'.format(server, project),
        data=clk_data,
        headers={
            "Authorization": apikey,
            'content-type': 'application/json'
        }
    )
    if response.status_code != 201:
        raise ServiceError("Error uploading CLKS to project", response)
    return response.json()


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

    if response.status_code != 201:
        raise ServiceError("Unexpected response while creating run", response)

    return response.json()


def run_get_status(server, project, run, apikey):
    response = requests.get(
        '{}/api/v1/projects/{}/runs/{}/status'.format(server, project, run),
        headers={"Authorization": apikey}
    )
    if response.status_code != 200:
        raise ServiceError("Run Status Error", response)
    return response.json()


def run_get_result_text(server, project, run, apikey):
    return requests.get(
        '{}/api/v1/projects/{}/runs/{}/result'.format(server, project, run),
        headers={"Authorization": apikey}
    ).text


def format_run_status(status):
    status_lines = [
        "State: {}".format(status['state']),
        "Stage {} ({}/{})".format(
            status['current_stage']['description'],
            status['current_stage'],
            status['stages']
        )
    ]

    if 'progress' in status['current_stage']:
        status_lines.append("Progress: {:.3f}%".format(status['current_stage']['progress']['relative']))

    return '\n'.join(status_lines)
