import io

from PIL import Image, ImageOps

TARGET_RATIO = 9 / 16


def crop_to_vertical(image_path: str) -> bytes:
    """EXIF 회전을 보정한 뒤 가운데를 기준으로 9:16 세로로 잘라 JPEG 바이트로 반환.
    Kling image-to-video는 비율 파라미터가 없고 입력 이미지 비율을 그대로 따른다."""
    with Image.open(image_path) as src:
        img = ImageOps.exif_transpose(src).convert("RGB")

    width, height = img.size
    if width / height > TARGET_RATIO:
        new_width = round(height * TARGET_RATIO)
        left = (width - new_width) // 2
        img = img.crop((left, 0, left + new_width, height))
    else:
        new_height = round(width / TARGET_RATIO)
        top = (height - new_height) // 2
        img = img.crop((0, top, width, top + new_height))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()
