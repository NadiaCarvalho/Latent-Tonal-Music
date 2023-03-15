"""Utility functions for harmrep"""


def run_name_to_dict(run_name):
    """
    X1
    """
    return dict((x.strip(), y.strip())
                for x, y in (element.split('=') for element in run_name.split('-') if '=' in element))
