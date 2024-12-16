import pydicom
import json
import numpy as np
import os
import sys


def calculate_slice_timing(tr, num_slices, mb_factor, slice_order, sets_per_tr):
    set_interval = (tr / 1000) / sets_per_tr  # Convert TR from ms to seconds
    slice_timing = np.zeros(num_slices)
    
    for i, slice_group in enumerate(slice_order):
        for slice_index in slice_group:
            slice_timing[slice_index] = i * set_interval
    return slice_timing.tolist()


def calculate_total_readout_time(phase_encoding_steps, effective_echo_spacing):
    """Calculate Total Readout Time using DICOM metadata."""
    return (phase_encoding_steps - 1) * effective_echo_spacing


def calculate_total_readout_time_from_exam_card(protocol_details):
    """Calculate Total Readout Time using EPI factor and bandwidth from exam card."""
    epi_factor = None
    bandwidth = None

    for line in protocol_details.splitlines():
        if "EPI factor" in line:
            epi_factor = int(line.split(":")[-1].strip())
        elif "WFS (pix) / BW (Hz)" in line:
            bandwidth = float(line.split("/")[-1].strip().split()[0])

    if epi_factor is None or bandwidth is None:
        raise ValueError("EPI factor or bandwidth not found in exam card protocol.")

    effective_echo_spacing = 1 / bandwidth
    total_readout_time = (epi_factor - 1) * effective_echo_spacing
    return total_readout_time


def match_protocol_in_exam_card(series_description, exam_card_path):
    """Match the series description with the corresponding protocol in the exam card."""
    matched_protocol = []
    capture = False
    normalized_series_description = series_description.strip().lower()
    with open(exam_card_path, 'r') as file:
        lines = file.readlines()
        for i, line in enumerate(lines):
            normalized_line = line.strip().lower()
            if normalized_series_description in normalized_line and "protocol name:" in normalized_line:
                capture = True
                matched_protocol.append(line)
                continue
            if capture:
                if "protocol name:" in normalized_line and i != 0:
                    break
                matched_protocol.append(line)
    if not matched_protocol:
        print(f"No match found for series: {series_description}")
    return "".join(matched_protocol) if matched_protocol else None


def determine_phase_encoding_direction(dicom_path, scanner_type="SIEMENS", exam_card_path=None):
    """Determine BIDS PhaseEncodingDirection from DICOM or Exam Card, supporting SIEMENS and PHILIPS."""
    rowcol_to_niftidim = {'COL': 'j', 'ROW': 'i'}

    # Read DICOM
    ds = pydicom.dcmread(dicom_path)
    series_description = ds.get("SeriesDescription", "Unknown").strip()

    if exam_card_path:
        protocol_details = match_protocol_in_exam_card(series_description, exam_card_path)
        if protocol_details:
            prep_dir = None
            fat_shift_dir = None
            for line in protocol_details.splitlines():
                if "EX_STACKS_0__prep_dir" in line:
                    prep_dir = line.split(":")[-1].strip().upper()
                if "EX_STACKS_0__fat_shift_dir" in line:
                    fat_shift_dir = line.split(":")[-1].strip().lower()

            if fat_shift_dir == "a":
                return "j-"
            elif fat_shift_dir == "p":
                return "j"
            if prep_dir == "AP":
                return "j-"
            elif prep_dir == "PA":
                return "j"
            elif prep_dir == "LR":
                return "i-"
            elif prep_dir == "RL":
                return "i"

    inplane_pe_dir = ds.get((0x0018, 0x1312), None)
    if inplane_pe_dir is None:
        raise ValueError(f"InPlanePhaseEncodingDirection not found in DICOM for SeriesDescription: '{series_description}'")

    inplane_pe_dir = inplane_pe_dir.value
    return f"{rowcol_to_niftidim[inplane_pe_dir]}"


def update_json_with_dicom_info(dicom_path, json_path, output_path, calculate_total_readout=False, scanner_type="SIEMENS", exam_card_path=None, compute_slice_timing=False):
    ds = pydicom.dcmread(dicom_path)

    phase_encoding_steps = int(ds.get("PhaseEncodingSteps", 95))
    effective_echo_spacing = float(ds.get("EffectiveEchoSpacing", 0.000593))
    tr = int(ds.get("RepetitionTime", 1500))
    num_slices = int(ds.get("NumberOfSlices", 54))
    mb_factor = int(ds.get("MultiBandFactor", 3))

    bids_phase_encoding_direction = determine_phase_encoding_direction(dicom_path, scanner_type, exam_card_path)

    slice_timing = None
    if compute_slice_timing:
        sets_per_tr = num_slices // mb_factor
        slice_order = [
            [0, 18, 36], [4, 22, 40], [8, 26, 44], [12, 30, 48], [16, 34, 52],
            [1, 19, 37], [5, 23, 41], [9, 27, 45], [13, 31, 49], [17, 35, 53],
            [2, 20, 38], [6, 24, 42], [10, 28, 46], [14, 32, 50], [3, 21, 39],
            [7, 25, 43], [11, 29, 47], [15, 33, 51]
        ]
        slice_timing = calculate_slice_timing(tr, num_slices, mb_factor, slice_order, sets_per_tr)

    if exam_card_path:
        protocol_details = match_protocol_in_exam_card(ds.get("SeriesDescription", "Unknown"), exam_card_path)
        if protocol_details:
            total_readout_time = calculate_total_readout_time_from_exam_card(protocol_details)
        else:
            total_readout_time = calculate_total_readout_time(phase_encoding_steps, effective_echo_spacing)
    elif calculate_total_readout:
        total_readout_time = calculate_total_readout_time(phase_encoding_steps, effective_echo_spacing)
    else:
        total_readout_time = float(ds.get("EstimatedTotalReadoutTime", 0.055742))

    with open(json_path, 'r') as f:
        json_data = json.load(f)

    if slice_timing:
        json_data["SliceTiming"] = slice_timing
    json_data["TotalReadoutTime"] = total_readout_time
    json_data["EffectiveEchoSpacing"] = effective_echo_spacing
    json_data["PhaseEncodingDirection"] = bids_phase_encoding_direction

    with open(output_path, 'w') as f:
        json.dump(json_data, f, indent=4)

    print(f"Updated JSON saved to {output_path}")


def print_help():
    print("""
Usage: python script_name.py <dicom_file> <json_file> <output_file> <exam_card_file> [--compute-slice-timing]

Options:
  --compute-slice-timing   Enable Slice Timing calculation.
    """)


if __name__ == '__main__':
    if len(sys.argv) < 5:
        print_help()
        sys.exit(1)

    dicom_file = sys.argv[1]
    json_file = sys.argv[2]
    output_file = sys.argv[3]
    exam_card_file = sys.argv[4]

    compute_slice_timing = "--compute-slice-timing" in sys.argv
    update_json_with_dicom_info(dicom_file, json_file, output_file, calculate_total_readout=False,
                                scanner_type="PHILIPS", exam_card_path=exam_card_file, compute_slice_timing=compute_slice_timing)
