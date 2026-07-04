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


def get_job_string(run_id_list):
    # We compress the consecutive run_id into ranges, to build a string
    # usable with run.py's --job option (e.g. "1,3,5:8")
    run_id_list = sorted(run_id_list)

    # We split the run_id into (start, end) ranges of consecutive values
    range_list = []
    for run_id in run_id_list:
        if(len(range_list) > 0 and run_id == range_list[-1][1]+1):
            range_list[-1][1] = run_id
        else:
            range_list.append([run_id, run_id])

    # We turn each range into a string: a single run_id, or "start:end"
    str_list = []
    for start, end in range_list:
        if(start == end):
            str_list.append(str(start))
        else:
            str_list.append(f"{start}:{end}")
    return ",".join(str_list)


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

    # We print them as a compressed, comma-separated list of ranges,
    # ready to be used with --job
    logging.info(get_job_string(missing_run_id_list)+"\n")
