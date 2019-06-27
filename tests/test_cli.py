"""
http://click.pocoo.org/5/testing/
"""
from __future__ import division, print_function

import json
import logging
import os
import random
import time
import unittest

import pytest
from click.testing import CliRunner
from future.builtins import range

import clkhash
import clkhash.cli
from clkhash import randomnames, rest_client
from clkhash.rest_client import ServiceError

from tests import *


class CLITestHelper(unittest.TestCase):
    SAMPLES = 100

    def setUp(self):
        super(CLITestHelper, self).setUp()
        self.pii_file = create_temp_file()
        self.pii_file_2 = create_temp_file()

        # Get random PII
        pii_data = randomnames.NameList(self.SAMPLES)
        data = [(name, dob) for _, name, dob, _ in pii_data.names]

        headers = ['NAME freetext', 'DOB YYYY/MM/DD']
        randomnames.save_csv(data, headers, self.pii_file)

        random.shuffle(data)
        randomnames.save_csv(data[::2], headers, self.pii_file_2)

        self.default_schema = [
            {"identifier": "INDEX"},
            {"identifier": "NAME freetext"},
            {"identifier": "DOB YYYY/MM/DD"},
            {"identifier": "GENDER M or F"}
        ]

        self.pii_file.close()
        self.pii_file_2.close()

    def tearDown(self):
        super(CLITestHelper, self).tearDown()

        # Delete temporary files if they exist.
        for f in self.pii_file, self.pii_file_2:
            try:
                os.remove(f.name)
            except:
                pass

    def run_command_capture_output(self, command):
        """
        Creates a NamedTempFile and saves the output of running a
        cli command to that file by adding `-o output.name` to the
        command before running it.

        :param command: e.g ["status"]
        :returns: The output as a string.
        :raises: AssertionError if the command's exit code isn't 0
        """

        runner = CliRunner()

        with temporary_file() as output_filename:
            command.extend(['-o', output_filename])
            cli_result = runner.invoke(clkhash.cli.cli, command)
            assert cli_result.exit_code == 0, cli_result.output
            with open(output_filename, 'rt') as output:
                return output.read()

    def run_command_load_json_output(self, command):
        """
         Parses the file as JSON.

        :param command: e.g ["status"]
        :return: The parsed JSON in the created output file.
        :raises: AssertionError if the command's exit code isn't 0
        :raises: json.decoder.JSONDecodeError if the output isn't json
        """
        logging.info(command)
        output_str = self.run_command_capture_output(command)
        return json.loads(output_str)


@unittest.skipUnless("INCLUDE_CLI" in os.environ,
                     "Set envvar INCLUDE_CLI to run. Disabled for jenkins")
class BasicCLITests(unittest.TestCase):

    def test_list_commands(self):
        runner = CliRunner()
        result = runner.invoke(clkhash.cli.cli, [])
        expected_commands = ['benchmark', 'create', 'create-project', 'generate',
                             'hash', 'upload',  'results', 'validate-schema']
        for expected_command in expected_commands:
            assert expected_command in result.output

    def test_version(self):
        runner = CliRunner()
        result = runner.invoke(clkhash.cli.cli, ['--version'])
        assert result.exit_code == 0
        assert clkhash.__version__ in result.output

    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(clkhash.cli.cli, '--help')

        assert 'hash' in result.output
        # assert 'bench' in result.output
        assert 'generate' in result.output
        assert 'Confidential Computing' in result.output

    def test_hash_auto_help(self):
        runner = CliRunner()
        result = runner.invoke(clkhash.cli.cli, ['hash'])
        assert 'Missing argument' in result.output

    def test_hash_help(self):
        runner = CliRunner()
        result = runner.invoke(clkhash.cli.cli, ['hash', '--help'])
        assert 'keys' in result.output
        assert 'schema' in result.output

    def test_bench(self):
        runner = CliRunner()
        result = runner.invoke(clkhash.cli.cli, ['benchmark'])
        assert 'hashes in' in result.output


class TestSchemaValidationCommand(unittest.TestCase):

    @staticmethod
    def validate_schema(schema_path):
        runner = CliRunner()
        result = runner.invoke(clkhash.cli.cli, [
            'validate-schema', schema_path
        ])
        return result

    def test_good_v1_schema(self):
        for schema_path in GOOD_SCHEMA_V1_PATH, SIMPLE_SCHEMA_PATH:
            result = self.validate_schema(schema_path)
            assert result.exit_code == 0
            assert 'schema is valid' in result.output

    def test_bad_v1_schema(self):
        result = self.validate_schema(BAD_SCHEMA_V1_PATH)
        assert result.exit_code == -1
        assert 'schema is not valid.' in result.output
        assert "'l' is a required property" in result.output


    def test_good_v2_schema(self):
        for schema_path in GOOD_SCHEMA_V2_PATH, RANDOMNAMES_SCHEMA_PATH:
            result = self.validate_schema(schema_path)
            assert result.exit_code == 0
            assert 'schema is valid' in result.output

    def test_bad_v1_schema(self):
        result = self.validate_schema(BAD_SCHEMA_V2_PATH)
        assert result.exit_code == -1
        assert 'schema is not valid.' in result.output


@unittest.skipUnless("INCLUDE_CLI" in os.environ,
                     "Set envvar INCLUDE_CLI to run. Disabled for jenkins")
class TestHashCommand(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()

    def test_hash_requires_keys(self):
        runner = self.runner

        with runner.isolated_filesystem():
            with open('in.csv', 'w') as f:
                f.write('Alice, 1967')

            result = runner.invoke(clkhash.cli.cli,
                                   ['hash', 'in.csv', 'out.json'])
            assert result.exit_code != 0
            self.assertIn('keys', result.output)

    def test_hash_with_provided_schema(self):
        runner = self.runner

        with runner.isolated_filesystem():
            with open('in.csv', 'w') as f:
                f.write('Alice,1967/09/27')

            result = runner.invoke(
                clkhash.cli.cli,
                ['hash', 'in.csv', 'a', 'b', SIMPLE_SCHEMA_PATH,
                 'out.json', '--no-header'])

            with open('out.json') as f:
                self.assertIn('clks', json.load(f))

    def test_hash_febrl_data(self):
        runner = self.runner
        schema_file = os.path.join(
            os.path.dirname(__file__),
            'testdata/dirty-data-schema.json'
        )
        a_pii = os.path.join(
            os.path.dirname(__file__),
            'testdata/dirty_1000_50_1.csv'
        )

        with runner.isolated_filesystem():
            result = runner.invoke(
                clkhash.cli.cli,
                ['hash', a_pii, 'a', 'b', schema_file, 'out.json'])

            result_2 = runner.invoke(
                clkhash.cli.cli,
                ['hash', a_pii, 'a', 'b', schema_file, 'out-2.json'])

            with open('out.json') as f:
                hasha = json.load(f)['clks']

            with open('out-2.json') as f:
                hashb = json.load(f)['clks']

        for i in range(1000):
            self.assertEqual(hasha[i], hashb[i])

    def test_hash_wrong_schema(self):
        runner = self.runner

        # This schema only has 4 features
        schema_file = os.path.join(
            os.path.dirname(__file__),
            'testdata/randomnames-schema.json'
        )

        # This CSV has 14 features
        a_pii = os.path.join(
            os.path.dirname(__file__),
            'testdata/dirty_1000_50_1.csv'
        )

        with runner.isolated_filesystem():

            result = runner.invoke(clkhash.cli.cli, ['hash',
                                                     '--quiet',
                                                     '--schema',
                                                     schema_file,
                                                     a_pii,
                                                     'a', 'b', '-'])

        assert result.exit_code != 0



@unittest.skipUnless("INCLUDE_CLI" in os.environ,
                     "Set envvar INCLUDE_CLI to run. Disabled for jenkins")
class TestHasherDefaultSchema(unittest.TestCase):

    samples = 100

    def setUp(self):
        self.pii_file = create_temp_file()

        pii_data = randomnames.NameList(TestHasherDefaultSchema.samples)
        randomnames.save_csv(
            pii_data.names,
            [f.identifier for f in pii_data.SCHEMA.fields],
            self.pii_file)
        self.pii_file.flush()

    def test_cli_includes_help(self):
        runner = CliRunner()
        result = runner.invoke(clkhash.cli.cli, ['--help'])
        self.assertEqual(result.exit_code, 0, result.output)

        assert 'Usage' in result.output
        assert 'Options' in result.output

    def test_version(self):
        runner = CliRunner()
        result = runner.invoke(clkhash.cli.cli, ['--version'])
        assert result.exit_code == 0
        self.assertIn(clkhash.__version__, result.output)

    def test_generate_command(self):
        runner = CliRunner()
        with temporary_file() as output_filename:
            with open(output_filename) as output:
                cli_result = runner.invoke(
                    clkhash.cli.cli,
                    ['generate', '50', output.name])
            self.assertEqual(cli_result.exit_code, 0, msg=cli_result.output)
            with open(output_filename, 'rt') as output:
                out = output.read()
        assert len(out) > 50

    def test_generate_default_schema_command(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            generate_schema_result = runner.invoke(
                clkhash.cli.cli,
                ['generate-default-schema', 'pii-schema.json'])
            self.assertEqual(generate_schema_result.exit_code, 0,
                             msg=generate_schema_result.output)

            hash_result = runner.invoke(
                clkhash.cli.cli,
                ['hash', self.pii_file.name, 'secret', 'key',
                 'pii-schema.json', 'pii-hashes.json'])
            self.assertEqual(hash_result.exit_code, 0, msg=hash_result.output)

    def test_basic_hashing(self):
        runner = CliRunner()
        with temporary_file() as output_filename:
            with open(output_filename, 'wt') as output:
                cli_result = runner.invoke(
                    clkhash.cli.cli,
                    ['hash', self.pii_file.name, 'secret', 'key',
                     RANDOMNAMES_SCHEMA_PATH, output.name])
            self.assertEqual(cli_result.exit_code, 0, msg=cli_result.output)

            with open(output_filename, 'rt') as output:
                self.assertIn('clks', json.load(output))


@unittest.skipUnless("INCLUDE_CLI" in os.environ,
                     "Set envvar INCLUDE_CLI to run. Disabled for jenkins")
class TestHasherSchema(CLITestHelper):
    def test_hashing_json_schema(self):
        runner = CliRunner()

        pii_data = randomnames.NameList(self.SAMPLES)
        pii_file = create_temp_file()
        randomnames.save_csv(pii_data.names,
                             [f.identifier for f in pii_data.SCHEMA.fields],
                             pii_file)
        pii_file.close()

        with temporary_file() as output_filename:
            with open(output_filename) as output:
                cli_result = runner.invoke(
                    clkhash.cli.cli,
                    ['hash', pii_file.name, 'secretkey1',
                     'secretkey2', RANDOMNAMES_SCHEMA_PATH, output.name])

            self.assertEqual(cli_result.exit_code, 0, msg=cli_result.output)

            with open(output_filename) as output:
                self.assertIn('clks', json.load(output))


@unittest.skipUnless("TEST_ENTITY_SERVICE" in os.environ,
                     "Set envvar TEST_ENTITY_SERVICE to run. Disabled for jenkins")
class TestCliInteractionWithService(CLITestHelper):

    def setUp(self):
        super(TestCliInteractionWithService, self).setUp()
        self.url = os.environ['TEST_ENTITY_SERVICE']

        self.clk_file = create_temp_file()
        self.clk_file_2 = create_temp_file()

        # hash some PII for uploading
        # TODO don't need to rehash data for every test
        runner = CliRunner()
        cli_result = runner.invoke(clkhash.cli.cli,
                                   ['hash',
                                   self.pii_file.name,
                                   'secretkey1',
                                   'secretkey2',
                                    SIMPLE_SCHEMA_PATH,
                                    self.clk_file.name])
        assert cli_result.exit_code == 0

        cli_result = runner.invoke(clkhash.cli.cli,
                                   ['hash',
                                   self.pii_file_2.name,
                                   'secretkey1',
                                   'secretkey2',
                                    SIMPLE_SCHEMA_PATH,
                                    self.clk_file_2.name])
        assert cli_result.exit_code == 0

        self.clk_file.close()
        self.clk_file_2.close()
        self._created_projects = []

    def tearDown(self):
        super(TestCliInteractionWithService, self).tearDown()
        os.remove(self.clk_file.name)
        os.remove(self.clk_file_2.name)

        self.delete_created_projects()

    def delete_created_projects(self):
        for project in self._created_projects:
            try:
                rest_client.project_delete(self.url, project['project_id'], project['result_token'])
            except KeyError:
                pass
            except ServiceError:
                # probably already deleted
                pass

    def _create_project(self, project_args=None):
        command = ['create-project', '--server', self.url, '--schema', SIMPLE_SCHEMA_PATH]
        if project_args is not None:
            for key in project_args:
                command.append('--{}'.format(key))
                command.append(project_args[key])

        project = self.run_command_load_json_output(command)
        self._created_projects.append(project)
        return project

    def _create_project_and_run(self, project_args=None, run_args=None):
        project = self._create_project(project_args)

        threshold = run_args['threshold'] if run_args is not None and 'threshold' in run_args else 0.99

        command = [
            'create',
            '--server', self.url,
            '--threshold', str(threshold),
            '--project', project['project_id'],
            '--apikey', project['result_token'],
        ]

        if run_args is not None:
            for key in run_args:
                command.append('--{}'.format(key))
                command.append(run_args[key])

        run = self.run_command_load_json_output(command)
        return project, run

    def test_status(self):
        self.run_command_load_json_output(['status', '--server', self.url])

    def test_status_invalid_server_raises(self):
        with pytest.raises(AssertionError) as exec_info:
            self.run_command_capture_output(['status', '--server', 'https://example.com'])

            assert 'invalid choice' in exec_info.value.args[0]

    def test_create_project(self):
        out = self._create_project()

        self.assertIn('project_id', out)
        self.assertIn('result_token', out)
        self.assertIn('update_tokens', out)

        self.assertGreaterEqual(len(out['project_id']), 16)
        self.assertGreaterEqual(len(out['result_token']), 16)
        self.assertGreaterEqual(len(out['update_tokens']), 2)

    def test_create_project_2_party(self):
        out = self._create_project(project_args={'parties': '2'})

        self.assertIn('project_id', out)
        self.assertIn('result_token', out)
        self.assertIn('update_tokens', out)

        self.assertGreaterEqual(len(out['project_id']), 16)
        self.assertGreaterEqual(len(out['result_token']), 16)
        self.assertGreaterEqual(len(out['update_tokens']), 2)

    def test_create_project_multi_party(self):
        out = self._create_project(
            project_args={'parties': '3', 'type': 'groups'})

        self.assertIn('project_id', out)
        self.assertIn('result_token', out)
        self.assertIn('update_tokens', out)

        self.assertGreaterEqual(len(out['project_id']), 16)
        self.assertGreaterEqual(len(out['result_token']), 16)
        self.assertGreaterEqual(len(out['update_tokens']), 3)

    def test_create_project_invalid_parties_type(self):
        with pytest.raises(AssertionError) as exec_info:
            self._create_project(project_args={'parties': '3'})

        assert "requires result type 'groups'"  in exec_info.value.args[0]

    def test_create_project_bad_type(self):
        with pytest.raises(AssertionError) as exec_info:
            self._create_project(project_args={'type': 'invalid'})

        assert 'invalid choice' in exec_info.value.args[0]

    def test_create_project_and_run(self):
        project, run = self._create_project_and_run()

        self.assertIn('project_id', project)
        self.assertIn('run_id', run)

    def test_delete_run(self):
        project, run = self._create_project_and_run()

        runner = CliRunner()

        command = [
                'delete',
                '--server', self.url,
                '--project', project['project_id'],
                '--run', run['run_id'],
                '--apikey', project['result_token']
            ]
        cli_result = runner.invoke(clkhash.cli.cli, command)
        assert cli_result.exit_code == 0, cli_result.output

        # TODO get runs and check it is gone?


    def test_delete_project(self):
        project, run = self._create_project_and_run()

        runner = CliRunner()
        command = [
            'delete-project',
            '--server', self.url,
            '--project', project['project_id'],
            '--apikey', project['result_token']
        ]
        cli_result = runner.invoke(clkhash.cli.cli, command)
        assert cli_result.exit_code == 0, cli_result.output

        with pytest.raises(ServiceError):
            rest_client.project_get_description(self.url, project['project_id'], project['result_token'])

    def test_create_with_optional_name(self):
        out = self._create_project({'name': 'testprojectname'})

        self.assertIn('project_id', out)
        self.assertIn('result_token', out)
        self.assertIn('update_tokens', out)

        self.assertGreaterEqual(len(out['project_id']), 16)
        self.assertGreaterEqual(len(out['result_token']), 16)
        self.assertGreaterEqual(len(out['update_tokens']), 2)

    def test_create_with_bad_schema(self):
        # Make sure we don't succeed with bad schema.
        schema_path = os.path.join(os.path.dirname(__file__), 'testdata', 'bad-schema-v1.json')
        with pytest.raises(AssertionError):
            self.run_command_load_json_output(
                [
                    'create-project',
                    '--server', self.url,
                    '--schema', schema_path
                ]
            )

    def test_single_upload(self):
        project = self._create_project()

        # Upload
        self.run_command_load_json_output(
            [
                'upload',
                '--server', self.url,
                '--project', project['project_id'],
                '--apikey', project['update_tokens'][0],
                self.clk_file.name
            ]
        )

    def test_2_party_upload_and_results(self):
        project, run = self._create_project_and_run()

        def get_coord_results():
            # Get results from coordinator
            return self.run_command_capture_output(
                [
                    'results',
                    '--server', self.url,
                    '--project', project['project_id'],
                    '--run', run['run_id'],
                    '--apikey', project['result_token']
                ]
            )

        # Upload Alice
        alice_upload = self.run_command_load_json_output(
            [
                'upload',
                '--server', self.url,
                '--project', project['project_id'],
                '--apikey', project['update_tokens'][0],
                self.clk_file.name
            ]
        )
        self.assertIn('receipt_token', alice_upload)

        out_early = get_coord_results()
        self.assertEqual("", out_early)

        # Upload Bob (subset of clks uploaded)
        bob_upload = self.run_command_load_json_output(
            [
                'upload',
                '--server', self.url,
                '--project', project['project_id'],
                '--apikey', project['update_tokens'][1],
                self.clk_file_2.name
            ]
        )

        self.assertIn('receipt_token', bob_upload)

        # Give the server a small amount of time to process
        time.sleep(5.0)

        results_raw = get_coord_results()
        res = json.loads(results_raw)
        self.assertIn('mask', res)

        # Should be close to half ones. This is really just testing the service
        # not the command line tool.
        number_in_common = res['mask'].count(1)
        self.assertGreaterEqual(number_in_common / self.SAMPLES, 0.4)
        self.assertLessEqual(number_in_common / self.SAMPLES, 0.6)

        # Get results from first DP
        alice_res = self.run_command_load_json_output(
            [
                'results',
                '--server', self.url,
                '--project', project['project_id'],
                '--run', run['run_id'],
                '--apikey', alice_upload['receipt_token']
            ]
        )

        self.assertIn('permutation', alice_res)
        self.assertIn('rows', alice_res)

        # Get results from second DP
        bob_res = self.run_command_load_json_output(
            [
                'results',
                '--server', self.url,
                '--project', project['project_id'],
                '--run', run['run_id'],
                '--apikey', bob_upload['receipt_token'],
                '--watch'
            ]
        )

        self.assertIn('permutation', bob_res)
        self.assertIn('rows', bob_res)

    def test_multi_party_upload_and_results(self):
        project, run = self._create_project_and_run(
            {'type': 'groups', 'parties': '3'})

        def get_coord_results():
            # Get results from coordinator
            return self.run_command_capture_output(
                [
                    'results',
                    '--server', self.url,
                    '--project', project['project_id'],
                    '--run', run['run_id'],
                    '--apikey', project['result_token']
                ]
            )

        # Upload Alice
        alice_upload = self.run_command_load_json_output(
            [
                'upload',
                '--server', self.url,
                '--project', project['project_id'],
                '--apikey', project['update_tokens'][0],
                self.clk_file.name
            ]
        )
        self.assertIn('receipt_token', alice_upload)

        out_early = get_coord_results()
        self.assertEqual("", out_early)

        # Upload Bob (subset of clks uploaded)
        bob_upload = self.run_command_load_json_output(
            [
                'upload',
                '--server', self.url,
                '--project', project['project_id'],
                '--apikey', project['update_tokens'][1],
                self.clk_file_2.name
            ]
        )

        self.assertIn('receipt_token', bob_upload)

        out_early = get_coord_results()
        self.assertEqual("", out_early)

        # Upload Charlie (we're lazy and just reuse Bob)
        charlie_upload = self.run_command_load_json_output(
            [
                'upload',
                '--server', self.url,
                '--project', project['project_id'],
                '--apikey', project['update_tokens'][2],
                self.clk_file_2.name
            ]
        )

        self.assertIn('receipt_token', charlie_upload)

        # Give the server a small amount of time to process
        time.sleep(10.0)

        results = get_coord_results()
        res = json.loads(results)
        self.assertIn('groups', res)

        # Recall that Bob and Charlie have the same samples. These form
        # half of Alice's samples.
        groups = res['groups']
        assert self.SAMPLES * .45 <= len(groups) <= self.SAMPLES * .55

        number_of_groups_of_three = sum(len(group) == 3 for group in groups)
        assert number_of_groups_of_three >= .9 * len(groups)
