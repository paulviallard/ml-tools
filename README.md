**ml-tools** is a small collection of standalone scripts for running machine learning experiments: a job runner to launch parameter sweeps (locally, on Slurm, or on OAR) from a single .ini file, a writer to collect results into hdf5 files (and merge them), and a helper to re-match result files with their new run_id when an experiment's .ini file is edited.

### Description of the tools

* **A system for running different scripts at once (in _run.py_)**

The file *run.py* allows you to run different commands described in a .ini file.
The script is able to (1) print the commands to execute, (2) to run them on the computer, and (3) to launch them on a Slurm/OAR cluster.

* **A class to save Python objects (in _writer.py_)**

The file *writer.py* contains a class handling the saving of Python objects in an hdf5 file.

* **A script to merge saved files (in _merge.py_)**

The file *merge.py* merges several files created by *writer.py* (matching a glob pattern) into a single output file.

* **A script to map run_id between two .ini files (in _map_run_id.py_)**

The file *map_run_id.py* matches the runs of two *run.py* .ini files (by comparing their command and parameters) and runs a command for each matched pair, substituting `{input_run_id}`/`{output_run_id}`. This is useful, for instance, to rename result files after the .ini file was edited and the run_id changed.

* **A script to find missing results (in _check_run_id.py_)**

The file *check_run_id.py* reads a *run.py* .ini file and checks, for every run_id it describes, whether a result file matching a given pattern (e.g. `results/results_{run_id}.h5`) exists. It prints the run_id with no matching file as a comma-separated list, ready to be passed to `run.py`'s `--job` option to re-run only the missing ones.

### Running the examples

##### writer.py
To run the example, you need to execute the following command in your bash shell.
```bash
python example/example_writer.py
```

##### run.py
To run the example, you need to execute the following command in your bash shell.
```bash
# Print the commands described in the .ini file, without running them
python run.py print example/example_run.ini

# Run them locally, one after the other
python run.py local example/example_run.ini

# Only run a subset of the jobs (job 1, job 3, and jobs 5 to 8)
python run.py local example/example_run.ini --job=1,3,5:8
```

For Slurm/OAR, *run.py* needs a batch script template: by default, it uses the file starting with `run_slurm_default` (resp. `run_oar_default`) at the root of the repository (there must be exactly one such default file). Passing `--config=myconfig` makes it use `run_slurm_myconfig` or `run_slurm_default_myconfig` instead (resp. `run_oar_myconfig`/`run_oar_default_myconfig`), so you can keep several templates around (e.g. one per partition or GPU type) and pick one at launch time.

```bash
# Launch them on a Slurm cluster with the run_slurm_default template,
# keeping at most 20 jobs in the queue at once
python run.py slurm example/example_run.ini --queue=20 --sleep=60

# Same, but using a "gpu" template: you need a run_slurm_gpu (or
# run_slurm_default_gpu) file for this to work
python run.py slurm example/example_run.ini --config=gpu --queue=20 --sleep=60

# Launch them on an OAR cluster with the run_oar_default template
python run.py oar example/example_run.ini

# Same, but using a "gpu" template: you need a run_oar_gpu (or
# run_oar_default_gpu) file for this to work
python run.py oar example/example_run.ini --config=gpu
```

##### map_run_id.py
To run the example, you need to execute the following command in your bash shell.
```bash
python map_run_id.py example/example_run.ini example/example_run_2.ini \
    "echo {input_run_id} -> {output_run_id}" --print
```

##### check_run_id.py
To run the example, you need to execute the following command in your bash shell.
```bash
python check_run_id.py example/example_run.ini "results/results_{run_id}.h5"
```
