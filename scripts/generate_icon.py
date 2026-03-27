"""macOS 앱 아이콘 생성 — QPainter 기반, 외부 의존 없음."""
from __future__ import annotations

import pathlib
import subprocess
import sys

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen


def generate_icon_image(size: int) -> QImage:
    """지정 크기의 앱 아이콘 이미지를 생성한다.

    Args:
        size: 이미지 가로/세로 크기 (px)

    Returns:
        생성된 QImage
    """
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(QColor(0, 0, 0, 0))

    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    s = size  # 편의 별칭
    margin = s * 0.03
    corner = s * 0.22  # macOS 앱 아이콘 표준 모서리 비율

    # 배경: 다크 라운드 렉트
    bg_rect = QRectF(margin, margin, s - margin * 2, s - margin * 2)
    bg_path = QPainterPath()
    bg_path.addRoundedRect(bg_rect, corner, corner)
    painter.fillPath(bg_path, QColor("#1C1C1E"))

    # 마이크 몸체 (캡슐 모양)
    mic_w = s * 0.18
    mic_h = s * 0.30
    mic_x = (s - mic_w) / 2
    mic_y = s * 0.22
    mic_path = QPainterPath()
    mic_path.addRoundedRect(QRectF(mic_x, mic_y, mic_w, mic_h), mic_w / 2, mic_w / 2)
    painter.fillPath(mic_path, QColor("#F5F5F7"))

    # 마이크 아크 (U자형 홀더)
    arc_pen = QPen(QColor("#F5F5F7"))
    arc_pen.setWidthF(s * 0.028)
    arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(arc_pen)

    arc_w = s * 0.30
    arc_h = s * 0.22
    arc_x = (s - arc_w) / 2
    arc_y = s * 0.35
    painter.drawArc(QRectF(arc_x, arc_y, arc_w, arc_h), 0, -180 * 16)

    # 스탠드 (세로선)
    stand_x = s / 2
    stand_top = arc_y + arc_h / 2
    stand_bottom = s * 0.68
    painter.drawLine(
        int(stand_x), int(stand_top),
        int(stand_x), int(stand_bottom),
    )

    # 베이스 (가로선)
    base_w = s * 0.16
    painter.drawLine(
        int(s / 2 - base_w / 2), int(stand_bottom),
        int(s / 2 + base_w / 2), int(stand_bottom),
    )

    # 사운드 웨이브 (빨간 악센트 호)
    wave_pen = QPen(QColor("#FF453A"))
    wave_pen.setWidthF(s * 0.022)
    wave_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(wave_pen)

    # 왼쪽 호
    for i, offset in enumerate([s * 0.08, s * 0.15]):
        arc_rect = QRectF(
            mic_x - offset,
            mic_y + mic_h * 0.1,
            mic_w + offset * 2,
            mic_h * 0.8,
        )
        opacity = 0.9 - i * 0.25
        wave_pen.setColor(QColor(255, 69, 58, int(255 * opacity)))
        painter.setPen(wave_pen)
        painter.drawArc(arc_rect, 120 * 16, 60 * 16)   # 왼쪽 호
        painter.drawArc(arc_rect, -60 * 16, -60 * 16)   # 오른쪽 호

    painter.end()
    return img


def main() -> None:
    """아이콘셋을 생성하고 .icns로 변환한다."""
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)  # noqa: F841

    project_root = pathlib.Path(__file__).parent.parent
    iconset_dir = project_root / "resources" / "AppIcon.iconset"
    iconset_dir.mkdir(parents=True, exist_ok=True)

    # macOS 필수 아이콘 크기
    sizes = [
        (16, "icon_16x16.png"),
        (32, "icon_16x16@2x.png"),
        (32, "icon_32x32.png"),
        (64, "icon_32x32@2x.png"),
        (128, "icon_128x128.png"),
        (256, "icon_128x128@2x.png"),
        (256, "icon_256x256.png"),
        (512, "icon_256x256@2x.png"),
        (512, "icon_512x512.png"),
        (1024, "icon_512x512@2x.png"),
    ]

    for size, filename in sizes:
        img = generate_icon_image(size)
        path = iconset_dir / filename
        img.save(str(path), "PNG")
        print(f"  Generated {filename} ({size}x{size})")

    # iconutil로 .icns 생성
    icns_path = project_root / "resources" / "AppIcon.icns"
    result = subprocess.run(
        ["iconutil", "-c", "icns", str(iconset_dir), "-o", str(icns_path)],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print(f"\n  AppIcon.icns created at {icns_path}")
        # iconset 디렉토리 정리
        import shutil

        shutil.rmtree(iconset_dir)
        print("  Cleaned up iconset directory")
    else:
        print(f"\n  Error: {result.stderr}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
