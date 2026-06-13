"""
JPG to DICOM Converter.
Converts a JPG/PNG image into a valid DICOM (.dcm) file with proper
medical metadata headers using pydicom.
"""

import os
import sys
import uuid
import numpy as np
from datetime import datetime
from PIL import Image

import pydicom
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid
from pydicom.sequence import Sequence


def jpg_to_dicom(
    jpg_path: str,
    output_path: str = None,
    patient_name: str = "HealthAI Patient",
    patient_id: str = "PAT-001",
    modality: str = "DX",
    body_part: str = "CHEST",
    study_description: str = "Chest X-Ray PA View",
    institution: str = "HealthAI Hospital",
    referring_physician: str = "Dr. Anika Verma",
) -> str:
    """
    Convert a JPG/PNG image to a DICOM file with proper medical metadata.

    Args:
        jpg_path: Path to the source JPG/PNG image
        output_path: Path for the output .dcm file (auto-generated if None)
        patient_name: Patient name for DICOM header
        patient_id: Patient ID for DICOM header
        modality: Imaging modality (DX=Digital X-Ray, CR=Computed Radiography, etc.)
        body_part: Body part examined
        study_description: Description of the study
        institution: Institution name
        referring_physician: Referring physician name

    Returns:
        Path to the generated DICOM file
    """
    if not os.path.exists(jpg_path):
        raise FileNotFoundError(f"Image not found: {jpg_path}")

    # Load the image
    img = Image.open(jpg_path)

    # Convert to grayscale if RGB (medical images are typically grayscale)
    if img.mode == "RGB" or img.mode == "RGBA":
        img = img.convert("L")

    # Get pixel data as numpy array
    pixel_array = np.array(img)

    # Generate output path if not provided
    if output_path is None:
        base = os.path.splitext(os.path.basename(jpg_path))[0]
        output_dir = os.path.dirname(jpg_path)
        output_path = os.path.join(output_dir, f"{base}.dcm")

    # Create the DICOM file meta info
    file_meta = pydicom.dataset.FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.1.1"  # Digital X-Ray
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.ImplementationClassUID = generate_uid()
    file_meta.ImplementationVersionName = "HealthAI_v1"

    # Create the dataset
    ds = FileDataset(output_path, {}, file_meta=file_meta, preamble=b"\x00" * 128)

    # ── Patient Module ───────────────────────────────────────
    ds.PatientName = patient_name
    ds.PatientID = patient_id
    ds.PatientBirthDate = "19810115"
    ds.PatientSex = "M"
    ds.PatientAge = "045Y"

    # ── General Study Module ─────────────────────────────────
    ds.StudyInstanceUID = generate_uid()
    ds.StudyDate = datetime.now().strftime("%Y%m%d")
    ds.StudyTime = datetime.now().strftime("%H%M%S.%f")
    ds.StudyID = f"STD-{uuid.uuid4().hex[:6].upper()}"
    ds.AccessionNumber = f"ACC-{uuid.uuid4().hex[:6].upper()}"
    ds.StudyDescription = study_description
    ds.ReferringPhysicianName = referring_physician

    # ── General Series Module ────────────────────────────────
    ds.SeriesInstanceUID = generate_uid()
    ds.SeriesNumber = 1
    ds.SeriesDescription = f"{body_part} Series 1"
    ds.Modality = modality
    ds.BodyPartExamined = body_part

    # ── General Equipment Module ─────────────────────────────
    ds.InstitutionName = institution
    ds.Manufacturer = "HealthAI Imaging"
    ds.ManufacturerModelName = "HealthAI-DX-2026"
    ds.SoftwareVersions = "1.0.0"
    ds.StationName = "HEALTHAI-WS01"

    # ── SOP Common Module ────────────────────────────────────
    ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.1.1"  # Digital X-Ray
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    ds.InstanceCreationDate = datetime.now().strftime("%Y%m%d")
    ds.InstanceCreationTime = datetime.now().strftime("%H%M%S.%f")

    # ── Image Pixel Module ───────────────────────────────────
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.Rows = pixel_array.shape[0]
    ds.Columns = pixel_array.shape[1]
    ds.BitsAllocated = 16
    ds.BitsStored = 12
    ds.HighBit = 11
    ds.PixelRepresentation = 0  # unsigned

    # Scale 8-bit to 12-bit range for medical image quality
    pixel_data_16 = pixel_array.astype(np.uint16) * 16  # 0-255 → 0-4080
    ds.PixelData = pixel_data_16.tobytes()

    # Window/Level for proper display
    ds.WindowCenter = 2040
    ds.WindowWidth = 4080
    ds.RescaleIntercept = 0
    ds.RescaleSlope = 1
    ds.RescaleType = "US"

    # ── Image Module ─────────────────────────────────────────
    ds.ImageType = ["ORIGINAL", "PRIMARY"]
    ds.ContentDate = datetime.now().strftime("%Y%m%d")
    ds.ContentTime = datetime.now().strftime("%H%M%S.%f")
    ds.InstanceNumber = 1
    ds.ImageComments = "Converted from JPG by HealthAI System"
    ds.LossyImageCompression = "01"
    ds.LossyImageCompressionMethod = "ISO_10918_1"  # JPEG

    # ── Pixel Spacing (approximate for chest X-ray) ──────────
    ds.PixelSpacing = [0.139, 0.139]  # mm per pixel
    ds.ImagerPixelSpacing = [0.139, 0.139]

    # Save DICOM file
    ds.is_little_endian = True
    ds.is_implicit_VR = False
    ds.save_as(output_path)

    return output_path


if __name__ == "__main__":
    # CLI usage: python jpg_to_dicom.py input.jpg [output.dcm]
    if len(sys.argv) < 2:
        print("Usage: python jpg_to_dicom.py <input.jpg> [output.dcm]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    result = jpg_to_dicom(input_path, output_path)
    print(f"DICOM file created: {result}")
    print(f"   File size: {os.path.getsize(result) / 1024 / 1024:.2f} MB")
