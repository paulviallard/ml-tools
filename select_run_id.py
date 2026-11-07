import os
import sys
import argparse
import logging

# Useful packages in the .ini files (and in the constraints)
try:
    import numpy as np
except ImportError:
    pass
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run import LaunchConfig
from check_run_id import get_job_string

###############################################################################


class CollectLaunchConfig(LaunchConfig):

    def __init__(self, f, job_id_list=None):
        self.__run_dict = {}
        self.__param = None
        super().__init__(f, job_id_list)

    def _get_var_list(self, param_list, known_param, known_var):
        # We get the parameters of a given run_id
        self.__param = dict(known_param)
        return super()._get_var_list(param_list, known_param, known_var)

    def _run_command(self, command, run_name=None, job_list=None):
        # When "running" a command, we save the parameters in the dict
        run_id = self.__param["run_id"]
        del self.__param["job_id"]
        self.__run_dict[run_id] = self.__param

    def get_run_dict(self):
        return dict(self.__run_dict)

###############################################################################


def get_run_dict(config_file):
    # We get, for a given .ini file, the dict associating each run_id to
    # its parameters
    config = CollectLaunchConfig(config_file)
    config.run()
    return config.get_run_dict()


def get_selected_run_id_list(run_dict, constraint):
    # We keep the run_id whose parameters satisfy the constraint
    selected_run_id_list = []
    for run_id, param in sorted(run_dict.items()):
        # We evaluate the constraint with the parameters as variables
        try:
            is_selected = eval(constraint, {**globals(), **param})
        # If the run does not have a parameter used in the constraint
        # (e.g., it comes from another section), it is not selected
        except NameError:
            is_selected = False
        if(is_selected):
            selected_run_id_list.append(run_id)
    return selected_run_id_list


###############################################################################


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    logging.StreamHandler.terminator = ""

    # ----------------------------------------------------------------------- #

    arg_parser = argparse.ArgumentParser(
        description='Select the run_id whose parameters satisfy a constraint')

    arg_parser.add_argument(
        "path", metavar="path", type=str,
        help="Path of the ini file describing the runs")
    arg_parser.add_argument(
        "constraint", metavar="constraint", type=str,
        help="Python expression on the parameters (e.g., 'algo in [\"a\"]')")

    arg_list = arg_parser.parse_args()

    # We get the parameters of each run_id described in the .ini file
    run_dict = get_run_dict(arg_list.path)

    # We keep the run_id satisfying the constraint
    selected_run_id_list = get_selected_run_id_list(
        run_dict, arg_list.constraint)

    # We print them as a compressed, comma-separated list of ranges,
    # ready to be used with --job
    logging.info(get_job_string(selected_run_id_list)+"\n")
