# Fix Sidecar

## **Overview**

This Python script updates a BIDS-compliant JSON sidecar file using metadata extracted from:

- JSON sidecar files as the primary source.
- DICOM files (as fallback).
- Optional Exam Card files (specific to Philips scanners).

The script calculates and updates additional metadata fields such as `SliceTiming`, `TotalReadoutTime`, `EffectiveEchoSpacing`, and `PhaseEncodingDirection`.

---

## **Features**

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

## **Usage**

```bash
python update_json_sidecar.py <dicom_file> <json_file> <output_file> <exam_card_file> [--compute-slice-timing] [--slice-order <slice_order>]
```

### **Arguments**

- `<dicom_file>`: Path to the input DICOM file.
- `<json_file>`: Path to the input JSON sidecar file.
- `<output_file>`: Path to save the updated JSON file.
- `<exam_card_file>`: Path to the Exam Card file for additional metadata (optional).

### **Options**

- `--compute-slice-timing`: Enable the calculation of `SliceTiming`.
- `--slice-order`: Provide a custom slice order as a string representation of a list of lists.
   - Example:
     ```bash
     --slice-order "[[0, 4, 8], [1, 5, 9], [2, 6, 10]]"
     ```

---

## **Example Workflow**

### **Basic Usage**

```bash
python update_json_sidecar.py example.dcm example.json updated_example.json exam_card.txt --compute-slice-timing
```

### **Custom Slice Order**

```bash
python update_json_sidecar.py example.dcm example.json updated_example.json exam_card.txt --slice-order "[[0, 18, 36], [4, 22, 40]]"
```

---

## **Function Descriptions**

### 1. **`calculate_slice_timing`**

```python
def calculate_slice_timing(tr, num_slices, mb_factor, slice_order, sets_per_tr)
```

- **Purpose**: Calculates the slice timing based on the TR, number of slices, and slice order.
- **Inputs**:
   - `tr`: Repetition time (ms).
   - `num_slices`: Total number of slices.
   - `mb_factor`: Multi-band factor.
   - `slice_order`: Slice acquisition order.
   - `sets_per_tr`: Number of sets per TR.
- **Output**: List of slice timings in seconds.

---

### 2. **`calculate_correct_slice_order`**

```python
def calculate_correct_slice_order(num_slices, mb_factor)
```

- **Purpose**: Computes the correct interleaved slice acquisition order for MB acquisitions.
- **Inputs**:
   - `num_slices`: Total number of slices.
   - `mb_factor`: Multi-band factor.
- **Output**: List of lists representing the slice acquisition order.

---

### 3. **`parse_tr_from_exam_card`**

```python
def parse_tr_from_exam_card(protocol_details)
```

- **Purpose**: Parses the TR (Repetition Time) from the Exam Card file, handling various formats such as `Act. TR/TE (ms): 1500 / 30`.
- **Inputs**:
   - `protocol_details`: Text content of the Exam Card file.
- **Output**: TR value in milliseconds.

---

### 4. **`update_json_with_dicom_info`**

```python
def update_json_with_dicom_info(dicom_path, json_path, output_path, ...)
```

- **Purpose**: Updates the JSON sidecar file with the following metadata:
   - `SliceTiming`
   - `TotalReadoutTime`
   - `EffectiveEchoSpacing`
   - `PhaseEncodingDirection`
- **Metadata Source Hierarchy**:
   1. JSON file (primary source).
   2. DICOM file (fallback).
   3. Exam Card file (for missing values, e.g., TR).
- **Inputs**:
   - `dicom_path`: Path to the DICOM file.
   - `json_path`: Path to the input JSON sidecar.
   - `output_path`: Path to save the updated JSON file.
   - Additional flags for slice timing and manual slice order.

---

## **Updates in Version**

1. **Fallback to JSON for Metadata**:
   - Retrieves key parameters like `PhaseEncodingSteps`, `EffectiveEchoSpacing`, `RepetitionTime`, `NumberOfSlices`, and `MultiBandFactor` directly from the JSON file.

2. **Improved Exam Card TR Parsing**:
   - Handles multiple TR formats, e.g., `1500 / 30` or `3200`.

3. **Robust Slice Order Calculation**:
   - Efficient interleaved group generation for MB acquisitions.

4. **Extensive Logging**:
   - Prints extracted and calculated parameters (e.g., `TR`, `Slice Order`, `Total Readout Time`).

---

## **Notes**

- Use `--compute-slice-timing` to enable `SliceTiming` calculation.
- Include the Exam Card file for Philips scanners to provide missing parameters like `TR` or `MB Factor`.
