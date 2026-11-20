import argparse
import logging
import glob
import numpy as np
from writer import Writer

###############################################################################


def get_key(path_dict, name, suffix_list):
    # We look for the key of the path that is the name followed by one of
    # the suffixes (e.g., iter_start for the name iter and the suffix start)
    for key in path_dict:
        for suffix in suffix_list:
            if(key == f"{name}_{suffix}" and path_dict[key] is not None):
                return key
    # If there is no such key, we return None
    return None


def get_start_key(path_dict, name):
    # We get the key of the beginning of the slice (e.g., iter_start
    # or iter_begin for the name iter)
    return get_key(path_dict, name, ["start", "begin"])


def get_end_key(path_dict, name):
    # We get the key of the end of the slice (e.g., iter_end or
    # iter_stop for the name iter)
    return get_key(path_dict, name, ["end", "stop"])


# ----------------------------------------------------------------------- #


def to_number(key, value):
    # We transform the value in the path into a number
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        raise ValueError(f"The value of {key} must be a number: {value}")


def get_range(path_dict, name):
    # We get the beginning and the end of the slice
    start_key = get_start_key(path_dict, name)
    end_key = get_end_key(path_dict, name)
    return (to_number(start_key, path_dict[start_key]),
            to_number(end_key, path_dict[end_key]))


# ----------------------------------------------------------------------- #


def get_slice_dict(slice_list, name):
    # We group the slices that only differ by their range
    slice_dict = {}
    for path_dict, data_dict in slice_list:
        # We get the path without the range
        range_key_list = [
            get_start_key(path_dict, name), get_end_key(path_dict, name)]
        path_dict_ = {
            key: value for key, value in path_dict.items()
            if key not in range_key_list}

        # The slices are grouped by this path and by the datasets
        slice_key = (
            tuple(sorted(path_dict_.items())),
            tuple(sorted(data_dict.keys())))
        if(slice_key not in slice_dict):
            slice_dict[slice_key] = []
        slice_dict[slice_key].append((path_dict, data_dict))
    return slice_dict


def merge_slice(slice_1, slice_2, name):
    path_dict_1, data_dict_1 = slice_1
    path_dict_2, data_dict_2 = slice_2

    # The path of the merged slice is the one of the first slice, with the
    # end of the second slice
    path_dict = dict(path_dict_1)
    end_key_1 = get_end_key(path_dict_1, name)
    path_dict[end_key_1] = path_dict_2[get_end_key(path_dict_2, name)]

    # We concatenate the datasets along the first axis
    # (np.atleast_1d transforms a single value into an array)
    data_dict = {}
    for key in data_dict_1.keys():
        try:
            data_dict[key] = np.concatenate(
                [np.atleast_1d(data_dict_1[key]),
                 np.atleast_1d(data_dict_2[key])], axis=0)
        except ValueError as error:
            raise ValueError(
                f"Cannot concatenate {key} of {path_dict}: {error}")
    return path_dict, data_dict


def merge_slice_list(slice_list, name):
    # We sort the slices by their range
    slice_list = sorted(
        slice_list, key=lambda slice_: get_range(slice_[0], name))

    # We merge each slice in the previous one if it follows it
    merged_slice_list = [slice_list[0]]
    for slice_ in slice_list[1:]:
        # (it follows the previous one if it begins where the previous ends)
        _, end = get_range(merged_slice_list[-1][0], name)
        start, _ = get_range(slice_[0], name)
        if(start == end):
            merged_slice_list[-1] = merge_slice(
                merged_slice_list[-1], slice_, name)
        else:
            merged_slice_list.append(slice_)
    return merged_slice_list


def get_concat_slice_list(slice_list, name):
    # For each group of slices that only differ by their range,
    # we merge the slices that follow each other
    concat_slice_list = []
    for same_slice_list in get_slice_dict(slice_list, name).values():
        concat_slice_list += merge_slice_list(same_slice_list, name)
    return concat_slice_list


###############################################################################


def main():
    logging.basicConfig(level=logging.INFO)
    logging.StreamHandler.terminator = ""

    arg_parser = argparse.ArgumentParser(
        description='Merge the writers following input_pattern'
                    'into output_file')

    arg_parser.add_argument(
        "--input_pattern", metavar="input_pattern", type=str, required=True,
        help="The pattern of the files to merge (e.g., results/res_*.h5)")
    arg_parser.add_argument(
        "--output_file", metavar="output_file", type=str, required=True,
        help="The path of the file that contains the merged data")
    arg_parser.add_argument(
        "--concat", metavar="concat", type=str, default=None,
        help="The name of the slices to concatenate "
             "(e.g., iter for iter_start and iter_end)")

    arg_list = arg_parser.parse_known_args()[0]

    input_pattern = arg_list.input_pattern
    output_file = arg_list.output_file
    concat = arg_list.concat

    # ----------------------------------------------------------------------- #

    # We create the output file
    output_writer = Writer(output_file)

    # We get the input files
    input_file_list = sorted(glob.glob(input_pattern))

    # We keep the slices to concatenate
    slice_list = []

    # For each file,
    for i, input_file in enumerate(input_file_list):

        logging.info(f"[{i+1}/{len(input_file_list)}]\r")

        # we open it
        input_writer = Writer(input_file)

        def filter(*args, **kwargs):
            return True

        # and we get the data
        path_dict, data_dict = input_writer.get(
            filter_data=filter, all=True, squeeze=False)

        # we save the data in the output file
        for j in range(len(list(path_dict.values())[0])):

            path_dict_ = {}
            for key in path_dict.keys():
                path_dict_[key] = path_dict[key][j]
            data_dict_ = {}
            for key in data_dict.keys():
                data_dict_[key] = data_dict[key][j]

            # (if it is a slice to concatenate, we keep it for later)
            if(concat is not None
               and get_start_key(path_dict_, concat) is not None
               and get_end_key(path_dict_, concat) is not None):
                slice_list.append((path_dict_, {
                    key: value for key, value in data_dict_.items()
                    if value is not None}))
                continue

            output_writer.filter(data_dict_.keys(), path_dict_)
            output_writer.set(
                data_dict=data_dict_,
                path_dict=path_dict_,
            )

    # We concatenate the slices that follow each other and we save them
    for path_dict_, data_dict_ in get_concat_slice_list(slice_list, concat):
        output_writer.filter(data_dict_.keys(), path_dict_)
        output_writer.set(
            data_dict=data_dict_,
            path_dict=path_dict_,
        )

    logging.info("\n")

###############################################################################


if __name__ == "__main__":
    main()
