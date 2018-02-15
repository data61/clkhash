from setuptools import setup, find_packages

requirements = [
        "bitarray==0.8.1",
        "click==6.7",
        "requests==2.18.4",
        "futures==3.1.1",
        "cryptography==2.1.3",
        "tqdm==4.19.4",
        "typing",
        "future==0.16.0",
        "typing>=3.6.2"
    ]

setup(
    name="clkhash",
    version='0.9.0',
    description='Hash utility to create Cryptographic Linkage Keys',
    url='https://github.com/n1analytics/clkhash',
    license='Apache',
    install_requires=requirements,
    test_requires=['nose>=1.3'],
    packages=find_packages(exclude=['tests']),
    package_data={'clkhash': ['data/*.csv']},
    entry_points={
        'console_scripts': [
            'clkutil = clkhash.cli:cli'
        ],
    }
)
