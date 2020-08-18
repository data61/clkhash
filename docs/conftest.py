# we don't want to fail a notebook test if there is a deprication warnings written to stderr
def pytest_collectstart(collector):
    collector.skip_compare += 'stderr',
