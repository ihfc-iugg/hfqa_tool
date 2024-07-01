# hfqa_tool

- [Overview](#overview)
- [Documentation](#documentation)
- [System Requirements](#system-requirements)
- [Installation Guide](#installation-guide)
- [Setting up the development environment](#setting-up-the-development-environment)
- [Running code](#running-code)
- [Caution](#caution)
- [License](#license)
- [Issues](https://github.com/https://git-int.gfz-potsdam.de/chishti/heatflow-quality-analysis-code/issues)

# Overview

`hfqa_tool` is a Python package containing tools for independence testing of Heat Flow data quality and structure, adhering to a controlled vocabulary. This is developed in compliance with the paper by Fuchs et al. (2023) titled "[Quality-assurance of heat-flow data: The new structure and evaluation scheme of the IHFC Global Heat Flow Database](https://doi.org/10.1016/j.tecto.2023.229976)," published in Tectonophysics 863: 229976. Also revised for the newer release 2024.

# Documenation
The official documentation with usage is at: 
ReadTheDocs: 

# System Requirements
## Hardware requirements
`hfqa_tool` package requires only a standard computer with enough RAM to support the in-memory operations.

## Software requirements
### OS Requirements
This package is supported for *Windows*, *macOS* and *Linux*. The package has been tested on the following systems:
+ Windows: Windows 10 Pro
+ Linux: Ubuntu 

### Python Dependencies
`hfqa_tool` mainly depends on the Python scientific computing and file handling stack.

```
numpy
pandas
math
datetime
openpyxl
glob
os
```

# Installation Guide:

### Install from PyPi
```
pip3 install hfqa_tool
```

### Install from Github
```
git clone https://github.com/sfchishti/hfqa_tool.git
cd hfqa_tool
python3 setup.py install
```
- `sudo`, if required
- `python3 setup.py build_ext --inplace  # for cython`, if you want to test in-place, first execute this

# Setting up the development environment:

# Running code
- Run all sections of the code. Descriptions and guidelines are provided with the code.
- When prompted with `Please enter the file directory:`, provide the directory/location of your Heatflow data files. This can be done in the last section (*Example*) of the code, specifically in section 13.1 of the [Vocabulary_check](https://git-int.gfz-potsdam.de/chishti/heatflow-quality-analysis-code/-/blob/Vocabulary_check/Vocabulary_check.ipynb) code, and section 12.1 of the [Combined_score](https://git-int.gfz-potsdam.de/chishti/heatflow-quality-analysis-code/-/blob/Quality_score/Combined_score.ipynb) code.
- If running on Linux or Mac OS, use forward slashes /. On Windows, backward slashes \ will work fine when assigning your directory.
- Get results in the same folder :)
    
# Caution
- The worksheet name of Heat flow data must be named "data list", to execute conversion of the data set in machine readable format (here, *.csv*). Else the function `convert2UTF8csv(folder_path)` will not work.
![data_list Image](Graphics/data_list.png)
- When a new data release occurs and the relevancy (indicated by *'Obligation'*) of a column in the HF data structure is updated, make sure to place the data structure files with the updated column relevancy into separate folders before running the code.
- Ignore file conversion of *.xlsx* files to a readable format if a *.csv* version already exists.
- If changes are made to the original Heat Flow database file in *.xlsx* format, delete the previous *.csv* file and generate a new one using the `convert2UTF8csv(folder_path)` function as described in the *Example* section.

# License

This project is covered under the ** License**.
