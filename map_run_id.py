import os
import sys
import argparse
import subprocess
import logging

# Useful packages in the .ini files
try:
    import numpy as np
except ImportError:
    pass
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run import LaunchConfig

###############################################################################


class CollectLaunchConfig(LaunchConfig):

    def __init__(self, f, job_id_list=None):
        self.__run_dict = {}
        self.__param = None
        self.__command = None
        super().__init__(f, job_id_list)

    def _get_var_list(self, param_list, known_param, known_var):
        # We get the parameters of a given run_id
        self.__param = dict(known_param)
        return super()._get_var_list(param_list, known_param, known_var)

    def _get_command(self, job_tree):
        # We get the command (before the replacements)
        self.__command = super()._get_command(job_tree)
        # We get the name of the section
        self.__section = (job_tree[0] or "").lstrip("!")
        return self.__command

    def _run_command(self, command, run_name=None, job_list=None):
        # When "running" a command, we save the command, the parameters and
        # the name of the section in the dict
        run_id = self.__param["run_id"]
        del self.__param["run_id"]
        del self.__param["job_id"]
        self.__run_dict[run_id] = {
            "param": self.__param,
            "command": self.__command,
            "section": self.__section,
        }

    def get_run_dict(self):
        return dict(self.__run_dict)

    # ----------------------------------------------------------------------- #

    def __is_in_ignore_list(self, ignore_list, section, name):
        # We check if the name is in the list to ignore (and if the section
        # is also in the list)
        for ignore_section, ignore_name in ignore_list:
            if(ignore_name == name and ignore_section in [None, section]):
                return True
        return False

    def __get_reverse_run_key_list(self, run_key_dict, ignore_list):
        section = run_key_dict["section"]
        # We create the list associated with a run
        # (the command and the parameters)
        reverse_run_key_list = []

        # We insert the command in the list if it is not ignored
        command = run_key_dict["command"]
        if(not(self.__is_in_ignore_list(ignore_list, section, "command"))):
            reverse_run_key_list.append(("command", command))
        # We insert the parameters in the list if it is not ignored
        for key, value in run_key_dict["param"].items():
            if(not(self.__is_in_ignore_list(ignore_list, section, key))):
                reverse_run_key_list.append((key, repr(value)))

        return reverse_run_key_list

    def get_reverse_run_dict(self, ignore_list):
        reverse_run_dict = {}
        # For each run,
        for run_id, run_key_dict in self.__run_dict.items():
            # We get its tuple
            reverse_run_key_tuple = tuple(self.__get_reverse_run_key_list(
                run_key_dict, ignore_list))
            # and insert it in the dict with the run_id
            if(reverse_run_key_tuple not in reverse_run_dict):
                reverse_run_dict[reverse_run_key_tuple] = []
            reverse_run_dict[reverse_run_key_tuple].append(run_id)
        return reverse_run_dict

###############################################################################


def get_reverse_run_dict(config_file, ignore_list):
    # We get, for a given .ini file, the dict associating each run
    # signature (command, parameters) to the run_id sharing it
    config = CollectLaunchConfig(config_file)
    config.run()
    return config.get_reverse_run_dict(ignore_list)


def parse_ignore(ignore_string):
    # If the ignore string is empty, we have nothing to ignore
    ignore_list = []
    if(ignore_string == ""):
        return ignore_list

    # For each item (without the whitespaces),
    for item in ignore_string.split(","):
        item = item.strip()
        # If it is empty, we skip it
        if(item == ""):
            continue
        # Otherwise, we insert it in the list as a tuple (section, name).
        # An item without "/" applies to every section (section is None)
        item_list = item.split("/", 1)
        if(len(item_list) == 1):
            item_list = [None]+item_list
        ignore_list.append(tuple(item_list))
    return ignore_list


def get_mapping_dict(input_reverse_run_dict, output_reverse_run_dict):
    # We build the run_id -> run_id mapping between the input and the
    # output file, by matching the runs that share the same command and
    # parameters
    mapping_dict = {}

    # For each run (or group of runs sharing the same command/parameters)
    # of the input file,
    for run_key, run_id_list in input_reverse_run_dict.items():
        run_id_list = sorted(run_id_list)

        # If we find no run at all in the output file, we skip it
        if(run_key not in output_reverse_run_dict):
            logging.warning(f"IGNORED:{run_id_list}\n")
            continue

        output_run_id_list = sorted(output_reverse_run_dict[run_key])

        # If both files have the same number of runs for this
        # command/parameters, we pair them up in run_id order. Otherwise,
        # we cannot tell which run_id should go with which, so we skip
        # them to avoid renaming a file incorrectly
        if(len(run_id_list) != len(output_run_id_list)):
            logging.warning(
                f"IGNORED:{run_id_list} -> {output_run_id_list}\n")
            continue

        for run_id, output_run_id in zip(run_id_list, output_run_id_list):
            mapping_dict[run_id] = output_run_id

    return mapping_dict


def generate_cmd_list(mapping, command):
    # We build the command to run for each mapped run, by substituting
    # {input_run_id}/{output_run_id} in the command
    cmd_list = []
    for input_run_id, output_run_id in sorted(mapping.items()):
        cmd_list.append(command.format(
            input_run_id=input_run_id, output_run_id=output_run_id))
    return cmd_list


###############################################################################


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    logging.StreamHandler.terminator = ""

    # ----------------------------------------------------------------------- #

    arg_parser = argparse.ArgumentParser(
        description='Run a command for each run, mapping its run_id '
                    'from the input ini file to the output ini file')

    arg_parser.add_argument(
        "input_file", metavar="input_file", type=str,
        help="The ini file the run_id were created with")
    arg_parser.add_argument(
        "output_file", metavar="output_file", type=str,
        help="The ini file whose run_id we want to adopt")
    arg_parser.add_argument(
        "command", metavar="command", type=str,
        help="The command to run, with {input_run_id} and {output_run_id}")

    arg_parser.add_argument(
        "--ignore", metavar="ignore", default="", type=str,
        help="The list of section/name to ignore when matching runs")
    arg_parser.add_argument(
        "--print", action="store_true", dest="print_only",
        help="If set, only print the commands instead of running them")

    arg_list = arg_parser.parse_args()

    # We parse the --ignore option
    ignore_list = parse_ignore(arg_list.ignore)

    # We get the reverse run dictionary (run signature -> run_id) of both files
    input_reverse_run_dict = get_reverse_run_dict(
        arg_list.input_file, ignore_list)
    output_reverse_run_dict = get_reverse_run_dict(
        arg_list.output_file, ignore_list)

    # We match the runs of both files to get the run_id -> run_id mapping
    mapping = get_mapping_dict(input_reverse_run_dict, output_reverse_run_dict)

    # We turn the mapping into the list of commands to run
    cmd_list = generate_cmd_list(mapping, arg_list.command)

    # For each command,
    for cmd in cmd_list:
        logging.info(f"RUN:{cmd}\n")
        # if we have the --print option, we do not run it
        if(not(arg_list.print_only)):
            subprocess.run(cmd, shell=True)
