import os
from io import BytesIO
from PIL import Image


class LocalStorage:
    def __init__(self):
        self.base_path = "static/avatars"
        self.base_url = "auth/avatars"
        self.allowed_formats = {"png", "jpg", "jpeg", "webp"}
        self.max_size = 5 * 1024 * 1024

        os.makedirs(self.base_path, exist_ok=True)

    def _crop_center_square(self, image: Image.Image) -> Image.Image:
        width, height = image.size
        min_side = min(width, height)

        left = (width - min_side) / 2
        top = (height - min_side) / 2
        right = (width + min_side) / 2
        bottom = (height + min_side) / 2

        return image.crop((left, top, right, bottom))

    async def upload_avatar(self, file, user_id: str) -> str:
        content = await file.read()

        if len(content) > self.max_size:
            raise ValueError("File too large")

        try:
            image = Image.open(BytesIO(content))
        except Exception:
            raise ValueError("Invalid image")

        ext = (image.format or "").lower()
        if ext not in self.allowed_formats:
            raise ValueError("Unsupported format")

        image = image.convert("RGB")
        image = self._crop_center_square(image)
        image = image.resize((512, 512))

        filename = f"{user_id}.webp"
        path = os.path.join(self.base_path, filename)

        image.save(path, "WEBP", quality=80, optimize=True)

        return f"{self.base_url}/{filename}"