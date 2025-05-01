#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 21 17:05:44 2024

#########################################################################################################################
#########################################################################################################################
###################                                                                                   ###################
################### Title:               Dicom Convert and Sidecar fix                                ###################
###################                                                                                   ###################
################### Description:                                                                      ###################
################### This script facilitates the conversion of DICOM files to NIfTI format            ###################
################### and ensures the resulting JSON sidecar is compliant with BIDS (Brain Imaging    ###################
################### Data Structure) metadata standards.                                              ###################
###################                                                                                   ###################
################### Version:        0.5.0                                                             ###################
###################                                                                                   ###################
################### Requirements:   Python modules - nibabel, dipy                                   ###################
###################                 External tool - dcm2niix                                        ###################
###################                                                                                   ###################
################### Bash Version:   Tested on GNU bash, version 4.3.48                               ###################
###################                                                                                   ###################
################### Author:          Gabriele Amorosino                                             ###################
################### Contact:         gabriele.amorosino@utexas.edu                                  ###################
###################                                                                                   ###################
#########################################################################################################################
#########################################################################################################################
###################                                                                                   ###################
################### Update:  Add manual override for PhaseEncodingDirection with CLI support          ##################
###################                                                                                   ###################
#########################################################################################################################
#########################################################################################################################
"""


import os
import shutil
import tempfile
import subprocess
import argparse
from update_json_sidecar import update_json_with_dicom_info

def convert_dicom_to_nifti(dicom_file: str, output_dir: str, tmp_dir: str = None):
    """
    Converts DICOM to NIfTI format using dcm2niix and stores results in output_dir.

    Parameters:
        dicom_file (str): Path to the DICOM file or directory.
        output_dir (str): Output directory for the NIfTI and JSON files.
        tmp_dir (str): Optional. Directory for temporary storage. If not provided, uses a system temporary directory.

    Returns:
        Tuple[str, str]: Paths to the generated NIfTI and JSON files.
    """
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Manage temporary directory
    if tmp_dir is None:
        tmp_dir = tempfile.mkdtemp()
        cleanup_tmp = True
    else:
        tmp_dir = os.path.abspath(tmp_dir)
        os.makedirs(tmp_dir, exist_ok=True)
        cleanup_tmp = False

    print(f"Using temporary directory: {tmp_dir}")

    # Create a subdirectory for dcm2niix output
    temp_output_dir = os.path.join(tmp_dir, "nifti_output")
    os.makedirs(temp_output_dir, exist_ok=True)

    try:
        # Copy DICOM file(s) to temporary directory
        dicom_basename = os.path.basename(dicom_file)
        tmp_dicom_path = os.path.join(tmp_dir, dicom_basename)
        if os.path.isdir(dicom_file):
            shutil.copytree(dicom_file, tmp_dicom_path)
        else:
            shutil.copy(dicom_file, tmp_dicom_path)

        # Run dcm2niix and output to temp_output_dir
        subprocess.run(
            ["dcm2niix", "-o", temp_output_dir, "-z", "n", "-v", "y", "-f", "%p", tmp_dicom_path],
            check=True
        )

        # Identify generated NIfTI and JSON files in temp_output_dir
        nifti_files = [f for f in os.listdir(temp_output_dir) if f.endswith(".nii")]
        json_files = [f for f in os.listdir(temp_output_dir) if f.endswith(".json")]
        if not nifti_files or not json_files:
            raise FileNotFoundError("NIfTI or JSON files were not generated in the temporary directory.")

        nifti_file = os.path.join(temp_output_dir, nifti_files[0])
        json_file = os.path.join(temp_output_dir, json_files[0])
        
        # Move the files to the output directory
        final_nifti_path = os.path.join(output_dir, os.path.basename(nifti_file))
        final_json_path = os.path.join(output_dir, os.path.basename(json_file))
        shutil.move(nifti_file, final_nifti_path)
        shutil.move(json_file, final_json_path)

        print(f"NIfTI file moved to: {final_nifti_path}")
        print(f"JSON file moved to: {final_json_path}")

        return final_nifti_path, final_json_path

    finally:
        # Clean up temporary directory if created by this function
        if cleanup_tmp:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            print(f"Temporary directory {tmp_dir} cleaned up.")

def main():
    parser = argparse.ArgumentParser(description="Convert DICOM to NIfTI and update JSON sidecar.")
    parser.add_argument("dicom_file", help="Path to the DICOM file or directory.")
    parser.add_argument("output_dir", help="Output directory for the NIfTI and JSON files.")
    parser.add_argument("--exam-card", help="Path to the exam card file.", default=None)
    parser.add_argument("--compute-slice-timing", help="Enable Slice Timing calculation.", action="store_true")
    parser.add_argument("--compute-total-readout", help="Enable Total Readout Time calculation.", action="store_true")
    parser.add_argument("--slice-order", help="Custom slice order as a list of lists.", default=None)
    parser.add_argument("--tmp-dir", help="Optional temporary directory for processing.", default=None)
    parser.add_argument("--scanner-type", help="Scanner type (default: 'Philips').", default="Philips")
    parser.add_argument("--flip-phase-encoding-direction", help="Toggle the sign of the phase encoding direction.", action="store_true")
    parser.add_argument("--verbose", help="Enable verbose output.", action="store_true")
    parser.add_argument("--phase-encoding-direction", help="Manually provide the BIDS PhaseEncodingDirection (e.g., j, j-, i, i-)", default=None)
    args = parser.parse_args()

    # Step 1: Convert DICOM to NIfTI
    nifti_file, json_file = convert_dicom_to_nifti(args.dicom_file, args.output_dir, tmp_dir=args.tmp_dir)

    # Step 2: Update JSON sidecar
    update_json_with_dicom_info(
        dicom_path=args.dicom_file,
        json_path=json_file,
        output_path=json_file,
        exam_card_path=args.exam_card,
        compute_slice_timing=args.compute_slice_timing,
        user_slice_order=args.slice_order,
        scanner_type=args.scanner_type,
        calculate_total_readout=args.compute_total_readout,
        flip_phase=args.flip_phase_encoding_direction,
        verbose=args.verbose,
        user_phase_encoding_direction=args.phase_encoding_direction
    )

if __name__ == "__main__":
    main()
