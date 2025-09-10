# Copyright © 2025 Paul Viallard <paul.viallard@gmail.com>
# This work is free. You can redistribute it and/or modify it under the
# terms of the Do What The Fuck You Want To Public License, Version 2,
# as published by Sam Hocevar. See http://www.wtfpl.net/ for more details.

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from writer import Writer
import numpy as np

# We define the filters that are needed for the example
def filter_data_fun(data, **kwargs):
    return True

def filter_path_fun(key1=None, key2=None, **kwargs):
    if(key2 is not None):
        return key2 in ["val2"]
    return True

def filter_data_del_fun(data, key1=None, key2=None, **kwargs):
    if(data in ["col1", "col2", "key1"]):
        return True
    return False

def filter_data_all_fun(data, key1=None, key2=None, **kwargs):
    return True

# We initialize the test hdf5 file
data = Writer("test.h5")

# We set the data in the hdf5 file
data.set(
    {"key1": "bouh", "col1": 0.0123, "col2": [[0.1]]}, {"key1": "val1", "key2": "val2"},
mode="a")
data.set(
    {"col1": 0.19, "col2": [[0.81]]}, {"key1": "val1", "key2": "val3"},
mode="a")
data.set({"col1": 0.021}, {})
data.set({"col2": [0.1223]}, {"key1": "val1"})

data.set({"col3": ["a"]}, {"key1": "val1", "key2": "val2"})
data.set({"col3": ["b"]}, {"key1": "val1", "key2": "val2"})
data.set({"col3": ["a"]}, {"key1": "val1"})
data.set({"col3": ["val4"]}, {"key2": "val2"})
data.set(
    {"col4": np.random.rand(2,10)}, {"key1": "val1", "key2": "val3"}, mode="a")
data.set(
    {"col4": np.random.rand(1,10)}, {"key1": "val1", "key2": "val3"}, mode="a")
data.set({"col5": ["a"]}, {"key2": "val4"})

# We test some functions
print(data)
print("------------------------------------------")
data.show(filter_data=filter_data_all_fun)
print("------------------------------------------")
data.show(filter_data=filter_data_all_fun, filter_path=filter_path_fun)
print("==========================================")
data.show(filter_data=filter_data_del_fun)
print("------------------------------------------")
data.filter(filter_data=filter_data_del_fun)
data.show(filter_data=filter_data_all_fun)
print("==========================================")
data_ = data.get(filter_data=filter_data_all_fun)
print(data_)
print("------------------------------------------")
data_ = data.get(filter_data=filter_data_all_fun, all=True)
print(data_)
print("------------------------------------------")
data_ = data.get_pandas(filter_data=filter_data_all_fun)
print(data_)
print("------------------------------------------")
data_ = data.get_numpy(filter_data=filter_data_all_fun)
print(data_)
print("==========================================")
data_ = data.get(["col2"], {"key1": "val1"})
print(data_)
data_ = data.get_pandas(["col2"], {"key1": "val1"})
print(data_)
data_ = data.get_numpy(["col2"], {"key1": "val1"})
print(data_)
print("------------------------------------------")
data.show(["col2"], {"key1": "val1"})
data.filter(["col2"], {"key1": "val1", "key2": "val2"})
data.show(["col2"], {"key1": "val1"})

# We remove the csv file
os.remove("test.h5")
