from setuptools import setup, find_packages
import codecs

requirements = [
        "bitarray>=0.8",
        "click>=6.7",
        "cryptography>=2.2",
        "enum34==1.1.6; python_version < '3.4'",
        "future>=0.16",
        "futures>=3.1; python_version < '3.2'",  # Backport from Py3.2
        "mypy_extensions>=0.3",
        "pyblake2>=1.1.1; python_version < '3.6'",
        "jsonschema>=2.6",
        "requests>=2.18",
        "tqdm>=4.19",
        "typing>=3.6; python_version < '3.5'"  # Backport from Py3.5
    ]

with codecs.open('README.md', 'r', 'utf-8') as f:
    readme = f.read()

setup(
    name="clkhash",
    version='0.11.0',
    description='Hash utility to create Cryptographic Linkage Keys',
    long_description=readme,
    long_description_content_type='text/markdown',
    url='https://github.com/n1analytics/clkhash',
    license='Apache',
    install_requires=requirements,
    setup_requires=['pytest-runner'],
    tests_require=['pytest', 'pytest-cov'],
    packages=find_packages(exclude=['tests']),
    package_data={'clkhash': ['data/*.csv', 'data/*.json', 'master-schemas/*.json']},
    entry_points={
        'console_scripts': [
            'clkutil = clkhash.cli:cli'
        ],
    }
)
