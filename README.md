<p align="center">
    <img src="../assets/oct.gif?raw=true">
</p>


# OCT file converter #

This repository contains code for extracting the raw optical coherence tomography (OCT) and fundus data from 
manufacturer's proprietary file formats. 

## Motivation
Research in ophthalmology is often hindered by manufacturer's usage of proprietary data formats for storing their data. 
For example, until recently, the ~200,000 OCT scans in the UK Biobank project was only available in Topcon's .fds
file format, which prevented bulk processing and analysis. The only freely available software that allows these scans
to be accessed is  [uocte](https://bitbucket.org/uocte/uocte/wiki/Home), which is written in C++ and is no longer 
maintained. This repository aims to make available python-based tools for reading these proprietary formats.


## Supported file formats
* .fds (Topcon)
* .fda (Topcon)
* .e2e (Heidelberg)
* .img (Zeiss)
* .dcm

## Installation
Requires **python3**.

```bash
pip install oct-converter
```


## Usage
A number of example usage scripts are included in examples/. 

Here is an example of reading a .fds file:

```python
from oct_converter.readers import FDS

# An example .fds file can be downloaded from the Biobank website:
# https://biobank.ndph.ox.ac.uk/showcase/refer.cgi?id=30
filepath = '/home/mark/Downloads/eg_oct_fds.fds'
fds = FDS(filepath)

oct_volume = fds.read_oct_volume()  # returns an OCT volume with additional metadata if available
oct_volume.peek() # plots a montage of the volume
oct_volume.save('fds_testing.avi')  # save volume as a movie
oct_volume.save('fds_testing.png')  # save volume as a set of sequential images, fds_testing_[1...N].png

fundus_image = fds.read_fundus_image()  # returns a  Fundus image with additional metadata if available
fundus_image.save('fds_testing_fundus.jpg')
```

## Contributions
Are welcome!

## Updates
30 October 2020
- Extract fundus and laterality data from .e2e
- Now attempts to extract additional volumetric data from .e2e files that was previously missed

22 August 2020
- Experimental support for reading OCT data from .fda files. 

14 July 2020
- Can now read fundus data from .fda files. 

