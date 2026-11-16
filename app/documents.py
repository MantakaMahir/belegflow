import base64
import io
import warnings
from email import policy
from email.parser import BytesParser
from pathlib import Path
from threading import Lock

import pypdfium2 as pdfium
from PIL import Image

PDF_LOCK = Lock()  # PDFium forbids simultaneous calls, even for unrelated documents.
SUPPORTED = {".pdf", ".png", ".jpg", ".jpeg", ".txt"}


def validate_file(filename, content, limit):
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED:
        raise ValueError("Supported files: PDF, PNG, JPEG, TXT, or an EML containing these files.")
    if not content or len(content) > limit:
        raise ValueError("Document is empty or exceeds the 15 MB upload limit.")
    if suffix == ".pdf" and not content.startswith(b"%PDF-"):
        raise ValueError("The file does not contain a valid PDF header.")
    if suffix == ".png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("The file does not contain a valid PNG header.")
    if suffix in {".jpg", ".jpeg"} and not content.startswith(b"\xff\xd8\xff"):
        raise ValueError("The file does not contain a valid JPEG header.")
    if suffix == ".txt":
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("Text documents must use UTF-8 encoding.") from exc
        if "\x00" in text or len(text) > 60000:
            raise ValueError("Text must be plain UTF-8 and at most 60,000 characters.")
    return Path(filename.replace("\\", "/")).name[:180]


def attachments(filename, content, limit):
    if Path(filename).suffix.lower() != ".eml":
        return [(validate_file(filename, content, limit), content)]
    message = BytesParser(policy=policy.default).parsebytes(content)
    files = []
    for part in message.walk():
        name = part.get_filename()
        if name and Path(name).suffix.lower() in SUPPORTED:
            data = part.get_payload(decode=True)
            files.append((validate_file(name, data, limit), data))
        if len(files) > 10:
            raise ValueError("Email files may contain at most 10 supported attachments.")
    if not files:
        raise ValueError("No PDF, PNG, JPEG, or TXT attachments found in the email.")
    return files


def image_part(content):
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(io.BytesIO(content)) as image:
            if image.width * image.height > 20_000_000:
                raise ValueError("Images must not exceed 20 megapixels.")
            image.thumbnail((1800, 1800))
            buffer = io.BytesIO()
            image.convert("RGB").save(buffer, format="JPEG", quality=85)
    encoded = base64.b64encode(buffer.getvalue()).decode()
    return {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}


def read_document(path: Path, max_pages):
    """Return local text and scanned-page image parts; never silently truncate pages."""
    content = path.read_bytes()
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return content.decode("utf-8-sig"), []
    if suffix != ".pdf":
        return "", [image_part(content)]
    texts, images = [], []
    with PDF_LOCK, pdfium.PdfDocument(content) as document:
        if len(document) > max_pages:
            raise ValueError(
                f"PDFs may contain at most {max_pages} pages; split this document first."
            )
        for index in range(len(document)):
            with document[index] as page:
                with page.get_textpage() as textpage:
                    text = textpage.get_text_range().strip()
                if len(text) >= 40:
                    texts.append(f"[Page {index + 1}]\n{text}")
                else:
                    width, height = page.get_size()
                    if width <= 0 or height <= 0:
                        raise ValueError("PDF contains an invalid page size.")
                    scale = min(2, 1800 / max(width, height))
                    with page.render(scale=scale) as bitmap:
                        buffer = io.BytesIO()
                        bitmap.to_pil().save(buffer, format="PNG")
                        images.append(image_part(buffer.getvalue()))
    text = "\n\n".join(texts)
    if len(text) > 60000:
        raise ValueError("Document text exceeds 60,000 characters; split the document first.")
    return text, images
