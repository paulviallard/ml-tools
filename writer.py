# Copyright © 2026 Paul Viallard <paul.viallard@gmail.com>
# This work is free. You can redistribute it and/or modify it under the
# terms of the Do What The Fuck You Want To Public License, Version 2,
# as published by Sam Hocevar. See http://www.wtfpl.net/ for more details.

import io
import os
import re
import h5py
import numpy as np
import pandas as pd

###############################################################################


class Writer():

    def __init__(self, file_):
        # We save the path associated with the data
        self._path_file = os.path.abspath(file_)

    # ----------------------------------------------------------------------- #

    def _load(self):
        # We load the data
        os.makedirs(os.path.dirname(self._path_file), exist_ok=True)
        self._data = h5py.File(self._path_file, "a")

    def _close(self):
        # We close the data
        self._data.close()

    # ----------------------------------------------------------------------- #

    def set(self, data_dict, path_dict, mode="r"):
        # NOTE: Here is the different mode to save the data:
        # "w" -> erase existing data
        # "a" -> append the data to the existing one
        # "r" -> do not erase the existing data, but write if no data

        # We load the data
        self._load()

        # We first check that the values/keys in the path_dict are of type str
        for key in path_dict.keys():
            if(not(isinstance(key, str))):
                self._close()
                raise ValueError("The keys in path_dict must be of type str")
            if(not(isinstance(path_dict[key], str))):
                self._close()
                raise ValueError("The values in path_dict must be of type str")

        # We check that the keys in the data_dict have the type str and
        # the values in the data_dict are compatible with a hdf5 file
        for key in data_dict.keys():
            if(not(isinstance(key, str))):
                self._close()
                raise ValueError("The keys in data_dict must be of type str")
            if(not(self.__ishdf5compatible(data_dict[key]))):
                self._close()
                raise ValueError(f"The values in data_dict must be compatible"
                                 + " with an hdf5 file")

        # We create the name of the path from the path dict
        path_name = self.__path_dict_to_path_name(path_dict)

        # We create the groups in the hdf5 file if necessary
        if(path_name != ""):
            group = self._data.require_group(path_name)
        else:
            group = self._data

        # For each key in the data dict
        for key in data_dict.keys():

            # If we are in the mode "w", we erase the existing data
            if(key in group and mode == "w"):
                del group[key]

            # If we are in the mode "a", we append the data if there is some
            # data in the path key of the hdf5 file
            if(key in group and mode == "a"):
                # We get the old shape and we update it
                old_shape_list = list(group[key].shape)
                shape_list = list(self.__getshape(data_dict[key]))
                if(len(shape_list) == 0):
                    shape_list = [1]

                # If the data do not have the same dimensions,
                # there is a problem
                if(len(old_shape_list) != len(shape_list)):
                    self._close()
                    raise ValueError("Shapes differ")
                if(old_shape_list[1:] != shape_list[1:]):
                    self._close()
                    raise ValueError("Shapes differ beyond the 1st dimension")

                # If there is no problem, we append the data
                shape_list[0] = shape_list[0] + old_shape_list[0]
                group[key].resize(shape_list)
                group[key][old_shape_list[0]:] = data_dict[key]

            # If there is no existing data in the group
            if(key not in group):
                # We set the data in the hdf5 file
                if(mode == "w" or mode == "r"):
                    group.create_dataset(
                        key, data=data_dict[key])
                elif(mode == "a"):
                    # If we are in the mode "a", we need first to get the
                    # shape of the data to set maxshape and we set the data
                    shape_list = list(self.__getshape(data_dict[key]))
                    if(len(shape_list) > 0):
                        shape_list[0] = None
                        group.create_dataset(
                            key, maxshape=shape_list, data=data_dict[key])
                    else:
                        group.create_dataset(
                            key, maxshape=[None], data=[data_dict[key]])
                else:
                    # We raise an error and close the data
                    self._close()
                    raise ValueError("mode must be either r, w, or a")

        # We close the data
        self._close()

    # ----------------------------------------------------------------------- #

    def __ishdf5compatible(self, data):
        # We open a mock dataset in a buffer and we load the dataset in the
        # buffer
        try:
            with io.BytesIO() as buffer:
                with h5py.File(buffer, "w") as f:
                    f.create_dataset("test", data=data)
            # If we have no problem to set the data, then the data is
            # compatible with the hdf5 file
            return True
        except Exception as e:
            # Otherwise, we have a problem
            return False

    def __getshape(self, value):
        # We open a mock dataset in a buffer and we load the dataset in the
        # buffer to check the shape
        try:
            with io.BytesIO() as buffer:
                with h5py.File(buffer, "w") as f:
                    f.create_dataset("test", data=value)
                    return f["test"].shape
        except Exception as e:
            # Normally, this must never happen
            return None

    # ----------------------------------------------------------------------- #

    def __path_dict_to_path_name(self, path_dict):
        # We initialize the path
        path_name = ""

        # We remove the None values in the path_dict
        path_dict = dict(path_dict)
        for key in list(path_dict.keys()):
            if(path_dict[key] is None):
                del path_dict[key]

        # For each key,
        for key in sorted(list(path_dict.keys())):
            # we add in the path the key and the values
            path_name += "{}={}/".format(
                key, path_dict[key])
        # We remove the last character "/"
        path_name = path_name[:-1]
        return path_name

    def __path_dict_to_path_name_list(self, path_dict):
        # We initialize the list
        path_name_list = []

        # We get the size of the lists in the dict
        dict_size = self.__dict_size(path_dict)

        # For each path,
        for i in range(dict_size):
            # we create a temporary dict
            path_dict_ = {}
            for key in path_dict.keys():
                path_dict_[key] = path_dict[key][i]

            # we get the name of the current path associated with the
            # temporary dict
            path_name = self.__path_dict_to_path_name(path_dict_)

            # we append the name of the path in the list
            path_name_list.append(path_name)

        # We return the list
        return path_name_list

    def __path_name_to_path_dict(self, path_name):

        path_dict = {}

        # We split the path name to get all the values
        for key_val in path_name.split("/"):
            # For each value, we split it again to obtain the "key" and "val"
            # from "key=val"
            key_val = re.split("[=,]", key_val)

            # If we have "key=val"
            if(len(key_val) == 2):
                # We get the "key"
                key = key_val[0]
                key = key.replace("-", "_")
                # We get the "val"
                val = key_val[1]
                # and we save in the dictionary
                path_dict[key] = val
            elif(len(key_val) == 1):
                continue
            else:
                # Otherwise, we raise an error and close the data
                self._close()
                raise RuntimeError("We must have the key=val in the path")

        return path_dict

    def __get_dict_to_path_dict_data_dict(self, get_dict):
        # We separate the data_dict and the path_dict
        data_dict = {}
        path_dict = {}
        for key in get_dict:
            if key.endswith("_data"):
                data_dict[key[:-5]] = get_dict[key]
            elif key.endswith("_path"):
                path_dict[key[:-5]] = get_dict[key]
        return path_dict, data_dict

    def __data_dict_to_squeeze_data_dict(self, data_dict):

        # We get the size of the lists in the dict
        dict_size = self.__dict_size(data_dict)

        squeeze_data_dict = {}
        for key in data_dict.keys():
            squeeze_data_dict[key] = []
            for i in range(dict_size):
                val = data_dict[key][i]
                if(val is None):
                    val = np.nan
                elif(isinstance(val, np.ndarray)):
                    val = np.squeeze(val)
                    if(len(val.shape) == 0):
                        val = val.item()
                squeeze_data_dict[key].append(val)

        return squeeze_data_dict

    def __dict_size(self, dict):
        dict_size = 0
        if(len(dict) > 0):
            dict_size = len(dict[list(dict.keys())[0]])
        return dict_size

    # ----------------------------------------------------------------------- #

    def __filter_path(self, path_dict, filter_path_fun):
        # If there is no filter, we ... do not filter
        if(filter_path_fun is None):
            return True
        # otherwise, we filter the path to check
        return filter_path_fun(**path_dict)

    def __filter_data(self, data, path_dict, filter_data_fun):
        # If there is no filter, we return None
        if(filter_data_fun is None):
            return None
        # otherwise, we filter the data to check
        return filter_data_fun(data, **path_dict)

    # ----------------------------------------------------------------------- #

    def get_pandas(
        self, data_list=None, path_dict=None,
        filter_data=None, filter_path=None
    ):
        # We get the path_dict and the data_dict
        path_dict, data_dict = self.__get(
            data_list=data_list, path_dict=path_dict,
            filter_data=filter_data, filter_path=filter_path,
            all=True)

        # We transform it in the pandas dataframe
        path_name_list = self.__path_dict_to_path_name_list(path_dict)
        data_dict = self.__data_dict_to_squeeze_data_dict(data_dict)
        data = pd.DataFrame(data_dict, index=path_name_list)

        return data

    def get_numpy(
        self, data_list=None, path_dict=None,
        filter_data=None, filter_path=None
    ):

        # We get the pandas dataframe
        data = self.get_pandas(
            data_list=data_list, path_dict=path_dict,
            filter_data=filter_data, filter_path=filter_path)
        # We transform into the numpy ndarray
        data = data.to_numpy()

        return data

    def get(
        self, data_list=None, path_dict=None,
        filter_data=None, filter_path=None,
        info=False, all=False, squeeze=True
    ):

        get_dict = self.__get(
            data_list=data_list, path_dict=path_dict,
            filter_data=filter_data, filter_path=filter_path,
            info=info, all=all)

        if(not(all)):
            data_dict = get_dict
            if(squeeze):
                data_dict = self.__data_dict_to_squeeze_data_dict(data_dict)
            return data_dict
        else:
            path_dict, data_dict = get_dict
            if(squeeze):
                data_dict = self.__data_dict_to_squeeze_data_dict(data_dict)
            return path_dict, data_dict


    def __get(
        self, data_list=None, path_dict=None,
        filter_data=None, filter_path=None, info=False, all=False):

        # We load the data
        self._load()

        # If we have a list of datasets and a path dict, this is a special case
        # and we can construct the filter
        if(data_list is not None and path_dict is not None):

            def filter_data_list_path_dict(data, **kwargs):
                for key in path_dict.keys():
                    if(key not in kwargs or kwargs[key] != path_dict[key]):
                        return False
                if(data not in data_list):
                    return False
                return True

            def filter_path_list_path_dict(**kwargs):
                for key in path_dict.keys():
                    if(key in kwargs and kwargs[key] != path_dict[key]):
                        return False
                return True

            filter_data = filter_data_list_path_dict
            filter_path = filter_path_list_path_dict

        # If we have a path dict but no list of datasets, this is a speicial
        # case where the get all the datasets (that are filtered)
        if(data_list is None and path_dict is not None):

            def filter_data_list_path_dict(data, **kwargs):
                return True

            def filter_path_list_path_dict(**kwargs):
                for key in path_dict.keys():
                    if(key in kwargs and kwargs[key] != path_dict[key]):
                        return False
                return True

            filter_data = filter_data_list_path_dict
            filter_path = filter_path_list_path_dict

        # We return the get
        get_dict = self.__get_(
            self._data, filter_data=filter_data, filter_path=filter_path,
            info=info
        )

        # Then, we separate the data_dict and the path_dict
        path_dict, data_dict = self.__get_dict_to_path_dict_data_dict(get_dict)

        # We close the data
        self._close()

        if(not(all)):
            return data_dict
        return path_dict, data_dict

    def __get_(self, group, filter_data=None, filter_path=None, info=False):

        # We initialize the dict to return
        get_dict = {}

        # We return the dict associated with the path
        path_dict = self.__path_name_to_path_dict(group.name)

        # If the filter of the path is not ok, we return an empty dictionary
        if(not(self.__filter_path(path_dict, filter_path))):
            return get_dict

        # If we have a dataset, then, we add it to get_dict if the filter is ok
        if(isinstance(group, h5py.Dataset)):
            name = group.name.split("/")[-1]
            if(self.__filter_data(name, path_dict, filter_data)):
                if(not(info)):
                    get_dict[name+"_data"] = [np.copy(group[()])]
                else:
                    get_dict[name+"_data"] = [(group.shape, group.dtype)]

        # If we have a group, we aim to merge all the datasets and subgroup
        # in the dict
        if(isinstance(group, h5py.Group)):

            # We first focus on the datasets to merge in the dict
            for child_name, child in group.items():

                if(isinstance(child, h5py.Dataset)):

                    get_dict_ = self.__get_(
                        child, filter_data, filter_path, info)

                    # If we have a filter and that the get_dict of
                    # the (child) subgroup is not empty
                    if(filter_data is not None and len(get_dict_) > 0):

                        # This is a special case: we create the get_dict with
                        # the path and the datasets
                        if(len(get_dict) == 0):
                            for key in path_dict.keys():
                                get_dict[key+"_path"] = [path_dict[key]]
                        for key in get_dict_.keys():
                            get_dict[key] = get_dict_[key]

                    # If we there is no filter, we do not get the datasets
                    # but we get the path
                    elif(filter_data is None):
                        if(len(get_dict) == 0):
                            for key in path_dict.keys():
                                get_dict[key+"_path"] = [path_dict[key]]


            # Now, that we have the datasets of this level, we can get (and
            # merge) with the subgroups
            for child_name, child in group.items():

                if(isinstance(child, h5py.Group)):
                    get_dict_ = self.__get_(
                        child, filter_data, filter_path, info)

                    # Now we need to merge the datasets and the values
                    # associated with the path

                    # To do so, we get the number of elements we have
                    # in the lists (in the group and the child subgroups)
                    try:
                        get_dict_size = len(
                            next(iter(get_dict.values())))
                    except StopIteration:
                        get_dict_size = 0
                    try:
                        get_dict_size_ = len(
                            next(iter(get_dict_.values())))
                    except StopIteration:
                        get_dict_size_ = 0

                    # Then, we update get_dict
                    for key in get_dict_.keys():
                        if key not in get_dict:
                            get_dict[key] = (
                                [None]*get_dict_size + get_dict_[key])
                        else:
                            get_dict[key] = (
                                get_dict[key]+get_dict_[key])
                    for key in get_dict.keys():
                        if key not in get_dict_:
                            get_dict[key] = (
                                get_dict[key] + [None]*get_dict_size_)

        return get_dict

    # ----------------------------------------------------------------------- #

    def filter(
        self, data_list=None, path_dict=None,
        filter_data=None, filter_path=None
    ):

        # We load the data
        self._load()

        # If we have a list of datasets and a path dict, this is a special case
        # and we can construct the filter
        if(data_list is not None and path_dict is not None):

            def filter_data_list_path_dict(data, **kwargs):
                for key in path_dict.keys():
                    if(key not in kwargs or kwargs[key] != path_dict[key]):
                        return True
                if(data not in data_list):
                    return True
                return False

            def filter_path_list_path_dict(**kwargs):
                for key in path_dict.keys():
                    if(key in kwargs and kwargs[key] != path_dict[key]):
                        return True
                return False

            filter_data = filter_data_list_path_dict
            filter_path = filter_path_list_path_dict

        # If we have a path dict but no list of datasets, this is a speicial
        # case where the get all the datasets (that are filtered)
        if(data_list is None and path_dict is not None):

            def filter_data_list_path_dict(data, **kwargs):
                return False

            def filter_path_list_path_dict(**kwargs):
                for key in path_dict.keys():
                    if(key in kwargs and kwargs[key] != path_dict[key]):
                        return True
                return False

            filter_data = filter_data_list_path_dict
            filter_path = filter_path_list_path_dict

        # We define the negation of the filters
        def neq_filter_data(*args, **kwargs):
            result = filter_data(*args, **kwargs)
            if(result is None):
                return None
            else:
                return not(result)

        def neq_filter_path(*args, **kwargs):
            result = filter_path(*args, **kwargs)
            if(result is None):
                return None
            else:
                return not(result)

        if(filter_data is None):
            neq_filter_data = None
        if(filter_path is None):
            neq_filter_path = None

        # We return the get with the information and not the datasets
        get_dict = self.__get_(
            self._data, filter_data=neq_filter_data,
            filter_path=neq_filter_path, info=True
        )

        # Then, we separate the data_dict and the path_dict
        path_dict, data_dict = self.__get_dict_to_path_dict_data_dict(get_dict)

        # We filter (i.e., remove the data in the hdf5 file)
        self.__filter_(path_dict, data_dict)

        # We close the data
        self._close()

    def __filter_(self, path_dict, data_dict):

        # We get the size in the dict
        filter_size = self.__dict_size(path_dict)

        # For each dataset that we want to remove
        for i in range(filter_size):

            # We get the name of the path
            path_dict_ = {}
            for key in path_dict.keys():
                path_dict_[key] = path_dict[key][i]
            path_name = self.__path_dict_to_path_name(path_dict_)

            # We remove the datasets that we want to remove
            for key in data_dict.keys():
                if(data_dict[key][i] is not None):
                    del self._data[f"{path_name}/{key}"]

            # We get the group associated with the path
            group = self._data
            if(path_name != ""):
                group = self._data[f"{path_name}"]

            # We delete the groups "recursively" if they are empty
            while(group != self._data and len(group.items()) == 0):
                group_ = group.parent

                group_path = group.name
                group_name = group_path.rsplit("/", 1)[-1]
                del group_[group_name]

                group = group_

    # ----------------------------------------------------------------------- #

    def __str__(self):

        def filter_data(data, **kwargs):
            return True

        path_dict, data_dict = self.__show(
            filter_data=filter_data, filter_path=None)

        # We get the string that we need to show
        string = self.__show_(path_dict, data_dict, "")
        return string


    def show(
        self, data_list=None, path_dict=None,
        filter_data=None, filter_path=None, to_print=True
    ):
        path_dict, data_dict = self.__show(
            data_list=data_list, path_dict=path_dict,
            filter_data=filter_data, filter_path=filter_path)

        # We get the string that we need to show
        string = self.__show_(path_dict, data_dict, "")

        # We print or return the string
        if(to_print):
            print(string)
        else:
            return string


    def __show(
        self, data_list=None, path_dict=None,
        filter_data=None, filter_path=None
    ):

        # We load the data
        self._load()

        # If we have a list of datasets and a path dict, this is a special case
        # and we can construct the filter
        if(data_list is not None and path_dict is not None):

            def filter_data_list_path_dict(data, **kwargs):
                for key in path_dict.keys():
                    if(key not in kwargs or kwargs[key] != path_dict[key]):
                        return False
                if(data not in data_list):
                    return False
                return True

            def filter_path_list_path_dict(**kwargs):
                for key in path_dict.keys():
                    if(key in kwargs and kwargs[key] != path_dict[key]):
                        return False
                return True

            filter_data = filter_data_list_path_dict
            filter_path = filter_path_list_path_dict

        # If we have a path dict but no list of datasets, this is a speicial
        # case where the get all the datasets (that are filtered)
        if(data_list is None and path_dict is not None):

            def filter_data_list_path_dict(data, **kwargs):
                return True

            def filter_path_list_path_dict(**kwargs):
                for key in path_dict.keys():
                    if(key in kwargs and kwargs[key] != path_dict[key]):
                        return False
                return True

            filter_data = filter_data_list_path_dict
            filter_path = filter_path_list_path_dict

        # We return the get with the information and not the datasets
        get_dict = self.__get_(
            self._data, filter_data=filter_data, filter_path=filter_path,
            info=True
        )

        # Then, we separate the data_dict and the path_dict
        path_dict, data_dict = self.__get_dict_to_path_dict_data_dict(get_dict)

        # We close the data
        self._close()

        return path_dict, data_dict


    def __show_(self, path_dict, data_dict, prefix=""):

        # We initialize the line_list to show
        line_list = []

        # If we have nothing in the path, it means that we have reached the
        # place where there is (maybe) some datasets to show
        if(len(path_dict) == 0):

            # For each key in data_dict
            for key in sorted(data_dict.keys()):

                # We check if there is a dataset to show
                if(data_dict[key][0] is not None):

                    # We generate the string
                    data = data_dict[key][0]

                    line_list.append(
                        f"{prefix}- {key}"
                        + f" (shape={data[0]}, dtype={data[1]})")

            # and return the string constituted of the datasets
            return "\n".join(line_list)

        # Otherwise, we need to handle the path
        # To do so, we get the key (of the current subgroup)
        key = list(path_dict.keys())[0]

        # We need to handle (recursively) all the values of the key
        while(len(path_dict[key]) > 0):

            # We get the first key/value in the path
            # (which is the root of the subgroup)
            val = path_dict[key][0]

            # If the value is not None, we print the value of the group
            if(val is not None):
                line_list.append(f"{prefix}> {key}={val}")

            # Now, we need to prepare for the recursion

            # Firstly, we check how many values are the same in the current
            # path_dict
            len_val = 0
            for val_ in path_dict[key]:
                if(val_ == val):
                    len_val += 1
                else:
                    break

            # Secondly, we prepare the path_dict and the data_dict for the next
            # subgroup thanks to len_val
            path_dict_ = dict(path_dict)
            del path_dict_[key]
            for key_ in path_dict_.keys():
                if(key != key_):
                    path_dict_[key_] = path_dict_[key_][:len_val]
            data_dict_ = dict(data_dict)
            for key_ in data_dict_.keys():
                data_dict_[key_] = data_dict_[key_][:len_val]

            # Thirdly, we prepare the prefix, and add some space
            # if we go deeper in the tree
            prefix_ = prefix
            if(val is not None):
                prefix_ = prefix + "  "

            # We get the line_list of the (next) subgroup
            # and we append it to the line_list of the current group
            line_list_ = self.__show_(path_dict_, data_dict_, prefix_)
            if(line_list_ != ""):
                line_list.append(line_list_)

            # Finally, we remove the current values associated with the group
            # and handle the next value associated with the key
            path_dict[key] = path_dict[key][len_val:]
            for path_key in path_dict.keys():
                if(key not in path_key):
                    path_dict[path_key] = path_dict[path_key][len_val:]

            for data_key in data_dict.keys():
                data_dict[data_key] = data_dict[data_key][len_val:]

        # We return the line_list
        return "\n".join(line_list)

###############################################################################
