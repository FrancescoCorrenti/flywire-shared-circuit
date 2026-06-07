"""Converte un PNG in PDF. Uso: python png_to_pdf.py input.png output.pdf"""
import sys
from PIL import Image

img = Image.open(sys.argv[1])
img.save(sys.argv[2], "PDF", resolution=300)
print(f"Saved {sys.argv[2]}")
