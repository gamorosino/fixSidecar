#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 21 17:05:44 2024

#########################################################################################################################
#########################################################################################################################
################### Author:          Gabriele Amorosino                                               ###################
################### Contact:         gabriele.amorosino@utexas.edu                                    ###################
#########################################################################################################################
#########################################################################################################################
"""


import pydicom
import json
import numpy as np
import sys
import ast
import re

def calculate_slice_timing(tr, num_slices, mb_factor, slice_order, sets_per_tr):
    """Calculate slice timing based on acquisition parameters."""
    set_interval = tr / sets_per_tr  # Convert TR from ms to seconds
    slice_timing = np.zeros(num_slices)
    
    for i, slice_group in enumerate(slice_order):
        for slice_index in slice_group:
            slice_timing[slice_index] = i * set_interval
    return slice_timing.tolist()


def calculate_correct_slice_order(num_slices, mb_factor,step_size = 4 ):
    """Calculate slice acquisition order based on number of slices and MB factor."""
    if mb_factor <= 0:
        raise ValueError("MultiBand Factor (MB Factor) must be greater than zero.")

    slice_order = []
     # Increment between groups
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


def calculate_total_readout_time_from_philips(dicom_data, json_data):
    """Calculate Total Readout Time using Chris Rorden's Philips formula."""
    water_fat_shift = json_data.get("WaterFatShift", None) or dicom_data.get((2001, 1022), None)
    imaging_frequency = json_data.get("ImagingFrequency", None) or dicom_data.get((0x0018, 0x0084), None)
    epi_factor = json_data.get("EchoTrainLength", None) or dicom_data.get((2001, 1013), None)
    recon_matrix_pe = json_data.get("ReconMatrixPE", None)

    if not all([water_fat_shift, imaging_frequency, epi_factor, recon_matrix_pe]):
        print("Insufficient data to calculate Total Readout Time using Philips formula.")
        return None, None

    try:
        effective_echo_spacing = water_fat_shift / (imaging_frequency * (epi_factor + 1) * 3.4)
        total_readout_time = effective_echo_spacing * (recon_matrix_pe - 1)
        return effective_echo_spacing, total_readout_time
    except Exception as e:
        print(f"Error calculating Philips Total Readout Time: {e}")
        return None, None

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

    # Effective Echo Spacing in seconds
    effective_echo_spacing = 1 / bandwidth  # Bandwidth is in Hz (cycles per second)
    # Calculate Total Readout Time
    total_readout_time = (epi_factor - 1) * effective_echo_spacing
    total_readout_time = round(total_readout_time, 6)  # Optional: rounding for better precision
    return effective_echo_spacing, total_readout_time



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


def determine_phase_encoding_direction(dicom_path, scanner_type="SIEMENS", exam_card_path=None, flip_phase=False):
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
                    fat_shift_dir = line.split(":")[-1].strip().upper()

            if fat_shift_dir == "A":
                pe_dir = "j"
            elif fat_shift_dir == "P":
                pe_dir = "j-"
            elif prep_dir == "AP":
                pe_dir = "j-"
            elif prep_dir == "PA":
                pe_dir = "j"
            elif prep_dir == "LR":
                pe_dir = "i-"
            elif prep_dir == "RL":
                pe_dir = "i"
            else:
                pe_dir = None

            if pe_dir:
                if flip_phase:
                    pe_dir = pe_dir[:-1] if pe_dir.endswith("-") else pe_dir + "-"

                return pe_dir

    inplane_pe_dir = ds.get((0x0018, 0x1312), None)
    if inplane_pe_dir is None:
        raise ValueError(f"InPlanePhaseEncodingDirection not found in DICOM for SeriesDescription: '{series_description}'")

    inplane_pe_dir = rowcol_to_niftidim[inplane_pe_dir.value]
    if flip_phase:
        inplane_pe_dir = inplane_pe_dir + "-" if "-" not in inplane_pe_dir else inplane_pe_dir[:-1]

    return inplane_pe_dir


def update_json_with_dicom_info(dicom_path, json_path, output_path, calculate_total_readout=False, scanner_type="SIEMENS", exam_card_path=None, compute_slice_timing=False, user_slice_order=None, flip_phase=False):
    # Read the DICOM file
    ds = pydicom.dcmread(dicom_path)
    with open(json_path, 'r') as f:
        json_data = json.load(f)    
    phase_encoding_steps = int(json_data.get("PhaseEncodingSteps", None))
    effective_echo_spacing = float(json_data.get("EstimatedEffectiveEchoSpacing", None))
    tr = float(json_data.get("RepetitionTime", None))
    if tr: tr=tr
    num_slices = json_data.get("NumberOfSlices", None)
    if num_slices: num_slices=int(num_slices)
    mb_factor = json_data.get("MultiBandFactor", None)
    if mb_factor: mb_factor=int(mb_factor)
    series_description = ds.get("SeriesDescription", "Unknown").strip()

    print('Read information from provided json file...')
    print("tr: ",tr)
    print("num_slices: ",num_slices)
    print("mb_factor: ",mb_factor)
    print("effective_echo_spacing: ",effective_echo_spacing)
    print("phase_encoding_steps: ",phase_encoding_steps)


    # If parameters are missing, fallback to DICOM
    if not tr or not num_slices or not mb_factor or not effective_echo_spacing or not phase_encoding_steps:
        ds = pydicom.dcmread(dicom_path)

    if not tr :
        tr = int(getattr(ds, "RepetitionTime", tr))
    
    if not num_slices :
        num_slices = getattr(ds, "NumberOfSlices", num_slices)
        if num_slices: num_slices=int(num_slices)
    
    if not mb_factor :
        mb_factor = getattr(ds, "MultiBandFactor", mb_factor)
        if mb_factor: mb_factor=int(mb_factor)
    
    if not effective_echo_spacing :
        effective_echo_spacing = getattr(ds, "EffectiveEchoSpacing", effective_echo_spacing)
        if effective_echo_spacing: effective_echo_spacing=float(effective_echo_spacing)
    if not phase_encoding_steps:
        
        phase_encoding_steps = getattr(ds, "PhaseEncodingSteps", phase_encoding_steps)
        if phase_encoding_steps: phase_encoding_steps=int(phase_encoding_steps)

    print('Read information from dicom file...')
    print("tr: ",tr)
    print("num_slices: ",num_slices)
    print("mb_factor: ",mb_factor)
    print("effective_echo_spacing: ",effective_echo_spacing)
    print("phase_encoding_steps: ",phase_encoding_steps)


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
        raise ValueError(f"Repetition Time not found SeriesDescription: '{series_description}'")

    if not num_slices:
        raise ValueError(f"Number of Slices not found SeriesDescription: '{series_description}'")


    if not mb_factor:
        mb_factor = 1

    print('Read information from exam card file...')
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
    bids_phase_encoding_direction = determine_phase_encoding_direction(dicom_path, scanner_type, exam_card_path, flip_phase=flip_phase)

    # Calculate Total Readout Time

    if calculate_total_readout:

        if exam_card_path:
            protocol_details = match_protocol_in_exam_card(ds.get("SeriesDescription", "Unknown"), exam_card_path)

        # Calculate Total Readout Time
        effective_echo_spacing_philips, total_readout_time_philips = calculate_total_readout_time_from_philips(ds, json_data)

        print("Calculate Total Readout Time")
        if protocol_details:
            effective_echo_spacing_exame, total_readout_time = calculate_total_readout_time_from_exam_card(protocol_details)
        
            if effective_echo_spacing == 0 :
                
                print("Effective echo spacing is missing from the provided JSON file. The value will be estimated based on the exam card settings.")
                effective_echo_spacing=effective_echo_spacing_exame
        
        elif total_readout_time_philips is not None:
            total_readout_time = total_readout_time_philips
            if effective_echo_spacing == 0 :
                
                print("Effective echo spacing is missing from the provided JSON file. The value will be estimated based on the dicom header info.")
                effective_echo_spacing=effective_echo_spacing_philips
        else:
            if effective_echo_spacing is not None:
                total_readout_time = calculate_total_readout_time(phase_encoding_steps, effective_echo_spacing)
            else:
                ValueError("Effective echo spacing is missing from the provided JSON file.")
    else:
        total_readout_time = float(json_data.get("EstimatedTotalReadoutTime", None))
        print('Set Total Readout Time as EstimatedTotalReadoutTime field of json file')
        if total_readout_time is None:
            total_readout_time = float(ds.get("EstimatedTotalReadoutTime", None))
        if total_readout_time is None:
            ValueError('EstimatedTotalReadoutTime missed from json file...')
    if total_readout_time and total_readout_time > 1:  # Convert from ms to seconds if necessary
            total_readout_time /= 100


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
    if len(sys.argv) < 4:
        print_help()
        sys.exit(1)

    dicom_file = sys.argv[1]
    json_file = sys.argv[2]
    output_file = sys.argv[3]
    exam_card_file = sys.argv[4] if len(sys.argv) > 4 else None

    compute_slice_timing = "--compute-slice-timing" in sys.argv
    slice_order_arg = None
    if "--slice-order" in sys.argv:
        try:
            slice_order_arg = sys.argv[sys.argv.index("--slice-order") + 1]
        except IndexError:
            print("Error: --slice-order requires a slice order as its argument.")
            sys.exit(1)
    flip_phase = "--flip-phase" in sys.argv
    update_json_with_dicom_info(
        dicom_file,
        json_file,
        output_file,
        calculate_total_readout=False,
        scanner_type="PHILIPS",
        exam_card_path=exam_card_file,
        compute_slice_timing=compute_slice_timing,
        user_slice_order=slice_order_arg,
        flip_phase=flip_phase
    )
