import os
import shutil
import tempfile
import subprocess
import argparse
from update_json_sidecar import update_json_with_dicom_info

def convert_dicom_to_nifti(dicom_file, nifti_dir, tmp_dir=None):
    """
    Converts DICOM to NIfTI format using dcm2niix and stores results in nifti_dir.

    Parameters:
        dicom_file (str): Path to the DICOM file or directory.
        nifti_dir (str): Output directory for the NIfTI and JSON files.
        tmp_dir (str): Optional. Directory for temporary storage. If not provided, uses a system temporary directory.

    Returns:
        Tuple[str, str]: Paths to the generated NIfTI and JSON files.
    """
    # Ensure the output directory exists
    os.makedirs(nifti_dir, exist_ok=True)

    # Manage temporary directory
    if tmp_dir is None:
        tmp_dir = tempfile.mkdtemp()
        cleanup_tmp = True
    else:
        tmp_dir = os.path.abspath(tmp_dir)
        os.makedirs(tmp_dir, exist_ok=True)
        cleanup_tmp = False

    try:
        # Copy DICOM file(s) to temporary directory
        dicom_basename = os.path.basename(dicom_file)
        tmp_dicom_path = os.path.join(tmp_dir, dicom_basename)
        if os.path.isdir(dicom_file):
            shutil.copytree(dicom_file, tmp_dicom_path)
        else:
            shutil.copy(dicom_file, tmp_dicom_path)

        # Run dcm2niix
        subprocess.run(
            ["dcm2niix", "-o", nifti_dir, "-z", "n", "-v", "y", "-f", "%p", tmp_dicom_path],
            check=True
        )

        # Identify generated NIfTI and JSON files
        nifti_files = [f for f in os.listdir(nifti_dir) if f.endswith(".nii")]
        json_files = [f for f in os.listdir(nifti_dir) if f.endswith(".json")]

        if not nifti_files or not json_files:
            raise FileNotFoundError("NIfTI or JSON files were not generated in the output directory.")

        nifti_file = os.path.join(nifti_dir, nifti_files[0])
        json_file = os.path.join(nifti_dir, json_files[0])

        return nifti_file, json_file

    finally:
        # Clean up temporary directory if created by this function
        if cleanup_tmp:
            shutil.rmtree(tmp_dir)

def main():
    parser = argparse.ArgumentParser(description="Convert DICOM to NIfTI and update JSON sidecar.")
    parser.add_argument("dicom_file", help="Path to the DICOM file or directory.")
    parser.add_argument("nifti_dir", help="Output directory for the NIfTI and JSON files.")
    parser.add_argument("--exam-card", help="Path to the exam card file.", default=None)
    parser.add_argument("--compute-slice-timing", help="Enable Slice Timing calculation.", action="store_true")
    parser.add_argument("--compute-total-readout", help="Enable Total Readout Time calculation.", action="store_true")
    parser.add_argument("--slice-order", help="Custom slice order as a list of lists.", default=None)
    parser.add_argument("--tmp-dir", help="Optional temporary directory for processing.", default=None)
    parser.add_argument("--scanner-type", help="Scanner type (default: 'SIEMENS').", default="SIEMENS")
    args = parser.parse_args()

    try:
        # Step 1: Convert DICOM to NIfTI
        nifti_file, json_file = convert_dicom_to_nifti(args.dicom_file, args.nifti_dir, tmp_dir=args.tmp_dir)

        # Step 2: Update JSON sidecar
        update_json_with_dicom_info(
            dicom_path=args.dicom_file,
            json_path=json_file,
            output_path=json_file,
            exam_card_path=args.exam_card,
            compute_slice_timing=args.compute_slice_timing,
            user_slice_order=args.slice_order,
            scanner_type=args.scanner_type,
            calculate_total_readout=args.compute_total_readout
        )

    except Exception as e:
        print(f"Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()
