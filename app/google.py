import base64
import re
from urllib.parse import quote

import google.auth
from google.auth.transport.requests import AuthorizedSession

from app.documents import SUPPORTED, attachments, validate_file
from app.exports import export_row
from app.providers import ProviderError


def session(settings, scope):
    if not settings.google_credentials_file:
        raise ValueError("Configure GOOGLE_CREDENTIALS_FILE on the backend first.")
    credentials, _ = google.auth.load_credentials_from_file(
        settings.google_credentials_file,
        scopes=[scope],
    )
    return AuthorizedSession(credentials)


def check(response):
    if not response.ok:
        raise ProviderError(
            f"Google returned HTTP {response.status_code}. Check scopes and resource permissions."
        )
    return response


def identifier(value):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", value):
        raise ValueError("Google resource ID is missing or invalid.")
    return value


def import_google(settings, engine, source, limit):
    imported = []
    if source == "drive":
        folder = identifier(settings.google_drive_folder_id)
        with session(settings, "https://www.googleapis.com/auth/drive.readonly") as client:
            files = (
                check(
                    client.get(
                        "https://www.googleapis.com/drive/v3/files",
                        params={
                            "q": f"'{folder}' in parents and trashed=false",
                            "fields": "files(id,name,size,webViewLink)",
                            "pageSize": limit,
                            "orderBy": "createdTime desc",
                        },
                        timeout=20,
                    )
                )
                .json()
                .get("files", [])
            )
            for file in files:
                from pathlib import Path

                if Path(file["name"]).suffix.lower() not in SUPPORTED:
                    continue
                if int(file.get("size", 0)) > settings.max_upload_bytes:
                    raise ValueError("A Drive document exceeds the upload limit.")
                with check(
                    client.get(
                        f"https://www.googleapis.com/drive/v3/files/{identifier(file['id'])}",
                        params={"alt": "media"},
                        stream=True,
                        timeout=30,
                    )
                ) as response:
                    data = bounded_bytes(response.iter_content(65536), settings.max_upload_bytes)
                filename = validate_file(file["name"], data, settings.max_upload_bytes)
                run, created = engine.create(
                    filename=filename,
                    content=data,
                    mode="live",
                    source="Google Drive",
                    source_url=f"https://drive.google.com/file/d/{identifier(file['id'])}/view",
                )
                imported.append({"id": run["id"], "created": created})
    else:
        with session(settings, "https://www.googleapis.com/auth/gmail.readonly") as client:
            base = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
            messages = (
                check(
                    client.get(
                        base,
                        params={"q": "has:attachment newer_than:30d", "maxResults": limit},
                        timeout=20,
                    )
                )
                .json()
                .get("messages", [])
            )
            for message in messages:
                url = f"{base}/{identifier(message['id'])}"
                info = check(client.get(url, params={"format": "metadata"}, timeout=20)).json()
                if info.get("sizeEstimate", 0) > settings.max_upload_bytes:
                    raise ValueError(
                        "An email exceeds the upload limit; import selected attachments manually."
                    )
                raw = check(client.get(url, params={"format": "raw"}, timeout=20)).json()["raw"]
                data = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
                if len(data) > settings.max_upload_bytes:
                    raise ValueError("Email exceeds the upload limit.")
                try:
                    files = attachments("message.eml", data, settings.max_upload_bytes)
                except ValueError as exc:
                    if str(exc).startswith("No PDF"):
                        continue
                    raise
                for filename, content in files:
                    run, created = engine.create(
                        filename=filename, content=content, mode="live", source="Gmail"
                    )
                    imported.append({"id": run["id"], "created": created})
    return imported


def bounded_bytes(chunks, limit):
    content = bytearray()
    for chunk in chunks:
        content.extend(chunk)
        if len(content) > limit:
            raise ValueError("Downloaded document exceeds the upload limit.")
    return bytes(content)


def append_sheet(settings, run):
    sheet = identifier(settings.google_sheet_id)
    target = quote(settings.google_sheet_range, safe="")
    with session(settings, "https://www.googleapis.com/auth/spreadsheets") as client:
        response = check(
            client.post(
                f"https://sheets.googleapis.com/v4/spreadsheets/{sheet}/values/{target}:append",
                params={"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"},
                json={"values": [export_row(run)]},
                timeout=30,
            )
        )
    return response.json().get("updates", {}).get("updatedRange", "")
