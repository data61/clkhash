from __future__ import division, print_function

import json
import os
import unittest

import pytest

import clkhash
from clkhash.backports import TimeoutError
from clkhash.clk import generate_clk_from_csv
from clkhash.rest_client import ServiceError, RestClient, format_run_status, ClientWaitingConfiguration
from tests import (SAMPLE_DATA_PATH_1, SAMPLE_DATA_PATH_2,
                   SAMPLE_DATA_SCHEMA_PATH, SIMPLE_SCHEMA_PATH)


@unittest.skipUnless("TEST_ENTITY_SERVICE" in os.environ,
                     "Set envvar TEST_ENTITY_SERVICE to run. Disabled for "
                     "jenkins")
class TestRestClientInteractionWithService(unittest.TestCase):

    @classmethod
    def setup_class(cls):
        cls.url = os.environ['TEST_ENTITY_SERVICE']

        cls.rest_client = RestClient(cls.url)

        schema_object = clkhash.schema.from_json_file(
            schema_file=open(SAMPLE_DATA_SCHEMA_PATH, 'rt'))
        secret = 'secret'
        cls.clk_data_1 = json.dumps(
            {'clks': generate_clk_from_csv(open(SAMPLE_DATA_PATH_1, 'rt'),
                                           secret, schema_object,
                                           header='ignore')})
        cls.clk_data_2 = json.dumps(
            {'clks': generate_clk_from_csv(open(SAMPLE_DATA_PATH_2, 'rt'),
                                           secret, schema_object,
                                           header='ignore')})
        cls._created_projects = []

    @classmethod
    def teardown_class(cls):
        cls._delete_created_projects()

    @classmethod
    def _delete_created_projects(cls):
        for project in cls._created_projects:
            try:
                cls.rest_client.project_delete(project['project_id'],
                                               project['result_token']
                                               )
            except ServiceError:
                # probably already deleted in the test
                pass

    def _create_project(self, schema=None, result_type='permutations', name='',
                        notes='', parties=2):
        if schema is None:
            schema = json.load(open(SIMPLE_SCHEMA_PATH, 'rt'))
        try:
            response = self.rest_client.project_create(schema, result_type, name,
                                                       notes, parties)
            self._created_projects.append(response)
            return response
        except ServiceError:
            raise

    def test_status(self):
        assert 'status' in self.rest_client.server_get_status()
        assert 'project_count' in self.rest_client.server_get_status()

    def test_project_description_bad_project(self):
        with pytest.raises(ServiceError):
            description = self.rest_client.project_get_description('not-a-valid-project_id',
                                                                   'not_a_result_token')

    def test_project_description(self):
        p = self._create_project(schema={'id': 'test schema'})
        description = self.rest_client.project_get_description(p['project_id'],
                                                               p['result_token'])
        assert 'id' in description['schema']
        assert description['schema']['id'] == 'test schema'

    def test_upload_clks(self):
        schema_object = json.load(open(SAMPLE_DATA_SCHEMA_PATH, 'rt'))
        p = self._create_project(schema=schema_object)
        upload_response = self.rest_client.project_upload_clks(p['project_id'],
                                                               p['update_tokens'][
                                                                   0],
                                                               self.clk_data_1)
        assert 'receipt_token' in upload_response

    def test_project_run(self):
        p = self._create_project()

        p_id = p['project_id']
        upload_response_1 = self.rest_client.project_upload_clks(p_id,
                                                                 p['update_tokens'][
                                                                     0],
                                                                 self.clk_data_1)
        upload_response_2 = self.rest_client.project_upload_clks(p_id,
                                                                 p['update_tokens'][
                                                                     1],
                                                                 self.clk_data_2)

        run_response = self.rest_client.run_create(p_id,
                                                   p['result_token'], 0.999,
                                                   name='clkhash rest client test')
        assert 'run_id' in run_response
        r_id = run_response['run_id']
        with pytest.raises(ServiceError):
            self.rest_client.run_get_status(p_id, 'invalid-run-id',
                                            p['result_token'])
        with pytest.raises(ServiceError):
            self.rest_client.run_get_status(p_id, r_id, 'invalid-token')

        status1 = self.rest_client.run_get_status(p_id, r_id,
                                                  p['result_token'])
        assert 'state' in status1
        assert 'stages' in status1
        print(format_run_status(status1))

        # Check we can watch the run progress this will raise if not
        # completed in 20 seconds
        for status_update in self.rest_client.watch_run_status(p_id, r_id,
                                                               p['result_token'],
                                                               20, 0.5):
            print(format_run_status(status_update))

        # Check that we can still "wait" on a completed run and get a valid
        # status
        status2 = self.rest_client.wait_for_run(p_id, r_id,
                                                p['result_token'], 10)
        assert status2['state'] == 'completed'
        coord_result_raw = self.rest_client.run_get_result_text(p_id,
                                                                r_id,
                                                                p['result_token'])
        coord_result = json.loads(coord_result_raw)
        assert 'mask' in coord_result
        assert len(coord_result['mask']) == 1000
        assert coord_result['mask'].count(1) > 10

        result_a = json.loads(
            self.rest_client.run_get_result_text(p_id, r_id,
                                                 upload_response_1[
                                                     'receipt_token']))
        result_b = json.loads(
            self.rest_client.run_get_result_text(p_id, r_id,
                                                 upload_response_2[
                                                     'receipt_token']))
        assert 'permutation' in result_a
        assert 'rows' in result_a
        assert 1000 == result_b['rows'] == result_a['rows']

        self.rest_client.run_delete(p_id, r_id, p['result_token'])
        self.rest_client.project_delete(p_id, p['result_token'])

    def test_project_run_before_data(self):
        p = self._create_project()

        p_id = p['project_id']
        upload_response_1 = self.rest_client.project_upload_clks(p_id,
                                                                 p['update_tokens'][
                                                                     0],
                                                                 self.clk_data_1)
        run_response = self.rest_client.run_create(p_id,
                                                   p['result_token'], 0.999,
                                                   name='clkhash rest client test')
        with pytest.raises(ServiceError):
            json.loads(self.rest_client.run_get_result_text(p_id,
                                                            run_response['run_id'],
                                                            upload_response_1[
                                                                'receipt_token']))


def test_status_404_raises_service_error(requests_mock):
    rest_client = RestClient('http://testing-es-url')
    requests_mock.get('http://testing-es-url/api/v1/status', status_code=404)
    with pytest.raises(ServiceError):
        rest_client.server_get_status()


def test_status_500_raises_service_error(requests_mock):
    rest_client = RestClient('http://testing-es-url')
    requests_mock.get('http://testing-es-url/api/v1/status', status_code=500)
    with pytest.raises(ServiceError):
        rest_client.server_get_status()


def test_status_invalid_json_raises_service_error(requests_mock):
    rest_client = RestClient('http://testing-es-url')
    requests_mock.get('http://testing-es-url/api/v1/status', status_code=200,
                      text='NOT JSON')
    with pytest.raises(ServiceError):
        rest_client.server_get_status()


def test_status_calls_correct_url(requests_mock):
    rest_client = RestClient('http://testing-es-url')
    requests_mock.get('http://testing-es-url/api/v1/status',
                      json={'status': 'ok'})
    rest_client.server_get_status()
    assert requests_mock.called


def test_create_project_passes_all_data(requests_mock):
    rest_client = RestClient('http://testing-es-url')
    requests_mock.post('http://testing-es-url/api/v1/projects',
                       json={'status': 'ok'}, status_code=201)
    rest_client.project_create({'id': 'schema'},
                               'restype', 'myname', 'mynote', 5)
    posted_data = requests_mock.last_request.json()
    assert all(expected_field in posted_data for expected_field in
               {'schema', 'result_type', 'number_parties', 'name', 'notes'})

    assert posted_data['name'] == 'myname'
    assert posted_data['notes'] == 'mynote'
    assert posted_data['number_parties'] == 5


def test_create_project_default_data(requests_mock):
    rest_client = RestClient('http://testing-es-url')
    requests_mock.post('http://testing-es-url/api/v1/projects',
                       json={'status': 'ok'}, status_code=201)
    rest_client.project_create({'id': 'schema'},
                               'restype', 'myname')
    posted_data = requests_mock.last_request.json()
    assert all(expected_field in posted_data for expected_field in
               {'schema', 'result_type', 'number_parties', 'name', 'notes'})

    assert 'created by clkhash' in posted_data['notes']
    assert posted_data['number_parties'] == 2


def test_create_project_handles_400(requests_mock):
    rest_client = RestClient('http://testing-es-url')
    requests_mock.post('http://testing-es-url/api/v1/projects',
                       json={'title': 'not ok', 'status': 400},
                       status_code=400)

    with pytest.raises(ServiceError):
        rest_client.project_create({'id': 'schema'},
                                   'restype', 'myname', 'mynote')


def test_create_project_handles_503(requests_mock):
    rest_client = RestClient('http://testing-es-url', ClientWaitingConfiguration(wait_exponential_max_ms=10,
                                                                                 wait_exponential_multiplier_ms=1,
                                                                                 stop_max_delay_ms=10))
    requests_mock.post('http://testing-es-url/api/v1/projects', text='',
                       status_code=503)

    with pytest.raises(ServiceError):
        rest_client.project_create({'id': 'schema'},
                                   'restype', 'myname', 'mynote')


def test_watch_run_time_out(requests_mock):
    rest_client = RestClient('http://testing-es-url')
    requests_mock.get(
        'http://testing-es-url/api/v1/projects/pid/runs/rid/status',
        json={'state': 'running'}, status_code=200)

    with pytest.raises(TimeoutError):
        for update in rest_client.watch_run_status('pid', 'rid', 'apikey',
                                                   timeout=0.5,
                                                   update_period=0.01):
            assert update['state'] == 'running'

    assert requests_mock.last_request.headers['Authorization'] == 'apikey'


def test_watch_run_rate_limited(requests_mock):
    rest_client = RestClient('http://testing-es-url', ClientWaitingConfiguration(wait_exponential_max_ms=10,
                                                                                 wait_exponential_multiplier_ms=1,
                                                                                 stop_max_delay_ms=10))
    requests_mock.register_uri(
        'GET',
        'http://testing-es-url/api/v1/projects/pid/runs/rid/status',
        [
            {'json': {'state': 'running'}, 'status_code': 200},
            {'json': {'state': 'running', 'progress': {}}, 'status_code': 200},
            {'text': '', 'status_code': 503},
            {'text': '', 'status_code': 503},
            {'json': {'state': 'running'}, 'status_code': 200},
            {'json': {'state': 'completed'}, 'status_code': 200}
        ]
    )

    for update in rest_client.watch_run_status('pid',
                                               'rid', 'apikey', timeout=None,
                                               update_period=0.01):
        assert update['state'] in {'running', 'completed'}

    assert update['state'] == 'completed'

    assert requests_mock.last_request.headers['Authorization'] == 'apikey'


def test_watch_run_no_repeated_updates(requests_mock):
    rest_client = RestClient('http://testing-es-url')
    requests_mock.register_uri(
        'GET',
        'http://testing-es-url/api/v1/projects/pid/runs/rid/status',
        [
            {'json': {'state': 'running',
                      'current_stage': {'number': 1, 'description': 'A',
                                        'progress': {'relative': 0.4}},
                      'stages': 2}, 'status_code': 200},
            {'json': {'state': 'running',
                      'current_stage': {'number': 1, 'description': 'A',
                                        'progress': {'relative': 0.4}},
                      'stages': 2}, 'status_code': 200},
            {'json': {'state': 'running',
                      'current_stage': {'number': 1, 'description': 'A',
                                        'progress': {'relative': 0.4}},
                      'stages': 2}, 'status_code': 200},
            {'json': {'state': 'running',
                      'current_stage': {'number': 1, 'description': 'A',
                                        'progress': {'relative': 0.8}},
                      'stages': 2}, 'status_code': 200},
            {'json': {'state': 'completed', 'stages': 2}, 'status_code': 200},
        ]
    )

    number_updates = 0
    for update in rest_client.watch_run_status('pid',
                                               'rid', 'apikey', timeout=None,
                                               update_period=0.01):
        assert update['state'] in {'running', 'completed'}
        number_updates += 1

    assert update['state'] == 'completed'
    assert 3 == number_updates


def test_watch_run_server_error(requests_mock):
    rest_client = RestClient('http://testing-es-url')
    requests_mock.register_uri(
        'GET',
        'http://testing-es-url/api/v1/projects/pid/runs/rid/status',
        [
            {'json': {'state': 'running',
                      'current_stage': {'number': 1, 'description': 'A',
                                        'progress': {'relative': 0.4}},
                      'stages': 2}, 'status_code': 200},
            {'json': {'state': 'running',
                      'current_stage': {'number': 1, 'description': 'A',
                                        'progress': {'relative': 0.8}},
                      'stages': 2}, 'status_code': 200},
            {'text': 'SERVER ERROR', 'status_code': 500},
        ]
    )
    with pytest.raises(ServiceError, match=r'.*SERVER ERROR') as exec_info:
        for update in rest_client.watch_run_status('pid', 'rid', 'apikey',
                                                   timeout=None,
                                                   update_period=0.01):
            assert update['state'] == 'running'
            assert 'A' in str(format_run_status(update))

    assert "SERVER ERROR" in str(exec_info.value)


def test_delete_project_handles_500(requests_mock):
    rest_client = RestClient('http://testing-es-url')
    requests_mock.delete('http://testing-es-url/api/v1/projects/pid', text='',
                         status_code=500)

    with pytest.raises(ServiceError):
        rest_client.project_delete('pid', 'mykey')

    assert requests_mock.last_request.headers['Authorization'] == 'mykey'


def test_delete_project_handles_503(requests_mock):
    rest_client = RestClient('http://testing-es-url', ClientWaitingConfiguration(wait_exponential_max_ms=10,
                                                                                 wait_exponential_multiplier_ms=1,
                                                                                 stop_max_delay_ms=10))
    requests_mock.delete('http://testing-es-url/api/v1/projects/pid', text='',
                         status_code=503)

    with pytest.raises(ServiceError):
        rest_client.project_delete('pid', 'mykey')

    assert requests_mock.last_request.headers['Authorization'] == 'mykey'


def test_delete_run_handles_500(requests_mock):
    rest_client = RestClient('http://testing-es-url')
    requests_mock.delete('http://testing-es-url/api/v1/projects/pid/runs/rid',
                         text='', status_code=500)

    with pytest.raises(ServiceError):
        rest_client.run_delete('pid', 'rid', 'mykey')

    assert requests_mock.last_request.headers['Authorization'] == 'mykey'


def test_delete_run_handles_503(requests_mock):
    rest_client = RestClient('http://testing-es-url', ClientWaitingConfiguration(wait_exponential_max_ms=10,
                                                                                 wait_exponential_multiplier_ms=1,
                                                                                 stop_max_delay_ms=10))
    requests_mock.delete('http://testing-es-url/api/v1/projects/pid/runs/rid',
                         text='', status_code=503)

    with pytest.raises(ServiceError):
        rest_client.run_delete('pid', 'rid', 'mykey')

    assert requests_mock.last_request.headers['Authorization'] == 'mykey'
