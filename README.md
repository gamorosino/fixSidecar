# Fix Sidecar

## **Overview**

This script facilitates the conversion of DICOM files to NIfTI format and ensures the resulting JSON sidecar is compliant with BIDS (Brain Imaging Data Structure) metadata standards.

---

## Author

**Gabriele Amorosino** (gabriele.amorosino@utexas.edu)

---

### Key aspects:

1. **DICOM to NIfTI Conversion**:
   - Leverages `dcm2niix` to convert DICOM files to NIfTI format efficiently.
   - Outputs a `.nii` file along with a corresponding `.json` metadata sidecar.

2. **BIDS Metadata Compliance**:
   - Automatically updates the JSON sidecar to include required and optional BIDS fields.
   - Incorporates metadata from DICOM files, JSON sidecars, and optionally, scanner-specific Exam Cards (e.g., for Philips).

3. **Standalone Metadata Update**:
   - Provides a script to update an existing NIfTI JSON sidecar file with metadata from its corresponding DICOM file.
   - Ideal for cases where the NIfTI file already exists but the metadata requires enhancement or compliance adjustments.

4. **Metadata Enhancements**:
   - Computes missing fields like `SliceTiming`, `TotalReadoutTime`, `EffectiveEchoSpacing`, and `PhaseEncodingDirection` using the provided metadata sources.
  
### **Metadata Update Features**

1. **Metadata Extraction Hierarchy**:
   - Retrieves metadata (e.g., `RepetitionTime`, `PhaseEncodingSteps`, `NumberOfSlices`, `MultiBandFactor`) from the JSON file as the primary source.
   - Falls back to DICOM metadata if the JSON file lacks necessary information.
   - Parses additional missing values (like TR) from the Exam Card file.

2. **Slice Timing Calculation**:
   - Calculates `SliceTiming` based on the TR, number of slices, multi-band factor, and interleaved slice acquisition order.

3. **Slice Order Calculation**:
   - Computes the correct interleaved slice acquisition order for MB (Multi-Band) acquisitions.
   - Allows manual override with user-provided slice orders.

4. **Phase Encoding Direction**:
   - Determines `PhaseEncodingDirection` using:
     - JSON or DICOM metadata.
     - Exam Card fields (if available).

5. **Total Readout Time**:
   - Computes `TotalReadoutTime` using:
     - `PhaseEncodingSteps` and `EffectiveEchoSpacing` (from JSON or DICOM).
     - Exam Card parameters (`EPI factor` and `Bandwidth`).

6. **Comprehensive JSON Updates**:
   - Updates the following fields in the JSON sidecar:
     - `SliceTiming`
     - `TotalReadoutTime`
     - `EffectiveEchoSpacing`
     - `PhaseEncodingDirection`

---

## **Installation Guide**

To set up the repository and install dependencies:

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd <repository-folder>
```

### Step 2: Install Dependencies

#### Using Virtual Environment

Create a virtual environment and install required packages:

```bash
python3 -m venv env
source env/bin/activate  # For Linux/macOS
env\Scripts\activate   # For Windows

pip install -r requirements.txt
```

#### Using Conda

Alternatively, you can create an environment using Conda:

```bash
conda env create -f res/config/fixSidecar.yml
conda activate fixSidecar
```

---

## **Usage**

Run the script to convert DICOM files and update their metadata:

```bash
python dcm_convert.py <dicom_file> <output_dir> [options]
```

Or use the standalone script to update an existing NIfTI JSON sidecar:

```bash
python update_json_sidecar.py <dicom_file> <json_file> <output_file> [options]
```

### Arguments

For `dcm_convert.py`:

- `<dicom_file>`: Path to the DICOM file or directory.
- `<output_dir>`: Directory where the converted NIfTI and updated JSON files will be saved.
#### Options
- `--no-fmri`: Skip JSON-sidecar update (useful for structural or non-fMRI data).

For `update_json_sidecar.py`:

- `<dicom_file>`: Path to the DICOM file.
- `<json_file>`: Path to the existing JSON sidecar file.
- `<output_file>`: Path to save the updated JSON file.

#### Options

- `--exam-card`: Path to the Exam Card file (Philips scanners) for additional metadata.
- `--compute-slice-timing`: Enable calculation of `SliceTiming`.
- `--compute-total-readout`: Enable calculation of `TotalReadoutTime`.
- `--slice-order`: Provide a custom slice acquisition order (as a JSON string).
- `--tmp-dir`: Specify a temporary directory for intermediate processing.
- `--scanner-type`: Define the scanner type (default: "Philips").
- `--flip-phase-encoding-direction`: Toggle the sign of the phase encoding direction.
- `--phase-encoding-direction`: Manually provide the BIDS PhaseEncodingDirection (e.g., j, j-, i, i-)

---

## **Example Usage**

### Basic Conversion

```bash
python dcm_convert.py example_dicom_folder output_directory
```

### Advanced Usage with Metadata Fixes

```bash
python dcm_convert.py example_dicom_folder output_directory --compute-slice-timing --exam-card exam_card.txt --slice-order "[[0, 4, 8], [1, 5, 9], [2, 6, 10]]"
```

### Standalone Metadata Update

```bash
python update_json_sidecar.py example.dcm existing_metadata.json updated_metadata.json --compute-slice-timing --slice-order "[[0, 4, 8], [1, 5, 9], [2, 6, 10]]"
```

---

## **New Features in this version**

- **Manual Phase Encoding Direction**

  - Added support for the `--phase-encoding-direction` flag to both `dcm_convert.py` and `update_json_sidecar.py`.
  - This option allows users to manually specify the `PhaseEncodingDirection` (e.g., "j", "-j", "i", "-i").
  - If this option is used, automatic computation from DICOM or ExamCard is skipped.
  - The output JSON will include a new metadata field: `PhaseEncodingDirectionSource`, which will be set to either `"manual"` or `"computed"` depending on how the direction was determined.

- **Fallback Estimation from NIfTI**

  - If `PhaseEncodingSteps` or `NumberOfSlices` are not found in the JSON, DICOM headers, or ExamCard, the values are automatically estimated from the corresponding NIfTI image file.
  - This increases robustness when metadata is incomplete or inconsistently exported.


---

## **Notes**

- Ensure `dcm2niix` is installed and accessible in your system's PATH.
- Use the `--exam-card` option for Philips scanners to improve metadata accuracy.
- This script supports both individual DICOM files and directories containing multiple DICOMs.

---

## **Disclaimer**
- The script was developed and tested on only data from the Philips 3T Ingenia CX MRI Scanner at the Vanderbilt University Institute of Imaging Sciences (VUIIS) at Vanderbilt University. There may be inaccuracies introduced when applying this script to other MRI scanners; be sure to check all processes and outputs carefully, if applying to data from a different MRI scanner.
---

## Acknowledgments
This work was supported by the following grant:
NIH R01HD114489, CRCNS: Dense longitudinal neuroimaging to evaluate learning in childhood (Principal Investigator S. Vinci Booher)
