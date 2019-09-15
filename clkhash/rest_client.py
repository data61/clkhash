import time

import requests
import clkhash
from clkhash.backports import TimeoutError
import logging
from retrying import retry

logger = logging.getLogger(__name__)


class ClientWaitingConfiguration:
    DEFAULT_WAIT_EXPONENTIAL_MULTIPLIER_MS = 100
    DEFAULT_WAIT_EXPONENTIAL_MAX_MS = 10000
    DEFAULT_STOP_MAX_DELAY_MS = 20000

    def __init__(self, wait_exponential_multiplier_ms=DEFAULT_WAIT_EXPONENTIAL_MAX_MS,
                 wait_exponential_max_ms=DEFAULT_WAIT_EXPONENTIAL_MAX_MS,
                 stop_max_delay_ms=DEFAULT_STOP_MAX_DELAY_MS):
        self.wait_exponential_multiplier_ms = wait_exponential_multiplier_ms
        self.wait_exponential_max_ms = wait_exponential_max_ms
        self.stop_max_delay_ms = stop_max_delay_ms


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


def _is_rate_limited_error(exception):
    """Return True if we should retry (in this case when it's a RateLimitedClient), False otherwise"""
    return isinstance(exception, RateLimitedClient)


def _handle_json_response(response, failure_message, expected_status_code=200):
    if response.status_code != expected_status_code:
        raise ServiceError(failure_message, response)
    try:
        return response.json()
    except ValueError:
        raise ServiceError(failure_message, response)


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


class RestClient:

    def __init__(self, server, client_waiting_configuration=None):
        self.server = server
        if client_waiting_configuration is None:
            self.client_waiting_configuration = ClientWaitingConfiguration()
        else:
            self.client_waiting_configuration = client_waiting_configuration

    def __request_wrapper(self, request_method, url, **kwargs):
        """
        Return a requests Response object, but will retry the same request as long as the server returns a 503 response and
        the maximum delayed has not been exceeded.
        The delay between requests will increase exponentially up to a threshold, from which it stays constant. The delay is:
        2^x * WAIT_EXPONENTIAL_MULTIPLIER_MS milliseconds between each retry, up to WAIT_EXPONENTIAL_MAX_MS milliseconds,
        then it stays at WAIT_EXPONENTIAL_MAX_MS milliseconds afterwards."
        """

        @retry(wait_exponential_multiplier=self.client_waiting_configuration.wait_exponential_multiplier_ms,
               wait_exponential_max=self.client_waiting_configuration.wait_exponential_max_ms,
               stop_max_delay=self.client_waiting_configuration.stop_max_delay_ms,
               retry_on_exception=_is_rate_limited_error)
        def wrapper():
            # The parameter 'data' should be a File (as coming from click.File) or a string (the direct data).
            # If it is a file, we need to reposition the reading pointer to the beginning of the file
            # if we are retrying to post. Otherwise, we send no data or missing data.
            # If this is not file, we don't need to do anything.
            if 'data' in kwargs and hasattr(kwargs['data'], 'seek'):
                kwargs['data'].seek(0, 0)
            response = requests.request(request_method, url, **kwargs)
            if response.status_code == 503:
                raise RateLimitedClient('Client is rate limited. Try requesting less frequently.', response)
            return response

        return wrapper()

    def server_get_status(self):
        response = self.__request_wrapper('get', self.server + "/api/v1/status")
        return _handle_json_response(response, "Error with service status")

    def project_create(self, schema, result_type, name, notes=None, parties=2):
        if notes is None:
            notes = 'Project created by clkhash version {}'.format(clkhash.__version__)

        response = self.__request_wrapper(
            'post',
            "{}/api/v1/projects".format(self.server),
            json={
                'schema': schema,
                'result_type': result_type,
                'number_parties': parties,
                'name': name,
                'notes': notes
            }
        )
        return _handle_json_response(response, "Error creating project", 201)

    def project_delete(self, project, apikey):
        response = self.__request_wrapper(
            'delete',
            '{}/api/v1/projects/{}'.format(self.server, project),
            headers={"Authorization": apikey}
        )
        if response.status_code != 204:
            raise ServiceError("Error deleting project", response)

    def project_get_description(self, project, apikey):
        response = self.__request_wrapper(
            'get',
            '{}/api/v1/projects/{}'.format(self.server, project),
            headers={
                "Authorization": apikey,
                'content-type': 'application/json'
            }
        )
        return _handle_json_response(response, "Error getting project description", 200)

    def project_upload_clks(self, project, apikey, clk_data):
        response = self.__request_wrapper(
            'post',
            '{}/api/v1/projects/{}/clks'.format(self.server, project),
            data=clk_data,
            headers={
                "Authorization": apikey,
                'content-type': 'application/json'
            }
        )
        return _handle_json_response(response, "Error uploading CLKS to project", 201)

    def run_create(self, project_id, apikey, threshold, name, notes=None):
        if notes is None:
            notes = 'Run created by clkhash {}'.format(clkhash.__version__)

        response = self.__request_wrapper(
            'post',
            "{}/api/v1/projects/{}/runs".format(self.server, project_id),
            headers={"Authorization": apikey},
            json={
                'threshold': threshold,
                'name': name,
                'notes': notes
            }
        )
        return _handle_json_response(response, "Unexpected response while creating run", 201)

    def run_get_status(self, project, run, apikey):
        response = self.__request_wrapper(
            'get',
            '{}/api/v1/projects/{}/runs/{}/status'.format(self.server, project, run),
            headers={"Authorization": apikey}
        )
        return _handle_json_response(response, "Run Status Error", 200)

    def wait_for_run(self, project, run, apikey, timeout=None, update_period=1):
        """
        Monitor a linkage run and return the final status updates. If a timeout is provided and the
        run hasn't entered a terminal state (error or completed) when the timeout is reached a
        TimeoutError will be raised.

        :param project:
        :param run:
        :param apikey:
        :param timeout: Stop waiting after this many seconds. The default (None) is to never give you up.
        :param update_period: Time in seconds between queries to the run's status.
        :raises TimeoutError: if timeout is reached
        """
        for status in self.watch_run_status(project, run, apikey, timeout, update_period):
            pass
        return status

    def watch_run_status(self, project, run, apikey, timeout=None, update_period=1):
        """
        Monitor a linkage run and yield status updates. Will immediately yield an update and then
        only yield further updates when the status object changes. If a timeout is provided and the
        run hasn't entered a terminal state (error or completed) when the timeout is reached,
        updates will cease and a TimeoutError will be raised.

        :param project:
        :param run:
        :param apikey:
        :param timeout: Stop waiting after this many seconds. The default (None) is to never give you up.
        :param update_period: Time in seconds between queries to the run's status.
        :raises TimeoutError: if timeout is reached
        """
        start_time = time.time()
        status = old_status = self.run_get_status(project, run, apikey)
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
                status = self.run_get_status(project, run, apikey)
            except RateLimitedClient:
                # Rare case with the default parameters but could occur: if the `retry` has continuously received 503
                # responses up to its timeout, it will stop retrying and raise the last received exception, i.e. a
                # RateLimitedException.
                time.sleep(1)
        raise TimeoutError("Timeout exceeded before run {} terminated".format(run))

    def run_get_result_text(self, project, run, apikey):
        response = self.__request_wrapper(
            'get',
            '{}/api/v1/projects/{}/runs/{}/result'.format(self.server, project, run),
            headers={"Authorization": apikey}
        )
        if response.status_code != 200:
            raise ServiceError("Error retrieving results", response)
        return response.text

    def run_delete(self, project, run, apikey):
        response = self.__request_wrapper(
            'delete',
            '{}/api/v1/projects/{}/runs/{}'.format(self.server, project, run),
            headers={"Authorization": apikey}
        )
        if response.status_code not in (200, 204):
            raise ServiceError("Error deleting run", response)
        return response.text
