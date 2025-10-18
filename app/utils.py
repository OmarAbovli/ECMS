# app/utils.py
import uuid
import os
from barcode import Code128
from barcode.writer import ImageWriter
import qrcode

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
BARCODES_DIR = os.path.join(BASE_DIR, "app", "static", "barcodes")
os.makedirs(BARCODES_DIR, exist_ok=True)

def generate_uuid():
    return str(uuid.uuid4())

def generate_code128_image(code_str, filename=None):
    """يرجع path للصورة المولدة (PNG)."""
    if filename is None:
        filename = f"{code_str}.png"
    path = os.path.join(BARCODES_DIR, filename)
    # Use ImageWriter to create PNG
    writer_options = {'write_text': False}
    Code128(code_str, writer=ImageWriter()).write(open(path, "wb"), writer_options)
    return path

def generate_qr_image(code_str, filename=None):
    if filename is None:
        filename = f"qr_{code_str}.png"
    path = os.path.join(BARCODES_DIR, filename)
    img = qrcode.make(code_str)
    img.save(path)
    return path
