# Heat Flow Quality Analysis Tool (hfqa_tool)
`hfqa_tool` is a Python package for validating heat-flow data against the IHFC Global Heat Flow Database (GHFDB) schema and assessing data quality according to International Heat Flow Commission standards, including quality scoring based on the methodology described in [doi:10.1016/j.tecto.2023.229976](https://doi.org/10.1016/j.tecto.2023.229976)

## Table of contents 
- [Version History](#version-history)
- [Overview](#overview)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Vocabulary Validation](#vocabulary-validation)
- [Quality Scoring](#quality-scoring)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [Citation](#citation)
- [License](#license)

## Version History 

| Version | Branch / Repository | Status |
|---------|-------------------|--------|
| v0.2.0 *(current)* | [`main`](https://github.com/ihfc-iugg/hfqa_tool) | Active |
| v0.1.0 | [`v0.1.0-legacy`](https://github.com/ihfc-iugg/hfqa_tool/tree/v0.1.0-legacy) | Deprecated — please use `main` |

> **Note:** As of v0.2.0, the `main` branch of [ihfc-iugg/hfqa_tool](https://github.com/ihfc-iugg/hfqa_tool) reflects the current active version. The previous codebase has been preserved under the `v0.1.0-legacy` branch for reference but is no longer maintained.

## Overview

`Vocabulary Validation` ensures that data entries comply with the GHFDB database schema by verifying required fields, value ranges, allowed vocabularies, multi-value fields, conditional rules, and by reporting, field-specific errors.

`Quality Score` calculates U-scores (uncertainty quantification, U1-U4), M-scores (methodology assessment based on measurement techniques, M1-M4), and P-flags (perturbations effect such as topographic, paleoclimatic etc. )


## Installation:

### Prerequisites
- Python 3.8 or higher
- pip, conda package manager

### Install from Github 
```bash
git clone https://github.com/viktoriadergunova/hfqa_tool.git
cd hfqa_tool
pip install -r requirements.txt # install dependencies
```
### Dependencies
```
pandas>=2.0
pyarrow
openpyxl
pyyaml
```
### Data Preparation

Your Excel file must follow offical GHFDB structure: #TODO add image
```
Row 1-7:   Metadata rows (configurable)
Row 8:     Column headers (ID, Level, Obligation, P1, P2, P3, ...)
Row 9+:    Data rows
```

## Quick Start - Vocabulary Validation
```bash
python main.py --vocab-check --input your_data.xlsx 
```
**Parameters:**
- `--vocab-check`: Run vocabulary validation mode
- `--input`: Path to your Excel file
- `--out-json`: Option to get .json files, saved in /voc
- `--out-excel`: Option to get .xlsx files (default), saved in /voc folder
- `--meta-rows`: Number of metadata rows at the top of your Excel sheet (default: 7)
- `--sheet`: Sheet index to validate (default: 1)
- 
**Full example with all options:**
```bash
python main.py --input your_data.xlsx --vocab-check --out-json --sheet 1 --meta-rows 7 --debug-prefix debug_run 
```
### Understanding the Output 
#### JSON Report Structure
```json
{
  "violations": [
    {
      "row_excel_number": 8,
      "column": "P2",
      "site_name": "[Site-001]",
      "flag": "missing",
      "comment": "HF Uncertainty"
    }
  ],
  "summary": {
    "total_rows_in_sheet": 1000,
    "data_rows_validated": 993,
    "rows_with_any_error": 45,
    "functional_error_count": 78,
    "conditional_error_count": 12,
    "runtime_seconds": 2.34
  }
}
```
## Excel Output

The Excel output file contains all original input data and two additional columns that describe validation results and row classification:

- **`row_type`** – indicates whether the row represents metadata or data
- **`validation_comments`** – contains column dependent error descriptions
- Rows without validation issues have an empty `validation_comments` field.

**Format**
| … | P1 | P2 | P3 | row_type | validation_comments |
|---|----|----|----|----------|---------------------|
| … | 65.5 |    | Site-001 | data | `[MISSING] C47 (Thermal conductivity number): Required field is empty; [INVALID VALUE] C26 (Stratigraphy): Value 'late paleozoic orogeny' is not in allowed list` |
| … | 72.3 | 5.2 | Site-002 | data |  |

- **MISSING**: Required field is empty
- **RANGE**: Value outside valid range
- **INVALID**: Value not in vocabulary
- **CONDITIONAL**: Context-dependent rule violated 

## Quality Scoring

The quality scoring module evaluates heat-flow data according to IHFC standards, providing a comprehensive assessment through three independent components:

### Quick Start - Quality Scoring
```bash
python main.py --quality-score --input your_data.xlsx 
```

**Parameters:**
- `--quality-score`: Run quality scoring mode
- `--input`: Path to your Excel file
- `--out-json`: Option to get .json files, saved in /voc
- `--out-excel`: Option to get .xlsx files (default), saved in /qc folder
- `--meta-rows`: Number of metadata rows (default: 7)
- `--sheet`: Sheet index to process (default: 0)
- `--debug-prefix`: Optional prefix for debug output files

**Full example with all options:**
```bash
python main.py --input your_data.xlsx --quality-score --out-json --sheet 1 --meta-rows 7 --debug-prefix debug_run 
```

### Quality Score Components

The quality assessment consists of three independent scores that are combined into a final quality code:

#### 1. U-Score (Uncertainty Quantification)
Evaluates the numerical uncertainty of heat-flow determinations based on the coefficient of variation (COV):

**Calculation**
```
COV(%) = (Heat Flow Uncertainty / Heat Flow Mean) × 100
```

**Format**
| Score | COV Range | Description |
|-------|-----------|-------------|
| U1 | < 5% | Excellent - Very low uncertainty |
| U2 | 5-15% | Good - Low uncertainty |
| U3 | 15-25% | Acceptable - Moderate uncertainty |
| U4 | > 25% | Poor - High uncertainty |
| Ux | N/A | Not determined / missing data |


#### 2. M-Score (Methodological Quality)
Assesses the quality of measurement methods for both temperature gradient and thermal conductivity determinations. The evaluation differs for borehole/mine data versus probe-sensing data.

**Format**
| Score | Quality Range | Description |
|-------|---------------|-------------|
| M1 | ≥ 0.75 | Excellent methodology |
| M2 | 0.50-0.74 | Good methodology |
| M3 | 0.25-0.49 | Acceptable methodology |
| M4 | < 0.25 | Poor methodology |
| M*x | Any | Incomplete metadata (x-suffix indicates missing data) |


#### 3. P-Flags (Perturbation Effects)
A 7-character code indicating the status of environmental perturbations that may affect heat-flow measurements:

**Format:** `SxxxCxh` (example)

Each position represents a specific perturbation:
1. **S/s** - Sedimentation effects
2. **E/e** - Erosion effects
3. **T/t** - Topography/Bathymetry effects
4. **P/p** - Paleoclimate effects
5. **V/v** - Surface/Bottom water temperature variation
6. **C/c** - Convection/Fluid flow
7. **R/r** - Heat refraction effects

**Character meanings:**
- **Uppercase letter** (e.g., `S`, `E`) = Present and **corrected**
- **Lowercase letter** (e.g., `s`, `e`) = Present but **not corrected**
- **Uppercase `X`** = Present but **not significant**
- **Lowercase `x`** = **Not recognized** or not present
- **Dash `-`** = Unspecified/missing data

**Format:**
- `SxxxCxh` = Sedimentation corrected, convection not recognized, heat refraction present but not corrected
- `SETPV--` = Multiple effects corrected, convection and heat refraction unspecified
- `-------` = All perturbations unspecified

### Combined Quality Score

The final quality score combines all three components:

**Format::**
- `U1M1.SxxxCxh` - Excellent uncertainty, excellent methodology, specific perturbations
- `U2M3x.-------` - Good uncertainty, acceptable methodology with missing metadata, unspecified perturbations
- `U3M2.SETPVXR` - Acceptable uncertainty, good methodology, multiple perturbations addressed

If the input data contains `ID` and `ID_parent` columns, an additional `quality_score_inherited` column is added to the output, representing the worst quality score inherited from all relevant child entries (`C9 = [Yes]`) to the parent level, following the inheritance scheme described in Fuchs et al. (2023).

**Example:**

| ID_parent | ID | C9 | quality_score | quality_score_inherited |
|-----------|----|----|---------------|------------------------|
| 1 | 1 | `[Yes]` | `U1M2.xeTxxxx` | `U3M2.xeTxxxx` |
| 1 | 2 | `[Yes]` | `U3M1.xeTxxxx` | `U3M2.xeTxxxx` |
| 1 | 3 | `[Yes]` | `U2M2.xeTxxCx` | `U3M2.xeTxxxx` |
| 1 | 4 | `[No]`  | `U4M4.xeTxVCx` | `U3M2.xeTxxxx` |

The inherited score `U3M2.xeTxxxx` is derived as follows: worst U (`U3`) and worst M (`M2`) are taken independently across all relevant children (`C9 = [Yes]`); P-flags are taken from the child with the worst U score (`U3M1.xeTxxxx`), using M as tiebreaker. Child 4 is excluded as it is not marked as relevant (`C9 = [No]`).

### Output Files

#### JSON Quality Report
```json
{
  "summary": {
    "total_rows_processed": 150,
    "quality_distribution": {
      "U1": 45,
      "U2": 67,
      "U3": 28,
      "U4": 10,
      "M1": 34,
      "M2": 56,
      "M3": 42,
      "M4": 18
    },
    "runtime_seconds": 3.42
  },
  "data": [
    {
      "row": 9,
      "site_name": "Site-001",
      "quality_U": "U1",
      "quality_M": "M2",
      "quality_P": "SxxxCxh",
      "quality_combined": "U1M2.SxxxCxh"
    }
  ]
}
```

#### Excel Output
The Excel output includes all original data plus an additional column:
- **`quality_score`** - Combined quality code (e.g., `U1M2.SxxxCxh`)

## Contributing

We welcome contributions! Please see [ISSUEs.md](ISSUEs.md) 

## Citation 

If you use this tool in your research, please cite:

```bibtex
@article{fuchs2023quality,
  title = {Quality-assurance of heat-flow data: The new structure and evaluation 
           scheme of the IHFC Global Heat Flow Database},
  author = {Fuchs, Sven and others},
  journal = {Tectonophysics},
  volume = {863},
  pages = {229976},
  year = {2023},
  doi = {10.1016/j.tecto.2023.229976}
}
```

## Authors

- Viktoria Dergunova (GFZ)
- Elif  Balkan-Pazvantoğlu (GFZ)
- Ben Norden (GFZ)
- Florian Neumann (MARUM, University of Bremen)
- Samah Elbarbary (GFZ)
- Alexey G. Petrunin (GFZ)
- Sven Fuchs (GFZ)

See [AUTHORs.md](AUTHORs.md) for detailed affiliations and contributions.

## License

This project is dual-licensed:

- **Source code**: [MIT License](license/MIT.txt)
- **Documentation and images**: [CC-BY-4.0](license/CC-BY-4.0.txt)

---

**Maintained by the Section Geoenergy, GFZ Helmholtz Centre for Geosciences**












