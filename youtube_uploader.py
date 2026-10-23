import os
import sys
import time
from pathlib import Path
from typing import List, Optional
import config

try:
    import google_auth_oauthlib.flow
    import googleapiclient.discovery
    import googleapiclient.errors
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.http import MediaFileUpload
except ImportError:
    pass

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def get_authenticated_service():
    """
    Authenticates with YouTube API via OAuth 2.0 and returns the youtube service client.
    Reuses token.json if already authorized.
    """
    creds = None
    token_file = config.YOUTUBE_TOKEN_FILE
    client_secret_file = Path(config.YOUTUBE_CLIENT_SECRET_FILE)

    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("[YOUTUBE] Refreshing expired OAuth credentials...")
            creds.refresh(Request())
        else:
            if not client_secret_file.exists():
                raise FileNotFoundError(
                    f"\n[YOUTUBE AUTH ERROR] Client secret file not found at: {client_secret_file}\n"
                    f"Please download your OAuth 2.0 client_secret.json from Google Cloud Console:\n"
                    f"1. Go to https://console.cloud.google.com/apis/credentials\n"
                    f"2. Create OAuth Client ID (Desktop Application)\n"
                    f"3. Download JSON and save as 'client_secret.json' in this folder."
                )

            print("[YOUTUBE] Initiating browser OAuth authentication...")
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                str(client_secret_file), SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save credentials for future runs
        with open(token_file, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
        print(f"[YOUTUBE] Saved authenticated credentials to {token_file}")

    return googleapiclient.discovery.build("youtube", "v3", credentials=creds)


def upload_video_to_youtube(
    video_file_path: Path,
    title: str,
    description: str,
    tags: Optional[List[str]] = None,
    category_id: str = "28",  # 28: Science & Technology, 24: Entertainment, 1: Film & Animation
    privacy_status: str = config.YOUTUBE_PRIVACY_STATUS
) -> str:
    """
    Uploads a video to YouTube with specified metadata and returns video URL.
    """
    if not video_file_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_file_path}")

    tags = tags or ["GoogleFlow", "Veo", "AIVideo", "Automation"]

    youtube = get_authenticated_service()

    body = {
        "snippet": {
            "title": title[:100],  # Max 100 chars
            "description": description[:5000],
            "tags": tags[:500],
            "categoryId": category_id
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False
        }
    }

    # Resumable upload in 4MB chunks
    media = MediaFileUpload(
        str(video_file_path),
        mimetype="video/mp4",
        chunksize=4 * 1024 * 1024,
        resumable=True
    )

    print(f"\n[YOUTUBE] Starting upload: {video_file_path.name}")
    print(f"[YOUTUBE] Title: {title}")
    print(f"[YOUTUBE] Privacy: {privacy_status}")

    insert_request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media
    )

    response = None
    while response is None:
        status, response = insert_request.next_chunk()
        if status:
            progress = int(status.progress() * 100)
            print(f"[YOUTUBE] Uploading... {progress}%", end="\r")

    video_id = response.get("id")
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    print(f"\n[SUCCESS] Upload Complete! Video URL: {video_url}")
    return video_url


if __name__ == "__main__":
    test_video = config.FINAL_VIDEO_DIR / "final_combined_video.mp4"
    if test_video.exists():
        upload_video_to_youtube(
            test_video,
            title="Test AI Video from Google Flow",
            description="Automated video generated via Google Flow pipeline.",
            privacy_status="private"
        )
    else:
        print(f"No video found at {test_video} to upload.")
