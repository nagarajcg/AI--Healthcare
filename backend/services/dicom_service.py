"""
DICOM Metadata Extraction Service.
Uses pydicom to parse .dcm files and extract clinical metadata.
"""

import os
from datetime import datetime


def extract_dicom_metadata(file_path: str) -> dict:
    """
    Extract metadata from a DICOM file.
    Returns a dict with patient info, study info, and image dimensions.
    Falls back to simulated metadata if pydicom is not available.
    """
    try:
        import pydicom
        ds = pydicom.dcmread(file_path, force=True)

        # Extract core fields safely
        def _get(attr, default="Unknown"):
            val = getattr(ds, attr, None)
            if val is None:
                return default
            return str(val).strip() if str(val).strip() else default

        # Image dimensions
        rows = int(getattr(ds, "Rows", 0))
        cols = int(getattr(ds, "Columns", 0))
        dimensions = f"{cols} x {rows}" if rows and cols else "Unknown"

        # Study date formatting
        raw_date = _get("StudyDate", "")
        study_date = raw_date
        if raw_date and raw_date != "Unknown" and len(raw_date) == 8:
            try:
                study_date = datetime.strptime(raw_date, "%Y%m%d").strftime("%Y-%m-%d")
            except ValueError:
                pass

        metadata = {
            "patient_name": _get("PatientName"),
            "patient_id": _get("PatientID"),
            "study_date": study_date,
            "modality": _get("Modality"),
            "body_part": _get("BodyPartExamined"),
            "image_dimensions": dimensions,
            "study_description": _get("StudyDescription"),
            "series_description": _get("SeriesDescription"),
            "institution": _get("InstitutionName"),
            "manufacturer": _get("Manufacturer"),
            "study_id": _get("StudyID"),
            "accession_number": _get("AccessionNumber"),
            "bits_allocated": int(getattr(ds, "BitsAllocated", 0)),
            "bits_stored": int(getattr(ds, "BitsStored", 0)),
            "photometric_interpretation": _get("PhotometricInterpretation"),
            "pixel_spacing": str(getattr(ds, "PixelSpacing", "Unknown")),
            "transfer_syntax": str(getattr(ds.file_meta, "TransferSyntaxUID", "Unknown")) if hasattr(ds, "file_meta") else "Unknown",
            "sop_class": _get("SOPClassUID"),
            "extracted_at": datetime.utcnow().isoformat() + "Z",
        }
        return metadata

    except ImportError:
        # pydicom not installed — return simulated metadata
        return _simulate_metadata(file_path)
    except Exception as e:
        # File not valid DICOM or other error — return simulated
        return _simulate_metadata(file_path, error=str(e))


def _simulate_metadata(file_path: str, error: str = None) -> dict:
    """Generate simulated metadata when pydicom is unavailable or file is not valid DICOM."""
    file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
    return {
        "patient_name": "DICOM Patient",
        "patient_id": "DCMPAT-001",
        "study_date": datetime.utcnow().strftime("%Y-%m-%d"),
        "modality": "DX",
        "body_part": "CHEST",
        "image_dimensions": "2048 x 2048",
        "study_description": "DICOM Study",
        "series_description": "Series 1",
        "institution": "HealthAI Hospital",
        "manufacturer": "Unknown",
        "study_id": "STD-001",
        "accession_number": "ACC-001",
        "bits_allocated": 16,
        "bits_stored": 12,
        "photometric_interpretation": "MONOCHROME2",
        "pixel_spacing": "0.14 x 0.14 mm",
        "transfer_syntax": "1.2.840.10008.1.2.1",
        "sop_class": "1.2.840.10008.5.1.4.1.1.1.1",
        "extracted_at": datetime.utcnow().isoformat() + "Z",
        "_simulated": True,
        "_note": "pydicom not available or file not valid DICOM" + (f" — {error}" if error else ""),
    }


def get_file_size_formatted(file_path: str) -> str:
    """Return human-readable file size."""
    if not os.path.exists(file_path):
        return "0 B"
    size = os.path.getsize(file_path)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
