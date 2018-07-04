from __future__ import division, print_function
import os
import time
import unittest
import json

import pytest

import clkhash
from clkhash.clk import generate_clk_from_csv
from clkhash import rest_client
from clkhash.rest_client import ServiceError
from tests import SIMPLE_SCHEMA_PATH, SAMPLE_DATA_SCHEMA_PATH, SAMPLE_DATA_PATH_1, SAMPLE_DATA_PATH_2


@unittest.skipUnless("TEST_ENTITY_SERVICE" in os.environ,
                     "Set envvar TEST_ENTITY_SERVICE to run. Disabled for jenkins")
class TestRestClientInteractionWithService(unittest.TestCase):

    def setUp(self):
        super(TestRestClientInteractionWithService, self).setUp()
        self.url = os.environ['TEST_ENTITY_SERVICE']

        schema_object = clkhash.schema.Schema.from_json_file(schema_file=open(SAMPLE_DATA_SCHEMA_PATH, 'rt'))
        keys = ('secret', 'key')
        self.clk_data_1 = json.dumps(
            {'clks': generate_clk_from_csv(open(SAMPLE_DATA_PATH_1, 'rt'), keys, schema_object, header='ignore')})
        self.clk_data_2 = json.dumps(
            {'clks': generate_clk_from_csv(open(SAMPLE_DATA_PATH_2, 'rt'), keys, schema_object, header='ignore')})

    def _create_project(self, schema=None, result_type='permutations', name='', notes='', parties=2):
        if schema is None:
            schema = json.load(open(SIMPLE_SCHEMA_PATH,'rt'))
        return rest_client.project_create(self.url, schema, result_type, name, notes, parties)

    def test_status(self):
        assert 'status' in rest_client.server_get_status(self.url)
        assert 'project_count' in rest_client.server_get_status(self.url)

    def test_project_description(self):
        p = self._create_project(schema={'id': 'test schema'})
        description = rest_client.project_get_description(self.url, p['project_id'], p['result_token'])
        assert 'id' in description['schema']
        assert description['schema']['id'] == 'test schema'

    def test_upload_clks(self):
        p = self._create_project()
        schema_object = clkhash.schema.Schema.from_json_file(schema_file=open(SAMPLE_DATA_SCHEMA_PATH, 'rt'))
        upload_response = rest_client.project_upload_clks(self.url, p['project_id'], p['update_tokens'][0], self.clk_data_1)
        assert 'receipt_token' in upload_response

    def test_project_run(self):
        p = self._create_project()

        p_id = p['project_id']
        upload_response_1 = rest_client.project_upload_clks(self.url, p_id, p['update_tokens'][0], self.clk_data_1)
        upload_response_2 = rest_client.project_upload_clks(self.url, p_id, p['update_tokens'][1], self.clk_data_2)

        run_response = rest_client.run_create(self.url, p_id, p['result_token'], 0.999, name='clkhash rest client test')
        assert 'run_id' in run_response
        r_id = run_response['run_id']
        with pytest.raises(ServiceError):
            status_invalid_run = rest_client.run_get_status(self.url, p_id, 'invalid-run-id', p['result_token'])
        with pytest.raises(ServiceError):
            status_invalid_auth = rest_client.run_get_status(self.url, p_id, r_id, 'invalid-token')

        status1 = rest_client.run_get_status(self.url, p_id, r_id, p['result_token'])
        assert 'state' in status1
        assert 'stages' in status1
        print(rest_client.format_run_status(status1))
        time.sleep(2)
        status2 = rest_client.run_get_status(self.url, p_id, r_id, p['result_token'])
        assert status2['state'] == 'completed'
        coord_result_raw = rest_client.run_get_result_text(self.url, p_id, r_id, p['result_token'])
        coord_result = json.loads(coord_result_raw)
        assert 'mask' in coord_result
        assert len(coord_result['mask']) == 1000
        assert coord_result['mask'].count(1) > 10

        result_a = json.loads(rest_client.run_get_result_text(self.url, p_id, r_id, upload_response_1['receipt_token']))
        assert 'permutation' in result_a
        assert 'rows' in result_a
        assert result_a['rows'] == 1000

        rest_client.run_delete(self.url, p_id, r_id, p['result_token'])
        rest_client.project_delete(self.url, p_id, p['result_token'])


def test_status_404_raises_service_error(requests_mock):
    requests_mock.get('http://testing-es-url/api/v1/status', status_code=404)
    with pytest.raises(ServiceError):
        rest_client.server_get_status('http://testing-es-url')


def test_status_500_raises_service_error(requests_mock):
    requests_mock.get('http://testing-es-url/api/v1/status', status_code=500)
    with pytest.raises(ServiceError):
        rest_client.server_get_status('http://testing-es-url')


def test_status_invalid_json_raises_service_error(requests_mock):
    requests_mock.get('http://testing-es-url/api/v1/status', status_code=200, text='NOT JSON')
    with pytest.raises(ServiceError):
        rest_client.server_get_status('http://testing-es-url')


def test_status_calls_correct_url(requests_mock):
    requests_mock.get('http://testing-es-url/api/v1/status', json={'status': 'ok'})
    rest_client.server_get_status('http://testing-es-url')
    assert requests_mock.called


def test_create_project_passes_all_data(requests_mock):
    requests_mock.post('http://testing-es-url/api/v1/projects', json={'status': 'ok'}, status_code=201)
    rest_client.project_create('http://testing-es-url', {'id': 'schema'}, 'restype', 'myname', 'mynote', 5)
    posted_data = requests_mock.last_request.json()
    assert all(expected_field in posted_data for expected_field in {'schema', 'result_type', 'number_parties', 'name', 'notes'})

    assert posted_data['name'] == 'myname'
    assert posted_data['notes'] == 'mynote'
    assert posted_data['number_parties'] == 5


def test_create_project_default_data(requests_mock):
    requests_mock.post('http://testing-es-url/api/v1/projects', json={'status': 'ok'}, status_code=201)
    rest_client.project_create('http://testing-es-url', {'id': 'schema'}, 'restype', 'myname')
    posted_data = requests_mock.last_request.json()
    assert all(expected_field in posted_data for expected_field in {'schema', 'result_type', 'number_parties', 'name', 'notes'})

    assert 'created by clkhash' in posted_data['notes']
    assert posted_data['number_parties'] == 2


def test_create_project_handles_400(requests_mock):
    requests_mock.post('http://testing-es-url/api/v1/projects', json={'title': 'not ok', 'status': 400}, status_code=400)

    with pytest.raises(ServiceError):
        rest_client.project_create('http://testing-es-url', {'id': 'schema'}, 'restype', 'myname', 'mynote')


def test_create_project_handles_503(requests_mock):
    requests_mock.post('http://testing-es-url/api/v1/projects', text='', status_code=503)

    with pytest.raises(ServiceError):
        rest_client.project_create('http://testing-es-url', {'id': 'schema'}, 'restype', 'myname', 'mynote')



