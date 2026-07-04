import argparse
import logging
import glob
from writer import Writer

###############################################################################


def main():
    logging.basicConfig(level=logging.INFO)
    logging.StreamHandler.terminator = ""

    arg_parser = argparse.ArgumentParser(
        description='Merge the writers following input_pattern'
                    'into output_file')

    arg_parser.add_argument(
        "--input_pattern", metavar="input_pattern", type=str, required=True,
        help="input_pattern")
    arg_parser.add_argument(
        "--output_file", metavar="output_file", type=str, required=True,
        help="output_file")

    arg_list = arg_parser.parse_known_args()[0]

    input_pattern = arg_list.input_pattern
    output_file = arg_list.output_file

    # ----------------------------------------------------------------------- #

    # We create the output file
    output_writer = Writer(output_file)

    # We get the input files
    input_file_list = sorted(glob.glob(input_pattern))

    # For each file,
    for input_file in input_file_list:

        logging.info(f"[{i+1}/{len(input_file_list)}]\r")

        # we open it
        input_writer = Writer(input_file)

        def filter(*args, **kwargs):
            return True

        # and we get the data
        path_dict, data_dict = input_writer.get(
            filter_data=filter, all=True, squeeze=False)

        # we save the data in the output file
        for i in range(len(list(path_dict.values())[0])):

            path_dict_ = {}
            for key in path_dict.keys():
                path_dict_[key] = path_dict[key][i]
            data_dict_ = {}
            for key in data_dict.keys():
                data_dict_[key] = data_dict[key][i]

            output_writer.filter(data_dict_.keys(), path_dict_)
            output_writer.set(
                data_dict=data_dict_,
                path_dict=path_dict_,
            )

    logging.info("\n")

###############################################################################


if __name__ == "__main__":
    main()
