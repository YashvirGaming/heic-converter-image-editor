"""
Image Studio PRO v1.0
HEIC/HEIF Converter + Image Resizer + Basic Editor + HD Upscaler

Install:
    pip install PySide6 Pillow pillow-heif

Run:
    python yashvir_image_studio.py

Optional:
    For stronger AI upscaling, an external AI model/backend can be added later.
    The built-in HD Upscale uses high-quality Lanczos resampling and sharpening.
"""

from __future__ import annotations

import os
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from pillow_heif import register_heif_opener

from PySide6.QtCore import Qt, QSize, QThread, Signal, QObject
from PySide6.QtGui import (
    QAction,
    QColor,
    QDragEnterEvent,
    QDropEvent,
    QFont,
    QImage,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QTextBrowser,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QTabWidget,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

register_heif_opener()

APP_NAME = "Yashvir Gaming Image Studio"
VERSION = "v1.0"
SUPPORTED_INPUTS = {".heic", ".heif", ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
OUTPUT_FORMATS = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
    "BMP": ".bmp",
    "TIFF": ".tiff",
}


# ----------------------------- Helpers -----------------------------

def pil_to_pixmap(image: Image.Image, max_size: QSize = QSize(760, 500)) -> QPixmap:
    img = image.copy()
    img.thumbnail((max_size.width(), max_size.height()), Image.Resampling.LANCZOS)
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA")

    data = img.tobytes("raw", img.mode)
    if img.mode == "RGB":
        qimg = QImage(data, img.width, img.height, img.width * 3, QImage.Format_RGB888)
    else:
        qimg = QImage(data, img.width, img.height, img.width * 4, QImage.Format_RGBA8888)

    return QPixmap.fromImage(qimg.copy())


def load_image(path: str) -> Image.Image:
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    return img.copy()


def ensure_rgb_for_jpeg(img: Image.Image) -> Image.Image:
    if img.mode in ("RGBA", "LA"):
        background = Image.new("RGB", img.size, "white")
        alpha = img.getchannel("A")
        background.paste(img.convert("RGB"), mask=alpha)
        return background
    if img.mode != "RGB":
        return img.convert("RGB")
    return img


def output_name(source: Path, extension: str) -> Path:
    return source.with_name(f"{source.stem}_converted{extension}")


# ----------------------------- Styles -----------------------------

THEMES = {
    "Neon Dark": """
        QWidget {
            background: #0a0d12;
            color: #e9f7ff;
            font-family: "Segoe UI";
            font-size: 10pt;
        }
        QMainWindow { background: #070a0f; }
        QTabWidget::pane {
            border: 1px solid #183040;
            background: #0b1017;
            border-radius: 8px;
        }
        QTabBar::tab {
            background: #0d141c;
            color: #8da6b7;
            padding: 11px 20px;
            margin-right: 3px;
            border: 1px solid #152632;
            border-bottom: none;
            border-top-left-radius: 7px;
            border-top-right-radius: 7px;
        }
        QTabBar::tab:selected {
            color: #66f7ff;
            border: 1px solid #22d3ee;
            background: #101c26;
        }
        QPushButton {
            background: #101923;
            border: 1px solid #21495a;
            border-radius: 7px;
            padding: 9px 14px;
            color: #eaffff;
            font-weight: 600;
        }
        QPushButton:hover {
            border-color: #00e5ff;
            background: #102631;
        }
        QPushButton:pressed { background: #123743; }
        QPushButton#primary {
            background: #083c49;
            border: 1px solid #00e5ff;
            color: #7ffaff;
        }
        QPushButton#danger {
            border-color: #7b3144;
            color: #ff91a9;
        }
        QLineEdit, QComboBox, QSpinBox {
            background: #080d13;
            border: 1px solid #234152;
            border-radius: 6px;
            padding: 7px;
            color: #efffff;
        }
        QComboBox QAbstractItemView {
            background: #0b1219;
            color: #efffff;
            selection-background-color: #104b5a;
        }
        QGroupBox {
            border: 1px solid #183646;
            border-radius: 8px;
            margin-top: 14px;
            padding-top: 12px;
            font-weight: 700;
            color: #71eff8;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
        }
        QListWidget, QTextEdit {
            background: #070b10;
            border: 1px solid #183646;
            border-radius: 8px;
        }
        QProgressBar {
            border: 1px solid #214152;
            border-radius: 6px;
            background: #070b10;
            text-align: center;
        }
        QProgressBar::chunk { background: #00d5e8; border-radius: 5px; }
        QSlider::groove:horizontal { background: #182832; height: 5px; border-radius: 3px; }
        QSlider::handle:horizontal {
            background: #00e5ff; width: 14px; margin: -5px 0; border-radius: 7px;
        }
        QCheckBox { spacing: 8px; }
        QScrollArea { border: none; }
    """,
    "Midnight Blue": """
        QWidget { background:#09111f; color:#e9f1ff; font-family:"Segoe UI"; }
        QPushButton { background:#111e32; border:1px solid #2d4d78; border-radius:7px; padding:9px 14px; }
        QPushButton:hover { border-color:#6ca8ff; background:#162943; }
        QPushButton#primary { background:#173a6b; border:1px solid #75adff; }
        QLineEdit,QComboBox,QSpinBox,QTextEdit,QListWidget { background:#07101d; border:1px solid #29415f; border-radius:7px; padding:7px; }
        QGroupBox { border:1px solid #29415f; border-radius:8px; margin-top:14px; padding-top:12px; color:#8fc0ff; font-weight:700; }
        QGroupBox::title { subcontrol-origin:margin; left:12px; padding:0 6px; }
        QTabBar::tab { background:#0d1727; color:#91a5c0; padding:11px 20px; border:1px solid #213650; }
        QTabBar::tab:selected { background:#162b48; color:#9ec9ff; border-color:#5e9be8; }
        QProgressBar { background:#07101d; border:1px solid #29415f; border-radius:6px; text-align:center; }
        QProgressBar::chunk { background:#438de0; }
    """,
    "Graphite": """
        QWidget { background:#181818; color:#eeeeee; font-family:"Segoe UI"; }
        QPushButton { background:#252525; border:1px solid #484848; border-radius:6px; padding:9px 14px; }
        QPushButton:hover { background:#303030; border-color:#888888; }
        QPushButton#primary { background:#333333; border:1px solid #bdbdbd; }
        QLineEdit,QComboBox,QSpinBox,QTextEdit,QListWidget { background:#141414; border:1px solid #414141; border-radius:6px; padding:7px; }
        QGroupBox { border:1px solid #444; border-radius:8px; margin-top:14px; padding-top:12px; color:#ddd; }
        QGroupBox::title { subcontrol-origin:margin; left:12px; padding:0 6px; }
        QTabBar::tab { background:#202020; color:#aaa; padding:11px 20px; border:1px solid #3a3a3a; }
        QTabBar::tab:selected { background:#333; color:white; }
        QProgressBar { background:#121212; border:1px solid #444; border-radius:6px; text-align:center; }
        QProgressBar::chunk { background:#888; }
    """
}


# ----------------------------- Worker -----------------------------

@dataclass
class ConvertJob:
    source: str
    output: str
    fmt: str
    quality: int


class ConverterWorker(QObject):
    progress = Signal(int)
    message = Signal(str)
    finished = Signal(int, int, str)
    error = Signal(str)

    def __init__(self, jobs: list[ConvertJob]):
        super().__init__()
        self.jobs = jobs
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        success = 0
        failed = 0
        total = len(self.jobs)

        for index, job in enumerate(self.jobs, 1):
            if self._stop:
                self.message.emit("Conversion cancelled.")
                break

            try:
                src = Path(job.source)
                dst = Path(job.output)
                dst.parent.mkdir(parents=True, exist_ok=True)

                self.message.emit(f"Converting: {src.name}")
                image = load_image(str(src))

                if job.fmt == "JPEG":
                    image = ensure_rgb_for_jpeg(image)
                    image.save(dst, "JPEG", quality=job.quality, optimize=True)
                elif job.fmt == "PNG":
                    image.save(dst, "PNG", optimize=True)
                elif job.fmt == "WEBP":
                    if image.mode not in ("RGB", "RGBA"):
                        image = image.convert("RGBA")
                    image.save(dst, "WEBP", quality=job.quality, method=6)
                elif job.fmt == "BMP":
                    image.convert("RGB").save(dst, "BMP")
                elif job.fmt == "TIFF":
                    image.save(dst, "TIFF", compression="tiff_lzw")
                else:
                    raise ValueError(f"Unsupported format: {job.fmt}")

                success += 1
                self.message.emit(f"✓ Saved: {dst.name}")
            except Exception as exc:
                failed += 1
                self.message.emit(f"✗ Failed: {Path(job.source).name} — {exc}")

            self.progress.emit(int(index / total * 100))

        self.finished.emit(success, failed, "Done")


# ----------------------------- Drop Area -----------------------------

class DropArea(QFrame):
    files_dropped = Signal(list)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setObjectName("dropArea")
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("⇩")
        icon.setFont(QFont("Segoe UI", 38, QFont.Weight.Bold))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("DROP HEIC / HEIF / IMAGES HERE")
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sub = QLabel("or use the Add Images button below • bulk processing supported")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(sub)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        paths = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                path = url.toLocalFile()
                if Path(path).suffix.lower() in SUPPORTED_INPUTS:
                    paths.append(path)
        if paths:
            self.files_dropped.emit(paths)
        event.acceptProposedAction()


# ----------------------------- About Dialog -----------------------------

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About / Credits")
        self.resize(620, 520)

        root = QVBoxLayout(self)
        title = QLabel("IMAGE STUDIO PRO V1.0")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet("color:#63f6ff;")
        root.addWidget(title)

        version = QLabel("Professional image conversion, resizing & editing • v1.0")
        root.addWidget(version)

        text = QTextBrowser()
        text.setReadOnly(True)
        text.setHtml("""
        <h2 style="color:#63f6ff;">Yashvir Gaming</h2>
        <p><b>Image Studio v1.0</b></p>
        <p>
        A desktop image utility built around PySide6, Pillow and pillow-heif.
        Designed for fast HEIC/HEIF conversion, bulk workflows, resizing,
        editing and high-quality enlargement.
        </p>

        <h3 style="color:#63f6ff;">Features</h3>
        <ul>
          <li>HEIC / HEIF → JPEG, PNG, WEBP, BMP and TIFF</li>
          <li>Drag & drop importing</li>
          <li>Bulk conversion</li>
          <li>Live conversion progress and result log</li>
          <li>Preview selected images</li>
          <li>Open Results folder</li>
          <li>Image resizing with aspect-ratio lock</li>
          <li>Brightness, contrast, saturation and sharpness</li>
          <li>Rotate, flip, grayscale and auto-enhance</li>
          <li>High-quality HD enlargement using Lanczos + sharpening</li>
          <li>Multiple dark themes</li>
        </ul>

        <h3 style="color:#63f6ff;">Credits</h3>
        <p><b>By Yashvir Gaming</b></p>
        <p>YouTube: <a href="https://youtube.com/@yashvirgaming">youtube.com/@yashvirgaming</a></p>
        <p>Version: v1.0</p>

        <h3 style="color:#63f6ff;">Technology</h3>
        <p>Python • PySide6 • Pillow • pillow-heif</p>

        <p style="color:#9aaab5;">
        This application processes images locally on your computer.
        No cloud upload is required by the application.
        </p>
        """)
        text.setOpenExternalLinks(True)
        root.addWidget(text)

        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        root.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)


# ----------------------------- Main Window -----------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(f"{APP_NAME} {VERSION}")
        self.resize(1182, 1171)
        self.setMinimumSize(1000, 700)

        self.files: list[str] = []
        self.current_image: Image.Image | None = None
        self.current_path: str | None = None
        self.worker_thread: QThread | None = None
        self.worker: ConverterWorker | None = None
        self.results_dir = Path.cwd() / "Results"
        self.results_dir.mkdir(exist_ok=True)

        self.build_ui()
        self.apply_theme("Neon Dark")

    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(18, 15, 18, 15)
        root.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title_box = QVBoxLayout()

        title = QLabel("YASHVIR GAMING")
        title.setFont(QFont("Segoe UI", 25, QFont.Weight.Bold))
        title.setStyleSheet("color:#6af7ff;")
        title_box.addWidget(title)

        subtitle = QLabel("IMAGE STUDIO  •  HEIC CONVERTER + EDITOR + UPSCALER")
        subtitle.setStyleSheet("color:#7894a4; letter-spacing:1px;")
        title_box.addWidget(subtitle)

        header.addLayout(title_box)
        header.addStretch()

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(THEMES.keys())
        self.theme_combo.setCurrentText("Neon Dark")
        self.theme_combo.currentTextChanged.connect(self.apply_theme)
        header.addWidget(QLabel("Theme:"))
        header.addWidget(self.theme_combo)

        about = QPushButton("Credits / About")
        about.clicked.connect(lambda: AboutDialog(self).exec())
        header.addWidget(about)

        root.addLayout(header)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.build_converter_tab(), "⚡ Converter")
        self.tabs.addTab(self.build_editor_tab(), "✦ Editor")
        self.tabs.addTab(self.build_resizer_tab(), "↗ Resize & HD Upscale")
        self.tabs.addTab(self.build_results_tab(), "▣ Results")
        root.addWidget(self.tabs)

        status = QHBoxLayout()
        self.status_label = QLabel("Ready • Local processing enabled")
        self.status_label.setStyleSheet("color:#6e8795;")
        status.addWidget(self.status_label)
        status.addStretch()
        credit = QLabel("By Yashvir Gaming • v1.0")
        credit.setStyleSheet("color:#5eeaf4;")
        status.addWidget(credit)
        root.addLayout(status)

    # ---------- Converter ----------
    def build_converter_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        self.drop_area = DropArea()
        self.drop_area.setMinimumHeight(150)
        self.drop_area.setStyleSheet("""
            QFrame#dropArea {
                border: 2px dashed #1f7180;
                border-radius: 12px;
                background: #09151c;
            }
            QFrame#dropArea:hover { border-color:#00e5ff; }
        """)
        self.drop_area.files_dropped.connect(self.add_files)
        layout.addWidget(self.drop_area)

        controls = QGroupBox("Conversion Settings")
        form = QGridLayout(controls)

        add_btn = QPushButton("＋ Add Images")
        add_btn.clicked.connect(self.browse_images)

        folder_btn = QPushButton("＋ Add Folder")
        folder_btn.clicked.connect(self.browse_folder)

        clear_btn = QPushButton("Clear List")
        clear_btn.setObjectName("danger")
        clear_btn.clicked.connect(self.clear_files)

        form.addWidget(add_btn, 0, 0)
        form.addWidget(folder_btn, 0, 1)
        form.addWidget(clear_btn, 0, 2)

        form.addWidget(QLabel("Output format:"), 1, 0)
        self.format_combo = QComboBox()
        self.format_combo.addItems(OUTPUT_FORMATS.keys())
        self.format_combo.setCurrentText("JPEG")
        form.addWidget(self.format_combo, 1, 1)

        form.addWidget(QLabel("JPEG/WEBP quality:"), 1, 2)
        self.quality = QSpinBox()
        self.quality.setRange(1, 100)
        self.quality.setValue(95)
        form.addWidget(self.quality, 1, 3)

        self.keep_structure = QCheckBox("Preserve source folders")
        form.addWidget(self.keep_structure, 2, 0, 1, 2)

        layout.addWidget(controls)

        middle = QHBoxLayout()

        list_box = QGroupBox("Import Queue")
        list_layout = QVBoxLayout(list_box)
        self.file_list = QListWidget()
        self.file_list.currentRowChanged.connect(self.preview_selected)
        list_layout.addWidget(self.file_list)
        middle.addWidget(list_box, 1)

        preview_box = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_box)
        self.converter_preview = QLabel("Select an image to preview")
        self.converter_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.converter_preview.setMinimumSize(420, 320)
        self.converter_preview.setStyleSheet("color:#607887;")
        preview_layout.addWidget(self.converter_preview)

        self.image_info = QLabel("")
        self.image_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(self.image_info)
        middle.addWidget(preview_box, 2)

        layout.addLayout(middle, 1)

        action_row = QHBoxLayout()
        self.convert_btn = QPushButton("⚡ CONVERT")
        self.convert_btn.setObjectName("primary")
        self.convert_btn.setMinimumHeight(46)
        self.convert_btn.clicked.connect(self.start_conversion)

        open_results = QPushButton("Open Results")
        open_results.clicked.connect(self.open_results)

        action_row.addWidget(self.convert_btn, 3)
        action_row.addWidget(open_results, 1)
        layout.addLayout(action_row)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(130)
        layout.addWidget(self.log)

        return page

    def browse_images(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Images",
            "",
            "Images (*.heic *.heif *.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff)"
        )
        self.add_files(paths)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if not folder:
            return
        found = []
        for p in Path(folder).rglob("*"):
            if p.is_file() and p.suffix.lower() in SUPPORTED_INPUTS:
                found.append(str(p))
        self.add_files(found)

    def add_files(self, paths: list[str]):
        added = 0
        existing = set(self.files)
        for path in paths:
            p = str(Path(path).resolve())
            if p not in existing and Path(p).suffix.lower() in SUPPORTED_INPUTS:
                self.files.append(p)
                self.file_list.addItem(p)
                existing.add(p)
                added += 1
        self.status_label.setText(f"Added {added} image(s) • Queue: {len(self.files)}")
        if added:
            self.file_list.setCurrentRow(self.file_list.count() - added)

    def clear_files(self):
        self.files.clear()
        self.file_list.clear()
        self.converter_preview.clear()
        self.image_info.clear()
        self.status_label.setText("Queue cleared.")

    def preview_selected(self, row: int):
        if row < 0 or row >= len(self.files):
            return
        path = self.files[row]
        try:
            img = load_image(path)
            self.converter_preview.setPixmap(pil_to_pixmap(img, QSize(650, 430)))
            self.image_info.setText(
                f"{Path(path).name}  •  {img.width} × {img.height}  •  {img.mode}"
            )
        except Exception as exc:
            self.converter_preview.setText(f"Preview error:\n{exc}")

    def start_conversion(self):
        if not self.files:
            QMessageBox.information(self, "Nothing to convert", "Add one or more images first.")
            return

        fmt = self.format_combo.currentText()
        ext = OUTPUT_FORMATS[fmt]
        quality = self.quality.value()

        jobs = []
        for source in self.files:
            src = Path(source)
            if self.keep_structure.isChecked():
                try:
                    rel = src.parent.relative_to(Path(self.files[0]).parent)
                except ValueError:
                    rel = Path()
                out_dir = self.results_dir / rel
            else:
                out_dir = self.results_dir

            jobs.append(ConvertJob(
                source=str(src),
                output=str(out_dir / f"{src.stem}_converted{ext}"),
                fmt=fmt,
                quality=quality
            ))

        self.convert_btn.setEnabled(False)
        self.progress.setValue(0)
        self.log.clear()
        self.log.append("▶ Conversion started...")
        self.log.append(f"Format: {fmt} • Files: {len(jobs)}")

        self.worker_thread = QThread()
        self.worker = ConverterWorker(jobs)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.message.connect(self.log.append)
        self.worker.finished.connect(self.conversion_finished)
        self.worker.error.connect(lambda e: self.log.append("ERROR: " + e))

        self.worker_thread.start()

    def conversion_finished(self, success: int, failed: int, _msg: str):
        self.log.append("")
        self.log.append(f"✓ Finished • Success: {success} • Failed: {failed}")
        self.status_label.setText(f"Conversion complete • {success} successful • {failed} failed")
        self.convert_btn.setEnabled(True)
        self.open_results()

        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()
        self.worker = None
        self.worker_thread = None
        self.refresh_results()

    # ---------- Editor ----------
    def build_editor_tab(self):
        page = QWidget()
        layout = QHBoxLayout(page)

        left = QVBoxLayout()
        source_box = QGroupBox("Image")
        source_layout = QVBoxLayout(source_box)

        open_btn = QPushButton("Open Image")
        open_btn.clicked.connect(self.open_editor_image)
        source_layout.addWidget(open_btn)

        self.editor_preview = QLabel("Open an image to edit")
        self.editor_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.editor_preview.setMinimumSize(650, 480)
        source_layout.addWidget(self.editor_preview)

        self.editor_info = QLabel("")
        self.editor_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        source_layout.addWidget(self.editor_info)

        left.addWidget(source_box)
        layout.addLayout(left, 3)

        right = QVBoxLayout()

        adjustments = QGroupBox("Basic Photoshop-style Adjustments")
        grid = QGridLayout(adjustments)

        self.brightness = self.make_slider()
        self.contrast = self.make_slider()
        self.saturation = self.make_slider()
        self.sharpness = self.make_slider()

        for row, (label, slider) in enumerate([
            ("Brightness", self.brightness),
            ("Contrast", self.contrast),
            ("Saturation", self.saturation),
            ("Sharpness", self.sharpness),
        ]):
            grid.addWidget(QLabel(label), row, 0)
            grid.addWidget(slider, row, 1)

        right.addWidget(adjustments)

        tools = QGroupBox("Edit Tools")
        tool_grid = QGridLayout(tools)

        for i, (text, slot) in enumerate([
            ("↶ Rotate Left", lambda: self.rotate_editor(-90)),
            ("↷ Rotate Right", lambda: self.rotate_editor(90)),
            ("↔ Flip H", lambda: self.flip_editor(True)),
            ("↕ Flip V", lambda: self.flip_editor(False)),
            ("☼ Auto Enhance", self.auto_enhance),
            ("◐ Grayscale", self.grayscale),
            ("Reset", self.reset_editor),
            ("Save As", self.save_editor),
        ]):
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            tool_grid.addWidget(btn, i // 2, i % 2)

        right.addWidget(tools)
        right.addStretch()

        layout.addLayout(right, 1)

        for slider in [self.brightness, self.contrast, self.saturation, self.sharpness]:
            slider.valueChanged.connect(self.update_editor_preview)

        return page

    def make_slider(self):
        s = QSlider(Qt.Orientation.Horizontal)
        s.setRange(0, 200)
        s.setValue(100)
        return s

    def open_editor_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "", "Images (*.heic *.heif *.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff)"
        )
        if path:
            self.current_path = path
            self.current_image = load_image(path)
            self.reset_adjustments()
            self.update_editor_preview()

    def reset_adjustments(self):
        for s in [self.brightness, self.contrast, self.saturation, self.sharpness]:
            s.blockSignals(True)
            s.setValue(100)
            s.blockSignals(False)

    def edited_image(self) -> Image.Image | None:
        if self.current_image is None:
            return None

        img = self.current_image.copy()
        img = ImageEnhance.Brightness(img).enhance(self.brightness.value() / 100)
        img = ImageEnhance.Contrast(img).enhance(self.contrast.value() / 100)
        img = ImageEnhance.Color(img).enhance(self.saturation.value() / 100)
        img = ImageEnhance.Sharpness(img).enhance(self.sharpness.value() / 100)
        return img

    def update_editor_preview(self):
        if self.current_image is None:
            return
        img = self.edited_image()
        self.editor_preview.setPixmap(pil_to_pixmap(img, QSize(700, 500)))
        self.editor_info.setText(
            f"{Path(self.current_path).name}  •  {img.width} × {img.height}"
        )

    def rotate_editor(self, angle):
        if self.current_image is None:
            return
        self.current_image = self.current_image.rotate(-angle, expand=True)
        self.update_editor_preview()

    def flip_editor(self, horizontal):
        if self.current_image is None:
            return
        self.current_image = ImageOps.mirror(self.current_image) if horizontal else ImageOps.flip(self.current_image)
        self.update_editor_preview()

    def auto_enhance(self):
        if self.current_image is None:
            return
        self.current_image = ImageOps.autocontrast(self.current_image.convert("RGB"))
        self.update_editor_preview()

    def grayscale(self):
        if self.current_image is None:
            return
        self.current_image = ImageOps.grayscale(self.current_image).convert("RGB")
        self.update_editor_preview()

    def reset_editor(self):
        if not self.current_path:
            return
        self.current_image = load_image(self.current_path)
        self.reset_adjustments()
        self.update_editor_preview()

    def save_editor(self):
        if self.current_image is None:
            QMessageBox.information(self, "No image", "Open an image first.")
            return

        path, selected = QFileDialog.getSaveFileName(
            self, "Save Edited Image", "", "JPEG (*.jpg);;PNG (*.png);;WEBP (*.webp);;TIFF (*.tiff)"
        )
        if not path:
            return

        try:
            img = self.edited_image()
            ext = Path(path).suffix.lower()
            if ext in (".jpg", ".jpeg"):
                ensure_rgb_for_jpeg(img).save(path, "JPEG", quality=95)
            elif ext == ".png":
                img.save(path, "PNG", optimize=True)
            elif ext == ".webp":
                img.save(path, "WEBP", quality=95, method=6)
            else:
                img.save(path, "TIFF", compression="tiff_lzw")

            QMessageBox.information(self, "Saved", f"Image saved successfully:\n{path}")
            self.refresh_results()
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", str(exc))

    # ---------- Resize / Upscale ----------
    def build_resizer_tab(self):
        page = QWidget()
        layout = QHBoxLayout(page)

        left = QVBoxLayout()

        source = QGroupBox("Source Image")
        source_layout = QVBoxLayout(source)
        open_btn = QPushButton("Open Image")
        open_btn.clicked.connect(self.open_resize_image)
        source_layout.addWidget(open_btn)

        self.resize_preview = QLabel("Open an image to begin")
        self.resize_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.resize_preview.setMinimumSize(680, 500)
        source_layout.addWidget(self.resize_preview)

        self.resize_info = QLabel("")
        self.resize_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        source_layout.addWidget(self.resize_info)

        left.addWidget(source)
        layout.addLayout(left, 3)

        right = QVBoxLayout()

        settings = QGroupBox("Resize / HD Upscale")
        form = QFormLayout(settings)

        self.resize_w = QSpinBox()
        self.resize_w.setRange(1, 30000)
        self.resize_w.setValue(1920)

        self.resize_h = QSpinBox()
        self.resize_h.setRange(1, 30000)
        self.resize_h.setValue(1080)

        self.lock_aspect = QCheckBox("Lock aspect ratio")
        self.lock_aspect.setChecked(True)

        self.scale_combo = QComboBox()
        self.scale_combo.addItems(["Custom", "2× HD", "3× HD", "4× HD", "1920×1080", "2560×1440", "3840×2160"])
        self.scale_combo.currentTextChanged.connect(self.apply_scale_preset)

        form.addRow("Preset:", self.scale_combo)
        form.addRow("Width:", self.resize_w)
        form.addRow("Height:", self.resize_h)
        form.addRow("", self.lock_aspect)
        right.addWidget(settings)

        up = QGroupBox("Quality")
        up_layout = QVBoxLayout(up)
        self.upscale_sharp = QSlider(Qt.Orientation.Horizontal)
        self.upscale_sharp.setRange(0, 200)
        self.upscale_sharp.setValue(70)
        up_layout.addWidget(QLabel("Post-upscale sharpening"))
        up_layout.addWidget(self.upscale_sharp)
        up_layout.addWidget(QLabel("Built-in HD mode: Lanczos resampling + controlled sharpening"))
        right.addWidget(up)

        self.resize_btn = QPushButton("↗ RESIZE / HD UPSCALE")
        self.resize_btn.setObjectName("primary")
        self.resize_btn.setMinimumHeight(48)
        self.resize_btn.clicked.connect(self.resize_or_upscale)
        right.addWidget(self.resize_btn)

        save_btn = QPushButton("Save Result")
        save_btn.clicked.connect(self.save_resize_result)
        right.addWidget(save_btn)

        right.addStretch()
        layout.addLayout(right, 1)

        self.resize_w.valueChanged.connect(self.sync_height)
        self.resize_h.valueChanged.connect(self.sync_width)

        return page

    def open_resize_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "", "Images (*.heic *.heif *.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff)"
        )
        if not path:
            return
        self.resize_source_path = path
        self.resize_source_image = load_image(path)
        self.resize_result = None
        img = self.resize_source_image
        self.resize_w.blockSignals(True)
        self.resize_h.blockSignals(True)
        self.resize_w.setValue(img.width)
        self.resize_h.setValue(img.height)
        self.resize_w.blockSignals(False)
        self.resize_h.blockSignals(False)
        self.resize_preview.setPixmap(pil_to_pixmap(img, QSize(720, 520)))
        self.resize_info.setText(f"{Path(path).name}  •  {img.width} × {img.height}")

    def apply_scale_preset(self, value):
        if not hasattr(self, "resize_source_image") or self.resize_source_image is None:
            return
        img = self.resize_source_image
        presets = {
            "2× HD": (img.width * 2, img.height * 2),
            "3× HD": (img.width * 3, img.height * 3),
            "4× HD": (img.width * 4, img.height * 4),
            "1920×1080": (1920, 1080),
            "2560×1440": (2560, 1440),
            "3840×2160": (3840, 2160),
        }
        if value in presets:
            w, h = presets[value]
            self.resize_w.blockSignals(True)
            self.resize_h.blockSignals(True)
            self.resize_w.setValue(w)
            self.resize_h.setValue(h)
            self.resize_w.blockSignals(False)
            self.resize_h.blockSignals(False)

    def sync_height(self, w):
        if self.lock_aspect.isChecked() and hasattr(self, "resize_source_image") and self.resize_source_image:
            ratio = self.resize_source_image.height / self.resize_source_image.width
            self.resize_h.blockSignals(True)
            self.resize_h.setValue(max(1, round(w * ratio)))
            self.resize_h.blockSignals(False)

    def sync_width(self, h):
        if self.lock_aspect.isChecked() and hasattr(self, "resize_source_image") and self.resize_source_image:
            ratio = self.resize_source_image.width / self.resize_source_image.height
            self.resize_w.blockSignals(True)
            self.resize_w.setValue(max(1, round(h * ratio)))
            self.resize_w.blockSignals(False)

    def resize_or_upscale(self):
        if not hasattr(self, "resize_source_image") or self.resize_source_image is None:
            QMessageBox.information(self, "No image", "Open an image first.")
            return

        try:
            target = self.resize_source_image.resize(
                (self.resize_w.value(), self.resize_h.value()),
                Image.Resampling.LANCZOS
            )

            strength = self.upscale_sharp.value() / 100
            if strength > 0:
                # UnsharpMask gives a clean enhancement after enlargement.
                target = target.filter(
                    ImageFilter.UnsharpMask(
                        radius=1.5,
                        percent=int(80 + strength * 100),
                        threshold=3
                    )
                )

            self.resize_result = target
            self.resize_preview.setPixmap(pil_to_pixmap(target, QSize(720, 520)))
            self.resize_info.setText(
                f"Result • {target.width} × {target.height} • Lanczos HD enlargement"
            )
            self.status_label.setText("HD resize completed. Click Save Result to export it.")
        except Exception as exc:
            QMessageBox.critical(self, "Resize failed", str(exc))

    def save_resize_result(self):
        if not hasattr(self, "resize_result") or self.resize_result is None:
            QMessageBox.information(self, "No result", "Run Resize / HD Upscale first.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Save Resized Image", "", "PNG (*.png);;JPEG (*.jpg);;WEBP (*.webp);;TIFF (*.tiff)"
        )
        if not path:
            return
        try:
            ext = Path(path).suffix.lower()
            if ext in (".jpg", ".jpeg"):
                ensure_rgb_for_jpeg(self.resize_result).save(path, "JPEG", quality=95)
            elif ext == ".webp":
                self.resize_result.save(path, "WEBP", quality=95, method=6)
            elif ext == ".tiff":
                self.resize_result.save(path, "TIFF", compression="tiff_lzw")
            else:
                self.resize_result.save(path, "PNG", optimize=True)

            QMessageBox.information(self, "Saved", f"Saved successfully:\n{path}")
            self.refresh_results()
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", str(exc))

    # ---------- Results ----------
    def build_results_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        top = QHBoxLayout()
        refresh = QPushButton("↻ Refresh")
        refresh.clicked.connect(self.refresh_results)
        open_btn = QPushButton("Open Results Folder")
        open_btn.clicked.connect(self.open_results)
        top.addWidget(refresh)
        top.addWidget(open_btn)
        top.addStretch()
        layout.addLayout(top)

        self.results_list = QListWidget()
        layout.addWidget(self.results_list)

        self.results_preview = QLabel("Select a result")
        self.results_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.results_preview.setMinimumHeight(250)
        layout.addWidget(self.results_preview)

        self.results_list.currentItemChanged.connect(self.preview_result)

        return page

    def refresh_results(self):
        self.results_list.clear()
        if not self.results_dir.exists():
            self.results_dir.mkdir(parents=True, exist_ok=True)

        for p in sorted(self.results_dir.rglob("*")):
            if p.is_file() and p.suffix.lower() in SUPPORTED_INPUTS:
                self.results_list.addItem(str(p))

    def preview_result(self, current, _previous):
        if not current:
            return
        path = current.text()
        try:
            img = load_image(path)
            self.results_preview.setPixmap(pil_to_pixmap(img, QSize(900, 350)))
        except Exception:
            self.results_preview.setText("Unable to preview result.")

    def open_results(self):
        self.results_dir.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(self.results_dir))
            elif sys.platform == "darwin":
                os.system(f'open "{self.results_dir}"')
            else:
                os.system(f'xdg-open "{self.results_dir}"')
        except Exception as exc:
            QMessageBox.warning(self, "Open Results", str(exc))

    # ---------- Theme ----------
    def apply_theme(self, name):
        app = QApplication.instance()
        if app:
            app.setStyleSheet(THEMES.get(name, THEMES["Neon Dark"]))


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("Yashvir Gaming")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
