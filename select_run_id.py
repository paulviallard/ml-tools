import os
import re
import sys
import argparse
import logging

# Useful packages in the .ini files (and in the constraints)
try:
    import numpy as np
except ImportError:
    pass
import math
import glob
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run import LaunchConfig, get_job_string

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


def get_selected_run_id_list(run_dict, constraint):
    # We get the name of the parameters of all the runs
    param_name_set = set()
    for param in run_dict.values():
        param_name_set.update(param.keys())

    # We keep the run id whose parameters satisfy the constraint
    selected_run_id_list = []
    for run_id, param in sorted(run_dict.items()):
        # We evaluate the constraint with the parameters as variables
        try:
            is_selected = eval(constraint, {**globals(), **param})
        # If the run does not have a parameter used in the constraint
        # (e.g., it comes from another section), it is not selected
        # (any other unknown name is an error, e.g., a typo)
        except NameError as error:
            # (we get the unknown name from the message of the error, since
            # error.name does not exist in the old versions of Python)
            unknown_name = re.search(r"name '(.*)' is not defined", str(error))
            if(unknown_name is None
               or unknown_name.group(1) not in param_name_set):
                raise
            is_selected = False
        if(is_selected):
            selected_run_id_list.append(run_id)
    return selected_run_id_list


def convert_run_id_list(config, selected_run_id_list):
    # We get the runs of each meta_id and of each of its prefixes
    meta_id_dict = {}
    for run_id in config.get_run_dict():
        meta_id = config.get_meta_id(run_id)
        # For each level of the meta id,
        for i in range(1, len(meta_id)+1):
            # we add the run id 
            sub_meta_id = meta_id[:i]
            if(i < len(meta_id)):
                sub_meta_id = sub_meta_id+("-",)
            if(sub_meta_id not in meta_id_dict):
                meta_id_dict[sub_meta_id] = []
            meta_id_dict[sub_meta_id].append(run_id)

    # We get the same dict for the selected runs (and the list of the
    # prefixes and the meta_id of each selected run)
    selected_meta_id_dict = {}
    meta_id_list_dict = {}
    for run_id in selected_run_id_list:
        meta_id = config.get_meta_id(run_id)
        meta_id_list_dict[run_id] = []
        # For each level of the meta id,
        for i in range(1, len(meta_id)+1):
            # we add the run id
            sub_meta_id = meta_id[:i]
            if(i < len(meta_id)):
                sub_meta_id = sub_meta_id+("-",)
            meta_id_list_dict[run_id].append(sub_meta_id)
            if(sub_meta_id not in selected_meta_id_dict):
                selected_meta_id_dict[sub_meta_id] = []
            selected_meta_id_dict[sub_meta_id].append(run_id)

    # We simplify the meta_id
    meta_id_list = []
    # For each selected run,
    for run_id in selected_run_id_list:
        # we look at its meta_id and its prefixes
        for sub_meta_id in meta_id_list_dict[run_id]:
            # If all the runs of this meta_id are selected
            if(len(selected_meta_id_dict[sub_meta_id])
               == len(meta_id_dict[sub_meta_id])):
                # we keep it
                if(sub_meta_id not in meta_id_list):
                    meta_id_list.append(sub_meta_id)
                break
    return meta_id_list


def get_meta_string(meta_id_list):
    # We create the string of each meta id
    meta_string_list = []
    for meta_id in meta_id_list:
        if(meta_id[-1] == "-"):
            index_list = meta_id[:-1]
        else:
            index_list = meta_id
        meta_string = "-"+"-".join([str(index) for index in index_list])
        if(meta_id[-1] == "-"):
            meta_string += "-"
        meta_string_list.append(meta_string)

    return ",".join(meta_string_list)


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
    config = CollectLaunchConfig(arg_list.path)
    config.run()
    run_dict = config.get_run_dict()

    # We keep the run_id satisfying the constraint
    selected_run_id_list = get_selected_run_id_list(
        run_dict, arg_list.constraint)
    selected_meta_id_list = convert_run_id_list(config, selected_run_id_list)

    # We print them as a compressed, comma-separated list of ranges,
    # ready to be used with --job
    logging.info(get_job_string(selected_run_id_list)+"\n")
    logging.info(get_meta_string(selected_meta_id_list)+"\n")
