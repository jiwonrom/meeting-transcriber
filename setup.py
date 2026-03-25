"""py2app 패키징 설정 — macOS .app 번들 생성."""
from setuptools import setup

APP = ["src/meeting_transcriber/app.py"]
DATA_FILES = [
    ("design", ["design/tokens_light.json", "design/tokens_dark.json"]),
]
OPTIONS = {
    "argv_emulation": False,
    "packages": ["meeting_transcriber"],
    "includes": [
        "meeting_transcriber.ui",
        "meeting_transcriber.core",
        "meeting_transcriber.storage",
        "meeting_transcriber.utils",
        "meeting_transcriber.ai",
    ],
    "plist": {
        "CFBundleName": "Meeting Transcriber",
        "CFBundleDisplayName": "Meeting Transcriber",
        "CFBundleIdentifier": "com.meetingtranscriber.app",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "NSMicrophoneUsageDescription": (
            "Meeting Transcriber needs microphone access "
            "to capture audio for real-time transcription."
        ),
        "LSUIElement": True,
        "NSHighResolutionCapable": True,
    },
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
