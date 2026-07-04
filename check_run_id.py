import os
import sys
import argparse
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run import LaunchConfig

###############################################################################


class CollectLaunchConfig(LaunchConfig):

    def __init__(self, f, job_id_list=None):
        self.__run_id_list = []
        super().__init__(f, job_id_list)

    def _run_command(self, command, run_name=None, job_list=None):
        # We get the run_id from the run name (job_<timestamp>_<run_id>)
        self.__run_id_list.append(int(run_name.split("_")[-1]))

    def get_run_id_list(self):
        return list(self.__run_id_list)

###############################################################################


def get_run_id_list(config_file):
    # We get, for a given .ini file, the list of run_id it describes
    config = CollectLaunchConfig(config_file)
    config.run()
    return config.get_run_id_list()


def get_missing_run_id_list(run_id_list, pattern):
    # We keep the run_id for which no result file matches the pattern
    missing_run_id_list = []
    for run_id in run_id_list:
        if(not(os.path.exists(pattern.format(run_id=run_id)))):
            missing_run_id_list.append(run_id)
    return missing_run_id_list


###############################################################################


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    logging.StreamHandler.terminator = ""

    # ----------------------------------------------------------------------- #

    arg_parser = argparse.ArgumentParser(
        description='Check the run_id with no matching result file')

    arg_parser.add_argument(
        "path", metavar="path", type=str,
        help="Path of the ini file describing the runs")
    arg_parser.add_argument(
        "pattern", metavar="pattern", type=str,
        help="Pattern of the result files, with {run_id}")

    arg_list = arg_parser.parse_args()

    # We get the run_id described in the .ini file
    run_id_list = get_run_id_list(arg_list.path)

    # We keep the ones with no matching result file
    missing_run_id_list = get_missing_run_id_list(
        run_id_list, arg_list.pattern)

    # We print them as a comma-separated list, ready to be used with --job
    logging.info(",".join(str(run_id) for run_id in missing_run_id_list)+"\n")
