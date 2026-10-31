"""YouTube upload helpers: credentials from environment secrets (or local token files), resumable upload."""
import json, os
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def get_creds(env_names, local_file=None):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    info = next((os.environ[n] for n in env_names if os.environ.get(n, "").strip()), None)
    if info:
        creds = Credentials.from_authorized_user_info(json.loads(info), SCOPES)
    elif local_file and Path(local_file).exists():
        creds = Credentials.from_authorized_user_file(local_file, SCOPES)
    else:
        return None
    if not creds.valid and creds.refresh_token:
        creds.refresh(Request())
    return creds


def upload(creds, path, title, description, tags, made_for_kids, category="27", privacy=None):
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    privacy = privacy or os.environ.get("YT_PRIVACY", "private")
    body = {"snippet": {"title": title[:100], "description": description[:4900], "tags": tags[:30],
                        "categoryId": category, "defaultLanguage": "hi", "defaultAudioLanguage": "hi"},
            "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": bool(made_for_kids)}}
    req = build("youtube", "v3", credentials=creds).videos().insert(
        part="snippet,status", body=body, media_body=MediaFileUpload(str(path), resumable=True))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    print(f"{Path(path).name} uploaded as {privacy.upper()} (made for kids: {bool(made_for_kids)}): https://youtu.be/{resp['id']}")
    return resp["id"]
