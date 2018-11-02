from setuptools import setup, find_packages
import codecs

requirements = [
        "bitarray>=0.8",
        "click>=6.7",
        "cryptography>=2.3",
        "enum34==1.1.6; python_version < '3.4'",
        "future>=0.16",
        "futures>=3.1; python_version < '3.2'",  # Backport from Py3.2
        "mypy_extensions>=0.3",
        "pyblake2>=1.1.1; python_version < '3.6'",
        "jsonschema>=2.6",
        "requests>=2.20",
        "tqdm>=4.24",
        "typing>=3.6; python_version < '3.5'",  # Backport from Py3.5
        "bashplotlib>=0.6.5"
    ]

with codecs.open('README.md', 'r', 'utf-8') as f:
    readme = f.read()

setup(
    name="clkhash",
    version='0.12.1',
    description='Hash utility to create Cryptographic Linkage Keys',
    long_description=readme,
    long_description_content_type='text/markdown',
    url='https://github.com/n1analytics/clkhash',
    license='Apache',
    install_requires=requirements,
    setup_requires=['pytest-runner'],
    tests_require=['pytest', 'pytest-cov', 'requests-mock', 'codecov'],
    packages=find_packages(exclude=['tests']),
    package_data={'clkhash': ['data/*.csv', 'data/*.json', 'schemas/*.json']},
    project_urls={
        'Documentation': 'http://clkhash.readthedocs.io/',
        'Source': 'https://github.com/n1analytics/clkhash',
        'Tracker': 'https://github.com/n1analytics/clkhash/issues',
    },
    entry_points={
        'console_scripts': [
            'clkutil = clkhash.cli:cli'
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Topic :: Security :: Cryptography",
        "Environment :: Console",
        "Operating System :: OS Independent",
        "Natural Language :: English",
    ],
)
