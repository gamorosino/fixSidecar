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

## Conversion + Harmonization

```bash
python dcm_convert.py <dicom_file> <output_dir> [options]
```

## Standalone Metadata Update

```bash
python update_json_sidecar.py <dicom_file> <json_file> <output_file> [options]
```

---

# CLI Options (v0.7.0)

### Common Options

* `--compute-slice-timing`
* `--compute-total-readout`
* `--exam-card`
* `--scanner-type`
* `--flip-phase-encoding-direction`
* `--phase-encoding-direction`

### Slice-Order Options

* `--slice-order-mode legacy|ascending|interleaved|stepped`
* `--slice-order-step <int>`
* `--slice-order "<json_string>"`

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