from setuptools import setup, find_packages

requirements = [
        "bitarray>=0.8",
        "click>=6.7",
        "requests>=2.18",
        "futures>=3.1; python_version < '3.2'",  # Backport from Py3.2
        "cryptography>=2.1",
        "tqdm>=4.19",
        "future>=0.16",
        "typing>=3.6; python_version < '3.5'",  # Backport from Py3.5
        "jsonschema>=2.6",
    ]

setup(
    name="clkhash",
    version='0.8.2-dev',
    description='Hash utility to create Cryptographic Linkage Keys',
    url='https://github.com/n1analytics/clkhash',
    license='Apache',
    install_requires=requirements,
    test_requires=['nose>=1.3'],
    packages=find_packages(exclude=['tests']),
    package_data={'clkhash': ['data/*.csv', 'master-schemas/*.json']},
    entry_points={
        'console_scripts': [
            'clkutil = clkhash.cli:cli'
        ],
    }
)
