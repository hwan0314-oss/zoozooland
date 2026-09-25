import io

from PIL import Image, ImageDraw

import image_prep


def _size_of(jpeg_bytes: bytes) -> tuple[int, int]:
    with Image.open(io.BytesIO(jpeg_bytes)) as img:
        return img.size


def test_exact_vertical_image_is_unchanged(tmp_path):
    path = tmp_path / "vertical.png"
    Image.new("RGB", (1080, 1920), "white").save(path)

    assert _size_of(image_prep.crop_to_vertical(str(path))) == (1080, 1920)


def test_wide_image_is_cropped_to_vertical(tmp_path):
    path = tmp_path / "wide.jpg"
    Image.new("RGB", (1600, 900), "white").save(path)

    assert _size_of(image_prep.crop_to_vertical(str(path))) == (506, 900)


def test_tall_image_is_cropped_to_vertical(tmp_path):
    path = tmp_path / "tall.jpg"
    Image.new("RGB", (900, 2000), "white").save(path)

    assert _size_of(image_prep.crop_to_vertical(str(path))) == (900, 1600)


def test_crop_keeps_the_center(tmp_path):
    path = tmp_path / "wide.png"
    img = Image.new("RGB", (1600, 900), "black")
    ImageDraw.Draw(img).rectangle((547, 0, 1052, 899), fill="white")
    img.save(path)

    with Image.open(io.BytesIO(image_prep.crop_to_vertical(str(path)))) as cropped:
        assert cropped.getpixel((5, 450)) > (240, 240, 240)
        assert cropped.getpixel((500, 450)) > (240, 240, 240)


def test_exif_rotation_is_applied_before_crop(tmp_path):
    path = tmp_path / "rotated.jpg"
    exif = Image.Exif()
    exif[0x0112] = 6  # 90도 회전해서 보여줘야 하는 폰 사진 (저장은 1600x900, 표시는 900x1600)
    Image.new("RGB", (1600, 900), "white").save(path, exif=exif)

    assert _size_of(image_prep.crop_to_vertical(str(path))) == (900, 1600)


def test_output_is_jpeg(tmp_path):
    path = tmp_path / "input.png"
    Image.new("RGBA", (1080, 1920), (255, 255, 255, 255)).save(path)

    with Image.open(io.BytesIO(image_prep.crop_to_vertical(str(path)))) as img:
        assert img.format == "JPEG"
