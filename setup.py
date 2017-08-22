from setuptools import setup, find_packages

requirements = [
        "bitarray==0.8.1",
        "networkx==1.11",
        "click==6.7",
        "requests==2.18.1"
    ]

setup(
    name="clkhash",
    version='0.7.2',
    description='Hash utility to create Cryptographic Linkage Keys',
    url='https://github.com/n1analytics/clkhash',
    license='Apache',
    setup_requires=requirements,
    install_requires=requirements,
    test_requires=requirements,
    packages=find_packages(exclude=['tests']),
    package_data={'clkhash': ['data/*.csv']},
    entry_points={
        'console_scripts': [
            'clkutil = clkhash.cli:cli'
        ],
    }
)
