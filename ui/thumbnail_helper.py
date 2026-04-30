"""
thumbnail_helper.py
Called automatically by app.py to save small preview images
for the before/after capture cards in the dashboard.
Not needed to run separately.
"""
import cv2
import os

def save_thumb(src_path, dest_path, width=200, height=70):
    """Resize a capture to thumbnail size for the UI cards."""
    img = cv2.imread(src_path)
    if img is None:
        return False
    thumb = cv2.resize(img, (width, height))
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    cv2.imwrite(dest_path, thumb)
    return True
