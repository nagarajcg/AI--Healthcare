"""
DICOM Preview Service.
Generates preview images from DICOM files using pixel array rendering
and window leveling for proper contrast adjustment.
"""

import os
import io
import hashlib
from datetime import datetime

# Preview cache directory
PREVIEW_CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "storage", "dicom_previews"
)
os.makedirs(PREVIEW_CACHE_DIR, exist_ok=True)


def generate_dicom_preview(dicom_path: str, window_center: float = None, window_width: float = None) -> str:
    """
    Generate a PNG preview image from a DICOM file.
    Uses window leveling for proper contrast adjustment.

    Args:
        dicom_path: Path to the .dcm file
        window_center: Window center for contrast (auto if None)
        window_width: Window width for contrast (auto if None)

    Returns:
        Path to the generated PNG preview
    """
    # Generate cache key based on file path + modification time
    file_hash = hashlib.md5(dicom_path.encode()).hexdigest()[:12]
    preview_name = f"preview_{file_hash}.png"
    preview_path = os.path.join(PREVIEW_CACHE_DIR, preview_name)

    # Return cached if exists
    if os.path.exists(preview_path):
        return preview_path

    try:
        import pydicom
        import numpy as np
        from PIL import Image

        ds = pydicom.dcmread(dicom_path, force=True)

        # Get pixel array
        pixel_array = ds.pixel_array.astype(float)

        # Apply window leveling
        if window_center is None:
            wc = getattr(ds, "WindowCenter", None)
            if wc is not None:
                window_center = float(wc[0]) if isinstance(wc, pydicom.multival.MultiValue) else float(wc)
            else:
                window_center = (pixel_array.max() + pixel_array.min()) / 2

        if window_width is None:
            ww = getattr(ds, "WindowWidth", None)
            if ww is not None:
                window_width = float(ww[0]) if isinstance(ww, pydicom.multival.MultiValue) else float(ww)
            else:
                window_width = pixel_array.max() - pixel_array.min()
                if window_width == 0:
                    window_width = 1

        # Apply window level transform
        lower = window_center - window_width / 2
        upper = window_center + window_width / 2
        pixel_array = np.clip(pixel_array, lower, upper)
        pixel_array = ((pixel_array - lower) / (upper - lower) * 255).astype(np.uint8)

        # Handle photometric interpretation
        if getattr(ds, "PhotometricInterpretation", "") == "MONOCHROME1":
            pixel_array = 255 - pixel_array

        # Create and save image
        if len(pixel_array.shape) == 2:
            img = Image.fromarray(pixel_array, mode="L")
        else:
            img = Image.fromarray(pixel_array)

        # Resize if too large (max 1024px)
        max_dim = max(img.size)
        if max_dim > 1024:
            scale = 1024 / max_dim
            new_size = (int(img.size[0] * scale), int(img.size[1] * scale))
            img = img.resize(new_size, Image.LANCZOS)

        img.save(preview_path, "PNG", optimize=True)
        return preview_path

    except ImportError:
        # Missing dependencies — generate placeholder
        return _generate_placeholder_preview(preview_path, dicom_path)
    except Exception as e:
        # DICOM has no pixel data or other error
        return _generate_placeholder_preview(preview_path, dicom_path, error=str(e))


def _generate_placeholder_preview(preview_path: str, dicom_path: str, error: str = None) -> str:
    """Generate a dark placeholder preview image with DICOM info text."""
    try:
        from PIL import Image, ImageDraw, ImageFont

        img = Image.new("RGB", (512, 512), (15, 20, 35))
        draw = ImageDraw.Draw(img)

        # Draw grid lines for medical feel
        for i in range(0, 512, 32):
            draw.line([(i, 0), (i, 512)], fill=(25, 35, 55), width=1)
            draw.line([(0, i), (512, i)], fill=(25, 35, 55), width=1)

        # Draw crosshairs
        draw.line([(256, 0), (256, 512)], fill=(40, 60, 90), width=1)
        draw.line([(0, 256), (512, 256)], fill=(40, 60, 90), width=1)

        # Text
        try:
            font = ImageFont.truetype("arial.ttf", 18)
            font_small = ImageFont.truetype("arial.ttf", 13)
        except (IOError, OSError):
            font = ImageFont.load_default()
            font_small = font

        filename = os.path.basename(dicom_path)
        draw.text((256, 200), "DICOM PREVIEW", fill=(59, 130, 246), anchor="mm", font=font)
        draw.text((256, 240), filename, fill=(148, 163, 184), anchor="mm", font=font_small)
        draw.text((256, 280), "Medical Imaging Data", fill=(100, 116, 139), anchor="mm", font=font_small)

        if error:
            draw.text((256, 320), f"Note: {error[:50]}", fill=(245, 158, 11), anchor="mm", font=font_small)

        # Corner markers
        marker_color = (59, 130, 246)
        for x, y in [(20, 20), (492, 20), (20, 492), (492, 492)]:
            draw.rectangle([x - 4, y - 4, x + 4, y + 4], outline=marker_color, width=1)

        img.save(preview_path, "PNG")
        return preview_path

    except ImportError:
        # Even PIL not available — return empty path
        return ""
