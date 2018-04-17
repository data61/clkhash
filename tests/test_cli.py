"""
http://click.pocoo.org/5/testing/
"""
from __future__ import division, print_function

import json
import os
import random
import time
import unittest

from click.testing import CliRunner

import clkhash
import clkhash.cli
from clkhash import randomnames

from tests import temporary_file, create_temp_file

SIMPLE_SCHEMA_PATH = os.path.join(
    os.path.dirname(__file__),
    'testdata',
    'simple-schema.json'
)

RANDOMNAMES_SCHEMA_PATH = os.path.join(
    os.path.dirname(clkhash.__file__),
    'data',
    'randomnames-schema.json'
)


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
            assert cli_result.exit_code == 0
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
        output_str = self.run_command_capture_output(command)
        return json.loads(output_str)


@unittest.skipUnless("INCLUDE_CLI" in os.environ,
                     "Set envvar INCLUDE_CLI to run. Disabled for jenkins")
class BasicCLITests(unittest.TestCase):

    def test_list_commands(self):
        runner = CliRunner()
        result = runner.invoke(clkhash.cli.cli, [])
        for expected_command in set(['hash', 'upload', 'create', 'results', 'generate', 'benchmark']):
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

    def tearDown(self):
        super(TestCliInteractionWithService, self).tearDown()
        os.remove(self.clk_file.name)
        os.remove(self.clk_file_2.name)

    def test_status(self):
        self.run_command_load_json_output(['status'])

    def test_create(self):
        out = self.run_command_load_json_output(['create'])

        self.assertIn('resource_id', out)
        self.assertIn('result_token', out)
        self.assertIn('update_tokens', out)

        self.assertGreaterEqual(len(out['resource_id']), 16)
        self.assertGreaterEqual(len(out['result_token']), 16)
        self.assertGreaterEqual(len(out['update_tokens']), 2)

    def test_create_with_threshold(self):
        out = self.run_command_load_json_output(['create', '--threshold', '0.50'])

        self.assertIn('resource_id', out)
        self.assertIn('result_token', out)
        self.assertIn('update_tokens', out)

        self.assertGreaterEqual(len(out['resource_id']), 16)
        self.assertGreaterEqual(len(out['result_token']), 16)
        self.assertGreaterEqual(len(out['update_tokens']), 2)

    def test_create_with_schema(self):
        out = self.run_command_load_json_output(
            ['create',
             '--schema',
             os.path.join(os.path.dirname(__file__),
                          'testdata',
                          'good-schema-v1.json')])

        self.assertIn('resource_id', out)
        self.assertIn('result_token', out)
        self.assertIn('update_tokens', out)

        self.assertGreaterEqual(len(out['resource_id']), 16)
        self.assertGreaterEqual(len(out['result_token']), 16)
        self.assertGreaterEqual(len(out['update_tokens']), 2)

        # Make sure we don't succeed with bad schema.
        runner = CliRunner()
        with temporary_file() as output_filename:
            cli_result = runner.invoke(
                clkhash.cli.cli,
                ['create',
                 '--schema',
                 os.path.join(os.path.dirname(__file__),
                              'testdata',
                              'bad-schema-v1.json')])
        self.assertNotEqual(cli_result, 0)

    def test_single_upload(self):
        mapping = self.run_command_load_json_output(['create'])

        # Upload
        self.run_command_load_json_output(
            [
                'upload',
                '--mapping',
                mapping['resource_id'],
                '--apikey',
                mapping['update_tokens'][0],
                self.clk_file.name
            ]
        )

    def test_2_party_upload_and_results(self):
        mapping = self.run_command_load_json_output(['create'])

        def get_coord_results():
            # Get results from coordinator
            return self.run_command_capture_output(
                [
                    'results',
                    '--mapping',
                    mapping['resource_id'],
                    '--apikey',
                    mapping['result_token']
                ]
            )

        # Upload Alice
        alice_upload = self.run_command_load_json_output(
            [
                'upload',
                '--mapping',
                mapping['resource_id'],
                '--apikey',
                mapping['update_tokens'][0],
                self.clk_file.name
            ]
        )

        out_early = get_coord_results()
        self.assertEqual("", out_early)

        # Upload Bob (subset of clks uploaded)
        bob_upload = self.run_command_load_json_output(
            [
                'upload',
                '--mapping',
                mapping['resource_id'],
                '--apikey',
                mapping['update_tokens'][1],
                self.clk_file_2.name
            ]
        )

        # Give the server a small amount of time to process
        time.sleep(3.0)

        res = json.loads(get_coord_results())
        self.assertIn('mask', res)

        # Should be close to half ones. This is really just testing the service
        # not the command line tool.
        number_in_common = res['mask'].count(1)
        self.assertGreaterEqual(number_in_common / self.SAMPLES, 0.4)
        self.assertLessEqual(number_in_common / self.SAMPLES, 0.6)

        # # Get results from first DP
        alice_res = self.run_command_load_json_output(
            [
                'results',
                '--mapping',
                mapping['resource_id'],
                '--apikey',
                alice_upload['receipt-token']
            ]
        )

        self.assertIn('permutation', alice_res)
        self.assertIn('rows', alice_res)
