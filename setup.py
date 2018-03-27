from setuptools import setup, find_packages

requirements = [
        "bitarray==0.8.1",
        "click==6.7",
        "requests==2.18.4",
        "futures>=3.1; python_version == '2.7'",
        "cryptography==2.1.3",
        "tqdm==4.19.4",
        "typing>=3.6.2",
        "future==0.16.0",
        "pyblake2==1.1.0; python_version < '3.6'",
        "enum34==1.1.6; python_version < '3.4'"
    ]

setup(
    name="clkhash",
    version='0.10.1',
    description='Hash utility to create Cryptographic Linkage Keys',
    url='https://github.com/n1analytics/clkhash',
    license='Apache',
    install_requires=requirements,
    setup_requires=['pytest-runner'],
    tests_require=['pytest', 'pytest-cov'],
    packages=find_packages(exclude=['tests']),
    package_data={'clkhash': ['data/*.csv']},
    entry_points={
        'console_scripts': [
            'clkutil = clkhash.cli:cli'
        ],
    }
)
