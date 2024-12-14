# fixSidecar# 

**DICOM JSON Update Script Documentation**

## **Overview**

This Python script is designed to update a BIDS-compliant JSON sidecar file using metadata extracted from:

- DICOM files.
- Optional Exam Card files (specific to Philips scanners).

The script calculates additional fields such as `SliceTiming`, `TotalReadoutTime`, and `PhaseEncodingDirection` to enhance the metadata.

---

## **Features**

1. **Slice Timing Calculation**
   - Calculates the timing of individual slices based on acquisition parameters.
2. **Phase Encoding Direction**
   - Determines the phase encoding direction using DICOM metadata or Exam Card fields.
   - Supports Siemens and Philips scanners.
3. **Total Readout Time Calculation**
   - Computes the total readout time using:
     - DICOM metadata (`EffectiveEchoSpacing` and `PhaseEncodingSteps`).
     - Exam Card parameters (`EPI factor` and `Bandwidth`).
4. **Exam Card Parsing**
   - Matches protocol details for a given series description in the Exam Card file.

---

## **Usage**

```bash
python script_name.py <dicom_file> <json_file> <output_file> <exam_card_file>
```

### **Arguments**

- `<dicom_file>`: Path to the input DICOM file.
- `<json_file>`: Path to the input JSON sidecar file.
- `<output_file>`: Path to save the updated JSON file.
- `<exam_card_file>`: Path to the Exam Card file for additional metadata (optional).

---

## **Function Descriptions**

### \*\*1. \*\***`calculate_slice_timing`**

```python
def calculate_slice_timing(tr, num_slices, mb_factor, slice_order, sets_per_tr)
```

- **Purpose**: Calculates the timing for each slice based on TR, number of slices, multiband factor, and slice acquisition order.
- **Inputs**:
  - `tr` (float): Repetition time in milliseconds.
  - `num_slices` (int): Total number of slices.
  - `mb_factor` (int): Multiband acceleration factor.
  - `slice_order` (list): Acquisition order of slices.
  - `sets_per_tr` (int): Number of sets per TR.
- **Output**: A list of slice timings in seconds.

---

### \*\*2. \*\***`calculate_total_readout_time`**

```python
def calculate_total_readout_time(phase_encoding_steps, effective_echo_spacing)
```

- **Purpose**: Computes the total readout time using DICOM metadata.
- **Inputs**:
  - `phase_encoding_steps` (int): Number of phase encoding steps.
  - `effective_echo_spacing` (float): Effective echo spacing in seconds.
- **Output**: Total readout time in seconds.

---

### \*\*3. \*\***`calculate_total_readout_time_from_exam_card`**

```python
def calculate_total_readout_time_from_exam_card(protocol_details)
```

- **Purpose**: Calculates the total readout time using Exam Card fields.
- **Inputs**:
  - `protocol_details` (str): Relevant protocol details extracted from the Exam Card.
- **Output**: Total readout time in seconds.

---

### \*\*4. \*\***`match_protocol_in_exam_card`**

```python
def match_protocol_in_exam_card(series_description, exam_card_path)
```

- **Purpose**: Matches the series description with the corresponding protocol in the Exam Card.
- **Inputs**:
  - `series_description` (str): The series description from the DICOM file.
  - `exam_card_path` (str): Path to the Exam Card file.
- **Output**: Matched protocol details as a string.

---

### \*\*5. \*\***`determine_phase_encoding_direction`**

```python
def determine_phase_encoding_direction(dicom_path, scanner_type="SIEMENS", exam_card_path=None)
```

- **Purpose**: Determines the phase encoding direction using:
  - DICOM metadata (`InPlanePhaseEncodingDirection`).
  - Exam Card fields (`EX_STACKS_0__prep_dir` and `EX_STACKS_0__fat_shift_dir`).
- **Inputs**:
  - `dicom_path` (str): Path to the DICOM file.
  - `scanner_type` (str): Scanner type (`"SIEMENS"` or `"PHILIPS"`).
  - `exam_card_path` (str, optional): Path to the Exam Card file.
- **Output**: BIDS-compliant phase encoding direction (`"j"`, `"j-"`, `"i"`, `"i-"`).

---

### \*\*6. \*\***`update_json_with_dicom_info`**

```python
def update_json_with_dicom_info(dicom_path, json_path, output_path, calculate_total_readout=False, scanner_type="SIEMENS", exam_card_path=None)
```

- **Purpose**: Updates a JSON sidecar with calculated metadata fields.
- **Inputs**:
  - `dicom_path` (str): Path to the DICOM file.
  - `json_path` (str): Path to the input JSON file.
  - `output_path` (str): Path to save the updated JSON file.
  - `calculate_total_readout` (bool): Flag to calculate total readout time from DICOM (if no Exam Card).
  - `scanner_type` (str): Scanner type (`"SIEMENS"` or `"PHILIPS"`).
  - `exam_card_path` (str, optional): Path to the Exam Card file.
- **Output**: None. Saves the updated JSON file to `output_path`.

---

### \*\*7. \*\***`print_help`**

```python
def print_help()
```

- **Purpose**: Prints usage information for the script.

---

## **Example Workflow**

```bash
python update_json_sidecar.py \
  example.dcm \
  example.json \
  updated_example.json \
  exam_card.txt
```

---

## **Notes**

- Ensure all required fields (`PhaseEncodingSteps`, `EffectiveEchoSpacing`, etc.) are available in the DICOM file or Exam Card.
- For Philips scanners, include the Exam Card to provide additional metadata.

---



