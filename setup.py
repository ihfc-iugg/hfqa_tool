from setuptools import setup, find_packages

setup(
    name="hfqa_tool",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        'numpy>=1.18.0',
        'pandas>=1.0.0',
        'openpyxl>=3.0.0',
        # 'glob', 'os', 'datetime', 'warnings', 're' and 'math' are part of the standard library
    ],
    author="Saman Firdaus Chishti"
    author_email="chishti@gfz-potsdam.de",
    description=(
        "`hfqa_tool` is a Python package containing tools for independent testing of "
        "Heat Flow data quality and structure, adhering to a controlled vocabulary. This "
        "is developed in compliance with the paper by Fuchs et al. (2023) titled "
        "[Quality-assurance of heat-flow data: The new structure and evaluation scheme of "
        "the IHFC Global Heat Flow Database](https://doi.org/10.1016/j.tecto.2023.229976), "
        "published in Tectonophysics 863: 229976. Also revised for the newer release 2024."
    ),
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url="https://github.com/sfchishti/hfqa_tool",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",  # Use the appropriate license
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    contributors= ["Elif Balkan-Pazvantoğlu", "Ben Norden", "Florian Neumann", "Samah Elbarbary", "Eskil Salis Gross", "Sven Fuchs"]
)
