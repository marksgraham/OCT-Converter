# Topcon OCT converter

This repository contains code for extracting the raw OCT and Fundus data from Topcon's .fds file format. The code is based on the file format specification in [uocte](https://bitbucket.org/uocte/uocte/wiki/Home), but adapted for the files output by the Topcon 3D OCT-1000 Mark II, used in the UK Biobank study.

## Getting started
- Adjust the filepath in `python/demo_fds_extraction` to point your your `.fds` file and run it
- There is a matlab version available to - run `matlab/demo_fds_extraction.m`

## Notes
- Currently the code only provides methods for extracting the OCT/fundus data, but there tends to be more data in the FDS file. All the available sections can be found in the `chunk_dict` dictionary (in the python code). This [wiki](https://bitbucket.org/uocte/uocte/wiki/Topcon%20File%20Format) provides some information on how these sections may be read.