# Fix Sidecar

## **Overview**

This tool converts DICOM files to NIfTI format and programmatically harmonizes the resulting JSON sidecar to ensure compliance with BIDS (Brain Imaging Data Structure) metadata standards.

Version **v0.7.0** introduces a generalized and extensible slice-order framework, legacy acquisition preservation, metadata provenance tracking, and improved CLI consistency.

---

## Author

**Gabriele Amorosino** ([gabriele.amorosino@utexas.edu](mailto:gabriele.amorosino@utexas.edu))

---

## Key Capabilities

### 1. DICOM to NIfTI Conversion

* Uses `dcm2niix` for robust DICOM → NIfTI conversion.
* Produces `.nii` images with accompanying `.json` metadata sidecars.
* Supports both single DICOM files and directory-based acquisitions.

### 2. BIDS Metadata Harmonization

* Automatically updates and validates required BIDS fields.
* Integrates metadata from:

  * JSON sidecar (primary source)
  * DICOM headers (fallback)
  * Optional Philips Exam Card files
* Ensures consistent unit handling and structured metadata output.

### 3. Standalone Metadata Update

* `update_json_sidecar.py` allows post-hoc correction of an existing JSON file.
* Useful when:

  * Metadata is incomplete
  * Conversion occurred externally
  * Additional compliance steps are required

### 4. Advanced Metadata Computation

The tool can compute and/or harmonize:

* `SliceTiming`
* `TotalReadoutTime`
* `EffectiveEchoSpacing`
* `PhaseEncodingDirection`
* `PhaseEncodingDirectionSource` (provenance annotation)

---

# Metadata Update Features (v0.7.0)

## 1. Hierarchical Metadata Resolution

Metadata is resolved in the following order:

1. JSON sidecar (primary)
2. DICOM header (fallback)
3. Exam Card (Philips-specific fallback)

This structured hierarchy increases robustness when working with partially exported datasets.

---

## 2. Generalized Slice-Order Framework (NEW in v0.7.0)

v0.7.0 introduces a flexible acquisition modeling system.

### Supported Slice-Order Modes

* `legacy`
  Preserves original lab-specific acquisition logic (MB=3 protocol).

* `ascending`
  Standard multi-band grouping in ascending shot order.

* `interleaved`
  Even–odd shot ordering.

* `stepped`
  Generalized cyclic stepping with configurable step size.

### Step Size Support

* `--slice-order-step` allows explicit control of stepping behavior.
* Default behavior:

  * `legacy` → step = 4 (backward compatible)
  * all other modes → step = 1

### Manual Override

* `--slice-order` allows direct specification of acquisition groups.
* Validation ensures:

  * full slice coverage
  * no duplicates
  * correct MB grouping

---

## 3. Slice Timing Computation

If `--compute-slice-timing` is enabled:

* Slice timing is reconstructed using:

  * TR
  * Number of slices
  * Multi-band factor
  * Derived slice-order

Supports:

* Automatic modes
* Stepped acquisitions
* Manual slice order definitions

---

## 4. Phase Encoding Direction

Determined via:

1. Manual override (`--phase-encoding-direction`)
2. Exam Card logic (Philips)
3. DICOM InPlanePhaseEncodingDirection

New in v0.7.0:

* Adds metadata field:

```json
"PhaseEncodingDirectionSource": "manual" | "computed"
```

This provides explicit provenance of the value.

---

## 5. Total Readout Time

Computed using:

* JSON `PhaseEncodingSteps` + `EffectiveEchoSpacing`
* Philips formula (Chris Rorden approach)
* Exam Card bandwidth + EPI factor
* Fallback to existing `EstimatedTotalReadoutTime`

Automatic ms → seconds normalization is applied when necessary.

---

## Installation

### Clone

```bash
git clone <repository-url>
cd <repository-folder>
```

### Virtual Environment

```bash
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
```

### Conda

```bash
conda env create -f res/config/fixSidecar.yml
conda activate fixSidecar
```

---
# Usage

Run the script to convert DICOM files and update their metadata:

```bash
python dcm_convert.py <dicom_file> <output_dir> [options]
```

Or use the standalone script to update an existing NIfTI JSON sidecar:

```bash
python update_json_sidecar.py <dicom_file> <json_file> <output_file> [options]
```

---

# Arguments

## For `dcm_convert.py`

### Required

* `<dicom_file>`
  Path to a DICOM file or a directory containing DICOM files.

* `<output_dir>`
  Directory where the converted NIfTI file and updated JSON sidecar will be saved.

---

### Optional Flags

* `--no-fmri`
  Skip JSON-sidecar update (useful for structural or non-fMRI data).

* `--exam-card <path>`
  Path to a Philips Exam Card file for additional metadata extraction.

* `--compute-slice-timing`
  Enable calculation of `SliceTiming`.

* `--compute-total-readout`
  Enable calculation of `TotalReadoutTime`.

* `--slice-order "<json_string>"`
  Provide a custom slice acquisition order as a JSON-formatted string.
  Example:

  ```bash
  --slice-order "[[0,12,24],[1,13,25],[2,14,26]]"
  ```

* `--slice-order-mode legacy|ascending|interleaved|stepped`
  Automatic slice-order strategy (used only if `--slice-order` is not provided).

  * `legacy` – preserves original lab-specific MB=3 behavior
  * `ascending` – sequential MB grouping
  * `interleaved` – even–odd shot ordering
  * `stepped` – generalized cyclic stepping

* `--slice-order-step <int>`
  Step size for slice-order calculation.
  Used for:

  * `slice-order-mode=stepped`
  * `slice-order-mode=legacy` (defaults to 4 if not specified)

* `--tmp-dir <path>`
  Specify a temporary directory for intermediate processing.

* `--scanner-type <type>`
  Define scanner type (default: `"Philips"`).

* `--flip-phase-encoding-direction`
  Toggle the sign of the inferred phase encoding direction.

* `--phase-encoding-direction <dir>`
  Manually provide the BIDS `PhaseEncodingDirection`.
  Examples: `j`, `j-`, `i`, `i-`
  If provided, automatic inference is skipped and provenance is recorded.

* `--version`
  Display tool version, Python version, and platform information.

---

## For `update_json_sidecar.py`

### Required

* `<dicom_file>`
  Path to the DICOM file.

* `<json_file>`
  Path to the existing JSON sidecar file.

* `<output_file>`
  Path where the updated JSON file will be written.

---

### Optional Flags

* `--exam-card <path>`
  Path to a Philips Exam Card file.

* `--compute-slice-timing`
  Enable calculation of `SliceTiming`.

* `--slice-order "<json_string>"`
  Provide a custom slice acquisition order (overrides automatic modes).

* `--slice-order-mode legacy|ascending|interleaved|stepped`
  Automatic slice-order strategy if `--slice-order` is not provided.

* `--slice-order-step <int>`
  Step size used for:

  * `stepped` mode
  * `legacy` mode (defaults to 4)

* `--phase-encoding-direction <dir>`
  Manually specify `PhaseEncodingDirection`.

* `--flip-phase`
  Toggle the sign of the inferred phase encoding direction.

* `--version`
  Display script version and system information.

---

# Example Usage

### Basic Conversion

```bash
python dcm_convert.py example_dicom_folder output_directory
```

### Stepped Acquisition Example

```bash
python dcm_convert.py example_dicom_folder output_directory \
    --compute-slice-timing \
    --slice-order-mode stepped \
    --slice-order-step 3
```

### Manual Phase Encoding Direction

```bash
python dcm_convert.py example_dicom_folder output_directory \
    --phase-encoding-direction "-j"
```

### Standalone JSON Update

```bash
python update_json_sidecar.py example.dcm existing.json updated.json \
    --compute-slice-timing \
    --slice-order-mode interleaved
```

---

# Versioning

Both scripts support:

```bash
--version
```

Which reports:

* Tool version
* Python version
* Platform information

---

# Notes

* Requires `dcm2niix` available in system PATH.
* Designed and validated primarily on Philips 3T Ingenia CX systems.
* Cross-scanner use should be validated carefully.

---

# Disclaimer

This software was developed and tested using data from the Philips 3T Ingenia CX MRI Scanner at the Vanderbilt University Institute of Imaging Sciences (VUIIS). Application to other scanners may require verification of acquisition assumptions and output correctness.

---

# Acknowledgments

This work was supported by the following grant:
NIH R01HD114489, CRCNS: Dense longitudinal neuroimaging to evaluate learning in childhood (Principal Investigator S. Vinci Booher)

We also thank **Eric Wilkey** for helpful feedback that improved this tool.
