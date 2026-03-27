"""py2app 패키징 설정 — macOS .app 번들 생성."""
from setuptools import setup

APP = ["src/meeting_transcriber/app.py"]
DATA_FILES = [
    ("design", ["design/tokens_light.json", "design/tokens_dark.json"]),
    ("", ["resources/AppIcon.icns"]),
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
        "CFBundleName": "Scribe",
        "CFBundleDisplayName": "Scribe",
        "CFBundleIdentifier": "com.scribe.app",
        "CFBundleVersion": "1.5.0",
        "CFBundleShortVersionString": "1.5.0",
        "NSMicrophoneUsageDescription": (
            "Scribe needs microphone access "
            "to capture audio for real-time transcription."
        ),
        "NSApplicationName": "Scribe",
        "CFBundleIconFile": "AppIcon",
        "LSUIElement": False,
        "NSHighResolutionCapable": True,
    },
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
