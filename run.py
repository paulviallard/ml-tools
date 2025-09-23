# Copyright © 2025 Paul Viallard <paul.viallard@gmail.com>
# This work is free. You can redistribute it and/or modify it under the
# terms of the Do What The Fuck You Want To Public License, Version 2,
# as published by Sam Hocevar. See http://www.wtfpl.net/ for more details.

import os
import re
import time
import itertools
import argparse
import configparser
import subprocess
import time
import logging
import glob

# Useful packages in the .ini files
import numpy as np
import math

###############################################################################


class LaunchConfig():

    def __init__(self, f, job_id_list):
        # We set the prefix of the job names (useful for slurm ...)
        self.prefix_run_name = "job_{}_".format(int(time.time()))

        # We save the ids of the jobs to execute
        self.job_id_list = job_id_list

        # We read the configuration file (.ini)
        config = configparser.ConfigParser(empty_lines_in_values=False)
        config.read(f)

        # We initialize the root of a tree. A node is organized as follows:
        # 1- Name of the jobs (name of the node)
        # 2- Name of the parent jobs (name of the parent node)
        # 3- "Data" of the job (i.e., hyperparameters, variables, command)
        # 4- Sub-tree containing the jobs that need to be run for every set of
        # hyperparameters
        # 5- Sub-tree containing the jobs that need to be run after the
        # previous sub-tree
        # 6- Flag to run sequentially the jobs of a node
        job_tuple = [None, None, None, [], [], False]
        self.job_tree = job_tuple

        # We initialize a dict to insert easily in the tree
        job_dict = {None: job_tuple}

        # We initialize the previous node that we have seen
        prog_previous = None

        # For every node of the tree (the sections in the ini file)
        for job_name in config.sections():

            # We remove the space in the sections of the ini file
            job_name_list = job_name.replace(" ", "")
            job_name_list = re.split(r'\s*(\|?->)\s*', job_name_list)

            # If the section can be rewritten as "[someth]"
            if(len(job_name_list) == 1):

                # We initialize the node of the tree with its "data"
                job_tuple = [job_name_list[0], prog_previous,
                             config[job_name], [], [], False]

                # We check if we need to run sequentially the jobs
                # and update the flag
                if re.match(r'^!', job_name_list[0]):
                    job_tuple[5] = True

                # We insert the new node in the dict
                job_dict[job_name_list[0]] = job_tuple
                # We insert the new node in the parent node
                job_dict[prog_previous][3].append(job_tuple)

                # We keep this node
                prog_previous = job_name_list[0]

            elif(len(job_name_list) == 3):

                # If the section can be rewriten as "[-> sth]"
                if(job_name_list[0] == ""):
                    # We initialize the node of the tree with its "data"
                    job_tuple = [job_name_list[2], prog_previous,
                                 config[job_name], [], [], False]

                    # We check if we need to run sequentially the jobs
                    # and update the flag
                    if re.match(r'^!', job_name_list[2]):
                        job_tuple[5] = True

                    # We insert the new node in the dict
                    job_dict[job_name_list[2]] = job_tuple
                    # We insert the new node in the parent node
                    job_dict[prog_previous][3].append(job_tuple)

                # If the section can be rewriten as "[sth1 |-> sth2]"
                elif(job_name_list[1] == "|->"):
                    # We initialize the node of the tree with its "data"
                    job_tuple = [job_name_list[2], job_name_list[0],
                                 config[job_name], [], [], False]

                    # We check if we need to run sequentially the jobs
                    # and update the flag
                    if re.match(r'^!', job_name_list[2]):
                        job_tuple[5] = True

                    # We insert the new node in the dict
                    job_dict[job_name_list[2]] = job_tuple
                    # We insert the new node in the node indicated by "someth1"
                    job_dict[job_name_list[0]][4].append(job_tuple)

                # If the section can be rewriten as "[sth1 -> sth2]"
                elif(job_name_list[1] == "->"):
                    # We initialize the node of the tree with its "data"
                    job_tuple = [job_name_list[2], job_name_list[0],
                                 config[job_name], [], [], False]

                    # We check if we need to run sequentially the jobs
                    # and update the flag
                    if re.match(r'^!', job_name_list[2]):
                        job_tuple[5] = True

                    # We insert the new node in the dict
                    job_dict[job_name_list[2]] = job_tuple
                    # We insert the new node in the parent node that is
                    # associated to "sth1"
                    job_dict[job_name_list[0]][3].append(job_tuple)

                # We keep this node
                prog_previous = job_name_list[2]

    def _get_param_list(self, param_list, known_param):

        # We get the params(, the variables and the command...)
        param_list = dict(param_list)

        # We remove the command
        if("command" in param_list):
            del param_list["command"]
        # We remove the variables
        for key in list(param_list.keys()):
            if(re.match("[$]{[^}]+}", key)):
                del param_list[key]

        # We create a todo list (see below)
        todo_param_list = {}

        # For each params
        for param_name in list(param_list.keys()):

            try:
                # We interpret the param
                known_param_ = dict(known_param)
                known_param_.update({"param_list": param_list})
                exec("param_list['" + param_name + "'] = "
                     + param_list[param_name], globals(), known_param_)

            except NameError:
                # If we cannot interpret the param, we add the param in the
                # todo list
                todo_param_list[param_name] = param_list[param_name]
                del param_list[param_name]
                continue

            # If the param is a dict, we need to transform it in a list of
            # params
            if(isinstance(param_list[param_name], dict)):

                # We get the dict
                param_dict = param_list[param_name]

                # If the elements of the dict are not a list, we create a list
                # with the element
                for key in param_dict:
                    if(not(isinstance(param_dict[key], list))):
                        param_dict[key] = [param_dict[key]]

                # We initialize a list
                param_str_list = []
                # For each combination of params in the dict
                for param in itertools.product(*param_dict.values()):
                    param = dict(zip(param_dict.keys(), param))

                    # We create a string with the params
                    param_str = ""
                    for key in sorted(param.keys()):
                        if(not(isinstance(param[key], str))):
                            param_str += key+"="+str(param[key])+","
                        else:
                            param_str += key+"=\""+str(param[key])+"\","
                    param_str = param_str[:-1]

                    # and we add it to the list
                    param_str_list.append(param_str)

                # We replace the dict by the list
                param_list[param_name] = param_str_list

            # If the parameter type is not a list
            if(not(isinstance(param_list[param_name], list))):
                # We create a list with the element
                param_list[param_name] = [param_list[param_name]]

        return param_list, todo_param_list

    def _get_var_list(self, param_list, known_param, known_var):

        # We get the variables (i.e., the params and the command...)
        var_list = dict(param_list)
        # We remove the params and the command
        for key in list(var_list.keys()):
            if(not(re.match("[$]{[^}]+}", key))):
                del var_list[key]

        # We update the list of variables with the previous ones
        known_var = dict(known_var)
        known_var.update(var_list)
        var_list = known_var

        # We add the params in the variables
        new_known_param = {}
        for param in known_param:
            new_known_param["${"+param+"}"] = str(known_param[param])
        known_var.update(new_known_param)

        # We create one special variable: ${params}
        # ${params} contains a list of params for the run
        var_list["${params}"] = ""
        for arg_name in sorted(list(known_param)):
            var_list["${params}"] += " --{}={}".format(
                arg_name, known_param[arg_name])
        var_list["${params}"] = var_list["${params}"][1:]

        # While the replacements are not stabilized
        terminated = False
        while not(terminated):
            terminated = True
            for var_name in var_list:
                for var_name_replace in var_list:
                    # We replace the name of the variables by their values
                    old_var_list = str(var_list[var_name])
                    var_list[var_name] = var_list[var_name].replace(
                        var_name_replace, var_list[var_name_replace])
                    if(old_var_list != var_list[var_name]):
                        terminated = False

        return var_list

    def _get_command(self, job_tree):
        # We get the command of the current job
        if("command" in job_tree[2]):
            return job_tree[2]["command"]

    def _construct_command(self, command, var_list):
        # For each variable
        for var_name in var_list:
            # We replace the variable by its content in the command
            command = command.replace(var_name, var_list[var_name])
        return command

    def run(self):
        # We initialize a run index (useful for slurm, oar ...)
        self.__run_index = 0
        # We run the jobs of the subtrees
        for prog_subtree in self.job_tree[3]:
            self._run(prog_subtree, prog_subtree[2], {}, {}, [])

    def _run(self, job_tree, param_list,
             known_param, known_var, known_dependency):

        # We keep the old parameters to check if there is a problem
        old_param_list = param_list

        # We get the list of the hyperparameters (of a given job)
        param_list, todo_param_list = self._get_param_list(
            param_list, known_param)

        # We initialize a list of run dependencies
        known_dependency = sorted(
            list(set(known_dependency)),
            key=lambda x: int(x.split('_')[-1]))
        dependency_1 = list(known_dependency)

        # For each combination of params
        for param in itertools.product(*param_list.values()):

            # We check if there is still some parameters to interpret
            if(len(todo_param_list) > 0):
                known_param_ = {
                    key: value for key, value in zip(param_list.keys(), param)}
                known_param_["run_id"] = self.__run_index

                # If we cannot interpret some parameters, there is a problem
                if(len(old_param_list) == len(todo_param_list)):
                    s_error = ', '.join(todo_param_list.keys())
                    if(len(todo_param_list) == 1):
                        s_error = "The parameter " + s_error + " is"
                    else:
                        s_error = "The parameters " + s_error + " are"
                    s_error += " not correct"
                    raise RuntimeError(s_error)

                # We update the known parameters before interpreting
                # recursively
                for key in known_param.keys():
                    if key not in known_param_:
                        known_param_[key] = known_param[key]

                # We run recursively the algorithm with the interpreted
                # parameters (to run the new loops ...)
                self._run(
                    job_tree, todo_param_list, known_param_,
                    known_var, known_dependency)
                continue

            # We increase the run index
            self.__run_index += 1
            # We create a name of this run
            run_name = self.prefix_run_name+str(self.__run_index)

            # We update our params for a given run
            param_ = dict(known_param)
            param_["run_id"] = self.__run_index
            param_["job_id"] = int(self.prefix_run_name[4:-1])
            param_.update(dict(zip(param_list.keys(), param)))

            # We update the variables for a given run
            var_ = dict(known_var)
            var_.update(self._get_var_list(job_tree[2], param_, var_))

            # We get the command
            command = self._get_command(job_tree)

            # If the command exists
            if(command is not None):
                # We interpret the command (with the variables)
                command = self._construct_command(command, var_)

                # We run the command if the job id is in the list
                if(self.job_id_list is None
                   or self.__run_index in self.job_id_list):
                    self._run_command(command, run_name, known_dependency)

            # Otherwise, if the command does not exist,
            # we decrease the run index
            else:
                self.__run_index -= 1

            # For each subtree (of type "[-> sth]" or "[sth1 -> sth2]")
            for job_subtree in job_tree[3]:

                # We update the dependencies: if the id is in the list
                # (and if the command exists), we add
                # the job id in the dependencies
                if((self.job_id_list is None
                   or self.__run_index in self.job_id_list)
                   and command is not None):
                    new_known_dependency = known_dependency+[run_name]
                else:
                    new_known_dependency = known_dependency

                # We run recursively the subtree (and we get the dependency)
                dependency_ = self._run(
                    job_subtree, job_subtree[2], param_,
                    var_, new_known_dependency)

                # We add the new dependencies in the list
                dependency_1 = sorted(
                    list(set(dependency_1 + dependency_)),
                    key=lambda x: int(x.split('_')[-1]))

            # We add our current run in the (first) dependency list if the job
            # id is in the list (and if the command exists)
            if((self.job_id_list is None
               or self.__run_index in self.job_id_list)
               and command is not None):
                dependency_1.append(run_name)
                dependency_1 = sorted(
                    list(set(dependency_1)),
                    key=lambda x: int(x.split('_')[-1]))

            # If we are in sequential mode, then, we need to update
            # the known dependency and run sequentially the jobs inside a node
            if(job_tree[5] is True):
                known_dependency = dependency_1

        # We create a second (and final) dependency list
        dependency_2 = list(dependency_1)

        # For each subtree (of type "[sth1 |-> sth2]")
        for job_subtree in job_tree[4]:

            # We run recursively the subtree (and we get the dependency)
            dependency_ = self._run(
                job_subtree, job_subtree[2],
                known_param, known_var, dependency_1)
            # We add the new dependencies in the list
            dependency_2 = sorted(
                list(set(dependency_2 + dependency_)),
                key=lambda x: int(x.split('_')[-1]))

        # We return the dependencies of the node
        return dependency_2

    def _run_command(self, command, run_name=None, job_list=None):
        # To be implemented!
        raise NotImplementedError


###############################################################################

class PrintLaunchConfig(LaunchConfig):

    def _run_command(self, command, run_name=None, dependency=None):
        # We create the message
        msg = "Job: {}".format(run_name)
        msg += " - Dependency: {}".format(", ".join(dependency))

        # We print the message
        logging.info(msg+"\n")
        logging.info("-"*len(msg)+"\n")

        # We print the command
        logging.info(command+"\n")


###############################################################################

class LocalLaunchConfig(LaunchConfig):

    def _run_command(self, command, run_name=None, job_list=None):
        # We execute the command in the shell
        subprocess.call(command, shell=True)


###############################################################################

class SlurmLaunchConfig(LaunchConfig):

    def __init__(self, f, job_id_list, config, queue, sleep):
        super().__init__(f, job_id_list)
        self.config = config
        self.queue = queue
        self.sleep = sleep
        self.__job_id_dict = {}

    def get_job_id(self, run_name):
        # We get the id of a job in the dict given the job name
        try:
            return self.__job_id_dict[run_name]
        except KeyError:
            return None

    def set_job_id(self, run_name, job_id):
        # We get the id of a job in the dict given the job name
        self.__job_id_dict[run_name] = job_id

    def get_job_queue_size(self):
        result = subprocess.run("squeue -u $(whoami)",
            shell=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, universal_newlines=True
        )
        job_queue_size = len(result.stdout.split("\n")[1:-1])
        return job_queue_size

    def _run_command(self, command, run_name=None, job_list=None):

        new_job_list = []
        if(job_list is not None):
            for run_name_ in job_list:
                job_id = self.get_job_id(run_name_)
                if(job_id is not None):
                    new_job_list.append(job_id)
        job_list = new_job_list

        # We get all the job id on which our job depends
        if(len(job_list) > 0):
            dependency = "--dependency=afterany:"
        else:
            dependency = ""
        for job_id in job_list:
            if(job_id is not None):
                dependency += str(job_id)+":"
        dependency = dependency[:-1]

        # We get the default configuration file
        config_file_list = glob.glob("./run_slurm_default*")
        if(len(config_file_list) == 0):
            raise RuntimeError(
                "There is no default configuration file for slurm")
        if(len(config_file_list) > 1):
            raise RuntimeError(
                "There is more than one default configuration file for slurm")
        config_file = config_file_list[0]

        # We get the right configuration file
        if(self.config is not None):
            config_file = None
            config_file_list = glob.glob("./run_slurm*")
            for config_file_ in config_file_list:
                if(config_file_ == f"./run_slurm_{self.config}".format()
                   or (config_file_ == f"./run_slurm_default_{self.config}")):
                    config_file = config_file_
                    continue
            if(config_file is None):
                raise RuntimeError(
                    "There is no configuration file"
                    + f"named {self.config} for slurm")

        # We put a job in the queue only if we have not reached the maximum
        # number of jobs in the queue we have fixed
        if(self.queue is not None):
            while(self.get_job_queue_size() >= self.queue):
                time.sleep(self.sleep)

        # We run the command to run oar
        result = subprocess.run("sbatch {} -J {} {} '{}'".format(
            dependency, run_name, config_file, command),
            shell=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, universal_newlines=True
        )
        logging.info("Executing sbatch {} -J {} {} '{}'\n".format(
            dependency, run_name, config_file, command)
        )
        print(result.stdout, end="")
        print(result.stderr, end="")

        # We get the job id and save it
        re_match = re.search(r'\d+', result.stdout)
        if(re_match):
            job_id = re_match.group(0)
            self.set_job_id(run_name, int(job_id))

###############################################################################

class OarLaunchConfig(LaunchConfig):

    def __init__(self, f, job_id_list, config, queue, sleep):
        super().__init__(f, job_id_list)
        self.config = config
        self.queue = queue
        self.sleep = sleep
        self.__job_id_dict = {}

    def get_job_id(self, run_name):
        # We get the id of a job in the dict given the job name
        try:
            return self.__job_id_dict[run_name]
        except KeyError:
            return None

    def set_job_id(self, run_name, job_id):
        # We get the id of a job in the dict given the job name
        self.__job_id_dict[run_name] = job_id

    def get_job_queue_size(self):
        result = subprocess.run("oarstat -u $(whoami)",
            shell=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, universal_newlines=True
        )
        job_queue_size = len(result.stdout.split("\n")[2:-1])
        return job_queue_size

    def _run_command(self, command, run_name=None, job_list=None):

        # NOTE: we can depend on only one job in OAR ...
        # So we will always depend on the highest job id in the list ...
        job_id = None
        i = len(job_list)-1
        while i >= 0 and job_id is None:
            job_id = self.get_job_id(job_list[-1])
            i -= 1
        if job_id is not None:
            dependency = "-a {}".format(job_id)
        else:
            dependency = ""

        # We get the default configuration file
        config_file_list = glob.glob("./run_oar_default*")
        if(len(config_file_list) == 0):
            raise RuntimeError(
                "There is no default configuration file for oar")
        if(len(config_file_list) > 1):
            raise RuntimeError(
                "There is more than one default configuration file for oar")
        config_file = config_file_list[0]

        # We get the right configuration file
        if(self.config is not None):
            config_file = None
            config_file_list = glob.glob("./run_oar*")
            for config_file_ in config_file_list:
                if(config_file_ == f"./run_oar_{self.config}".format()
                   or (config_file_ == f"./run_oar_default_{self.config}")):
                    config_file = config_file_
                    continue
            if(config_file is None):
                raise RuntimeError(
                    "There is no configuration file"
                    + f"named {self.config} for oar")

        # We put a job in the queue only if we have not attained the maximum
        # number of jobs in the queue we have fixed
        if(self.queue is not None):
            while(self.get_job_queue_size() >= self.queue):
                time.sleep(self.sleep)

        # We run the command to run oar
        result = subprocess.run("oarsub {} -n {} -S '{} {}'".format(
            dependency, run_name, config_file, command),
            shell=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, universal_newlines=True
        )
        logging.info("Executing oarsub {} -n {} -S '{} {}'\n".format(
            dependency, run_name, config_file, command)
        )
        print(result.stdout, end="")
        print(result.stderr, end="")

        # We get the job id and save it
        re_match = re.search(r'OAR_JOB_ID=(\d+)', result.stdout)
        if(re_match):
            job_id = re_match.group(1)
            self.set_job_id(run_name, int(job_id))

###############################################################################

if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    logging.StreamHandler.terminator = ""

    # ----------------------------------------------------------------------- #

    arg_parser = argparse.ArgumentParser(
        description='Execute the job described in the ini file')

    arg_parser.add_argument(
        "mode", metavar="mode", type=str,
        help="The mode of execution (either print, local, slurm, or oar)")
    arg_parser.add_argument(
        "path", metavar="path", type=str,
        help="The path of the ini file")
    arg_parser.add_argument(
        "--config", metavar="config", default=None, type=str,
        help="The configuration associated with the mode slurm or oar")
    arg_parser.add_argument(
        "--job", metavar="job", default=None, type=str,
        help="The job's id or the job_id_list of the jobs to execute")
    arg_parser.add_argument(
        "--queue", metavar="queue", default=None, type=int,
        help="The maximum number of jobs in the queue"
    )
    arg_parser.add_argument(
        "--sleep", metavar="sleep", default=None, type=int,
        help="The time (sec) before rechecking the number of jobs in the queue"
    )

    arg_list = arg_parser.parse_args()
    mode = arg_list.mode
    path = arg_list.path
    config = arg_list.config
    job = arg_list.job
    queue = arg_list.queue
    sleep = arg_list.sleep

    # We create the list of job id to execute
    job_id_list = None
    # If the option --job has been selected
    if(job is not None):

        # We create the list
        job_id_list = []

        # For each id range/id
        job_range_list = job.split(",")
        for job_range in job_range_list:

            # We get the ids in the "range"
            try:
                job_range = job_range.split(":")
                job_range = sorted([int(r) for r in job_range])
            except ValueError:
                arg_parser.error("--job: these are not valid job ids")

            if(len(job_range) > 2):
                arg_parser.error(
                    "--job: a range must contain 2 values only")

            # We add all the ids in the list
            if(len(job_range) == 2):
                job_range = list(range(job_range[0], job_range[1]+1))
            job_id_list = job_id_list+job_range

        # We sort the list
        job_id_list = sorted(job_id_list)

    if(mode != "print" and mode != "local"
       and mode != "slurm" and mode != "oar"
       ):
        arg_parser.error("mode: it must be either print, local, slurm or oar")
    if(not(os.path.exists(path))):
        arg_parser.error("path: {} does not exist".format(path))

    if(config is not None and (mode == "print" or mode == "local")):
        arg_parser.error("--config: it is only available for slurm or oar")
    if(queue is not None and (mode == "print" or mode == "local")):
        arg_parser.error("--queue: it is only available for slurm or oar")
    if(sleep is not None and (mode == "print" or mode == "local")):
        arg_parser.error("--sleep: it is only available for slurm or oar")
    if(sleep is None and (mode != "print" and mode != "local")):
        sleep = 60

    # ----------------------------------------------------------------------- #

    if(mode == "print"):
        PrintLaunchConfig(path, job_id_list).run()
    elif(mode == "local"):
        LocalLaunchConfig(path, job_id_list).run()
    elif(mode == "slurm"):
        SlurmLaunchConfig(path, job_id_list, config, queue, sleep).run()
    elif(mode == "oar"):
        OarLaunchConfig(path, job_id_list, config, queue, sleep).run()
