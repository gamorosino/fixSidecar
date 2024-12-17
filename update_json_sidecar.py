import pydicom
import json
import numpy as np
import sys
import ast
import re

def calculate_slice_timing(tr, num_slices, mb_factor, slice_order, sets_per_tr):
    """Calculate slice timing based on acquisition parameters."""
    set_interval = (tr / 1000) / sets_per_tr  # Convert TR from ms to seconds
    slice_timing = np.zeros(num_slices)
    
    for i, slice_group in enumerate(slice_order):
        for slice_index in slice_group:
            slice_timing[slice_index] = i * set_interval
    return slice_timing.tolist()


def calculate_correct_slice_order(num_slices, mb_factor):
    """Calculate slice acquisition order based on number of slices and MB factor."""
    if mb_factor <= 0:
        raise ValueError("MultiBand Factor (MB Factor) must be greater than zero.")

    slice_order = []
    step_size = 4  # Increment between groups
    start_offsets = [0, 1, 2, 3]  # Starting offsets for each slice set
    # Loop to create the interleaved groups
    off=int(num_slices/mb_factor)
    k=0
    steps = 0
    a_i=0
    flag_on=0
    cont=0
    slices = list(range(0,num_slices,mb_factor))
    for stp in slices:
        group = []
        cont = cont + 1
        if stp == 0:
            step_size=0
            a_i=0
        else:
            step_size=4
        if flag_on == 0:
            if  a_i + step_size + off + off >= num_slices:
                flag_on = 1
                k = k + 1 
                cont = 0
                a_i=0 + k 
                step_size=0
                #a_i = a_i +  step_size
        else:
            if a_i +  step_size+2*off >= num_slices:
                flag_on = 1
                k = k + 1 
                cont = 0
                a_i=0 + k 
                step_size=0
                #a_i = a_i +  step_size
        a_i = a_i +  step_size
        b_i = a_i + off
        c_i = b_i + off

        group=[a_i,b_i,c_i]
        slice_order.append(group)

    return slice_order



def parse_tr_from_exam_card(protocol_details):
    """Extract TR (Repetition Time) from the protocol details, handling various formats."""
    tr = None
    for line in protocol_details.splitlines():
        if "Act. TR/TE (ms)" in line: #or "TR  :" in line:
            match = re.search(r"(\d+)\s*(?:/\s*\d+)?", line)
            if match:
                tr = int(match.group(1))
    return tr


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


def extract_parameters_from_exam_card(protocol_details):
    """Extract parameters from the protocol details in the exam card."""
    tr = parse_tr_from_exam_card(protocol_details)
    num_slices = None
    mb_factor = None

    for line in protocol_details.splitlines():
        if "EX_STACKS_0__slices" in line:
            num_slices = int(line.split(":")[-1].strip())
        elif "MB Factor" in line:
            mb_factor = int(line.split(":")[-1].strip())

    return tr, num_slices, mb_factor


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


def update_json_with_dicom_info(dicom_path, json_path, output_path, calculate_total_readout=False, scanner_type="SIEMENS", exam_card_path=None, compute_slice_timing=False, user_slice_order=None):
    # Read the DICOM file
    ds = pydicom.dcmread(dicom_path)
    with open(json_path, 'r') as f:
        json_data = json.load(f)    
    phase_encoding_steps = int(json_data.get("PhaseEncodingSteps", 95))
    effective_echo_spacing = float(json_data.get("EffectiveEchoSpacing", 0.000593))
    tr = float(json_data.get("RepetitionTime", 0))*1000
    num_slices = int(json_data.get("NumberOfSlices", 0))
    mb_factor = int(json_data.get("MultiBandFactor", 0))

    # If parameters are missing, fallback to DICOM
    if not tr or not num_slices or not mb_factor:
        ds = pydicom.dcmread(dicom_path)
        phase_encoding_steps = int(getattr(ds, "PhaseEncodingSteps", phase_encoding_steps))
        effective_echo_spacing = float(getattr(ds, "EffectiveEchoSpacing", effective_echo_spacing))
        tr = int(getattr(ds, "RepetitionTime", tr))
        num_slices = int(getattr(ds, "NumberOfSlices", num_slices))
        mb_factor = int(getattr(ds, "MultiBandFactor", mb_factor))

    # Fallback to exam card if parameters are missing
    if not tr or not num_slices or not mb_factor:
        if exam_card_path:
            protocol_details = match_protocol_in_exam_card(ds.get("SeriesDescription", "Unknown"), exam_card_path)
            if protocol_details:
                tr_card, slices_card, mb_card = extract_parameters_from_exam_card(protocol_details)
                tr = tr_card if not tr else tr
                num_slices = slices_card if not num_slices else num_slices
                mb_factor = mb_card if not mb_factor else mb_factor

    # Default values if parameters are still missing
    if not tr:
        tr = 2000
    if not num_slices:
        num_slices = 64
    if not mb_factor:
        mb_factor = 1


    print("tr: ",tr)
    print("num_slices: ",num_slices)
    print("mb_factor: ",mb_factor)



    # Calculate Slice Timing
    slice_timing = None
    if compute_slice_timing:
        # Slice order
        if user_slice_order:
            slice_order = ast.literal_eval(user_slice_order)  # Convert string to list
            print(f"Using user-provided slice order: {slice_order}")
        else:
            slice_order = calculate_correct_slice_order(num_slices, mb_factor)
        print(f"Calculated slice order: {slice_order}")
        sets_per_tr = num_slices // mb_factor
        print("sets_per_tr: ",sets_per_tr)
        slice_timing = calculate_slice_timing(tr, num_slices, mb_factor, slice_order, sets_per_tr)

    # Determine Phase Encoding Direction
    bids_phase_encoding_direction = determine_phase_encoding_direction(dicom_path, scanner_type, exam_card_path)

    # Calculate Total Readout Time
    if exam_card_path:
        protocol_details = match_protocol_in_exam_card(ds.get("SeriesDescription", "Unknown"), exam_card_path)
    
    if calculate_total_readout:
        if protocol_details:
                total_readout_time = calculate_total_readout_time_from_exam_card(protocol_details)
        else:
                total_readout_time = calculate_total_readout_time(phase_encoding_steps, effective_echo_spacing)
    else:
        total_readout_time = float(json_data.get("EstimatedTotalReadoutTime", None))
        if total_readout_time is None:
            total_readout_time = float(ds.get("EstimatedTotalReadoutTime", None))
        total_readout_time = total_readout_time  #convert in seconds

    # Update JSON
    with open(json_path, 'r') as f:
        json_data = json.load(f)

    if slice_timing:
        json_data["SliceTiming"] = slice_timing
    json_data["TotalReadoutTime"] = total_readout_time
    json_data["EffectiveEchoSpacing"] = effective_echo_spacing
    json_data["PhaseEncodingDirection"] = bids_phase_encoding_direction

    print("Slice Timing: ",slice_timing)
    print("Total Readout Time: ",total_readout_time)
    print("Effective echo spacing: ",effective_echo_spacing)
    print("Phase Encoding Direction: ",bids_phase_encoding_direction)


    with open(output_path, 'w') as f:
        json.dump(json_data, f, indent=4)

    print(f"Updated JSON saved to {output_path}")


def print_help():
    print("""
Usage: python script_name.py <dicom_file> <json_file> <output_file> <exam_card_file> [--compute-slice-timing] [--slice-order <slice_order>]

Options:
  --compute-slice-timing   Enable Slice Timing calculation.
  --slice-order            Provide a custom slice order as a string representation of a list of lists.
                           Example: "[[0, 4, 8], [1, 5, 9], [2, 6, 10]]"
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
    slice_order_arg = None
    if "--slice-order" in sys.argv:
        try:
            slice_order_arg = sys.argv[sys.argv.index("--slice-order") + 1]
        except IndexError:
            print("Error: --slice-order requires a slice order as its argument.")
            sys.exit(1)

    update_json_with_dicom_info(
        dicom_file,
        json_file,
        output_file,
        calculate_total_readout=False,
        scanner_type="PHILIPS",
        exam_card_path=exam_card_file,
        compute_slice_timing=compute_slice_timing,
        user_slice_order=slice_order_arg,
    )
