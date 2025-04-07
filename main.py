import sys
import os
import logging # Use logging instead of print for errors/info
import time
import base64 # Needed for embedding raster in SVG
from io import BytesIO # Needed for in-memory image operations

# Import necessary PyQt6 modules
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QWidget, QPushButton, QProgressBar, QFileDialog, QComboBox, QCheckBox, QSpinBox, QDialog,
    QLineEdit, QMessageBox, QSizePolicy, QStyle
)
# ***** FIX: Added QBuffer, QIODevice imports *****
from PyQt6.QtCore import (
    Qt, QSize, QObject, QThread, pyqtSignal, QMimeData, QUrl, QSettings,
    QRect, QPoint, QRectF, QBuffer, QIODevice
)
from PyQt6.QtGui import QIcon, QPixmap, QImage, QPainter, QDragEnterEvent, QDropEvent
# Import SVG module - requires PyQt6-Svg (usually included with PyQt6)
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtSvg import QSvgRenderer

# Import Pillow (PIL) for image manipulation
from PIL import Image
import requests
import json # For potential future update checks using JSON API

# --- Configuration ---
APP_NAME = "Image Converter"
ORGANIZATION_NAME = "Zanz Softwares" # For QSettings
APP_VERSION = "1.7.0" # Updated version
GITHUB_REPO = "zanz-softwares/image-converter" # For update checks

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

# --- Main Application Window ---
class ImageConverterApp(QMainWindow):

    def __init__(self):
        super().__init__()
        # Use global APP_VERSION for window title
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION} - Zanz Softwares")
        self.setMinimumSize(600, 550)  # Adjusted minimum size
        self.resize(600, 600)  # Adjusted default size

        # --- State Variables ---
        self.current_image_path = None # Path to the loaded image/svg
        self.current_pixmap = None # Holds the QPixmap for preview
        self.is_svg_input = False # Flag to track input type
        self.settings = QSettings(ORGANIZATION_NAME, APP_NAME)
        self.last_input_dir = self.settings.value("lastImageInputDir", "")
        self.last_output_dir = self.settings.value("lastImageOutputDir", os.path.join(os.path.expanduser("~"), "Desktop")) # Default to Desktop

        # --- Set Window Icon ---
        # Try loading from common names/locations
        icon_paths = ["icon.ico", "icon.png", os.path.join(os.path.dirname(__file__), "icon.ico"), os.path.join(os.path.dirname(__file__), "icon.png")]
        for icon_path in icon_paths:
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
                logging.info(f"Loaded icon from: {icon_path}")
                break
        else:
             logging.warning("Application icon (icon.ico/icon.png) not found.")


        # --- Initialize UI ---
        self._init_ui()
        self._connect_signals()
        self._update_button_states() # Initial state

    def _init_ui(self):
        """ Creates and arranges all UI widgets. """
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15) # Add margins
        main_layout.setSpacing(10) # Add spacing between widgets

        # --- Drop Area ---
        self.drop_label = QLabel("Drag and drop image or SVG here\nor click to select file")
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_label.setMinimumHeight(150)
        self.drop_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.drop_label.setWordWrap(True)
        self.set_drop_label_style("default") # Use helper for styling
        # Allow drop_label itself to accept drops
        self.drop_label.setAcceptDrops(True)
        self.drop_label.dragEnterEvent = self.dragEnterEvent # Connect events directly
        self.drop_label.dragLeaveEvent = self.dragLeaveEvent
        self.drop_label.dropEvent = self.dropEvent
        self.drop_label.mousePressEvent = self.select_file # Click to select

        main_layout.addWidget(self.drop_label)

        # --- Image Details ---
        self.details_label = QLabel("File Details: (Load a file)")
        self.details_label.setStyleSheet("font-weight: bold; font-size: 11pt; margin-top: 10px;")
        main_layout.addWidget(self.details_label)

        # --- Output Format Selection ---
        format_group_layout = QHBoxLayout() # Horizontal layout for format checkboxes
        format_group_layout.addWidget(QLabel("Convert to:"))
        self.png_checkbox = QCheckBox("PNG")
        self.jpeg_checkbox = QCheckBox("JPEG")
        self.ico_checkbox = QCheckBox("ICO")
        self.svg_checkbox = QCheckBox("SVG") # Added SVG checkbox
        format_group_layout.addWidget(self.png_checkbox)
        format_group_layout.addWidget(self.jpeg_checkbox)
        format_group_layout.addWidget(self.ico_checkbox)
        format_group_layout.addWidget(self.svg_checkbox)
        format_group_layout.addStretch()
        main_layout.addLayout(format_group_layout)

        # --- Thumbnail Options ---
        thumb_group_layout = QHBoxLayout()
        thumb_group_layout.addWidget(QLabel("Resize to Preset:"))
        self.youtube_checkbox = QCheckBox("YouTube (1280x720)")
        self.tiktok_checkbox = QCheckBox("TikTok (1080x1920)")
        self.facebook_checkbox = QCheckBox("Facebook (180x180)")
        # Add tooltips for clarity
        self.youtube_checkbox.setToolTip("Resize output to 1280x720 pixels.")
        self.tiktok_checkbox.setToolTip("Resize output to 1080x1920 pixels.")
        self.facebook_checkbox.setToolTip("Resize output to 180x180 pixels.")
        thumb_group_layout.addWidget(self.youtube_checkbox)
        thumb_group_layout.addWidget(self.tiktok_checkbox)
        thumb_group_layout.addWidget(self.facebook_checkbox)
        thumb_group_layout.addStretch()
        main_layout.addLayout(thumb_group_layout)

        # --- Action Buttons ---
        button_layout = QHBoxLayout()
        # Use standard icons now that QStyle is imported
        self.convert_btn = QPushButton(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)," Convert")
        self.convert_btn.setToolTip("Convert the loaded image to the selected formats.")
        self.convert_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; border-radius: 5px; padding: 8px 15px; } QPushButton:hover { background-color: #45a049; } QPushButton:disabled { background-color: #cccccc; }")

        self.update_btn = QPushButton(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload)," Check for Updates")
        self.update_btn.setToolTip("Check GitHub for newer versions of the application.")
        self.update_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; border-radius: 5px; padding: 8px 15px; } QPushButton:hover { background-color: #1e88e5; }")

        button_layout.addStretch() # Push buttons to the right
        button_layout.addWidget(self.convert_btn)
        button_layout.addWidget(self.update_btn)
        main_layout.addLayout(button_layout)

        # --- Progress Bar ---
        self.progress = QProgressBar()
        self.progress.setStyleSheet("""
            QProgressBar { border: 1px solid #bbb; border-radius: 5px; text-align: center; height: 20px; font-size: 10pt; }
            QProgressBar::chunk { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4CAF50, stop:1 #8BC34A); border-radius: 4px; }
        """)
        self.progress.hide() # Hidden initially
        main_layout.addWidget(self.progress)

        # --- Status Label ---
        self.status_label = QLabel("Status: Ready. Add image or SVG file to begin.") # Initial text
        self.status_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred) # Allow expanding
        self.status_label.setWordWrap(True) # Wrap long status messages
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft) # Align text
        self.status_label.setObjectName("status_label") # For potential QSS targeting
        main_layout.addWidget(self.status_label) # Add status label to layout

        # --- Version Label ---
        self.version_label = QLabel(f"Version: {APP_VERSION}")
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        self.version_label.setStyleSheet("color: grey; font-size: 8pt; margin-top: 5px;") # Adjusted margin
        main_layout.addWidget(self.version_label)

        # Enable drag and drop for the main window (optional, drop label handles it too)
        self.setAcceptDrops(True)

    def _connect_signals(self):
        """ Connects UI signals to appropriate methods (slots). """
        # Checkbox mutual exclusivity for thumbnails
        self.youtube_checkbox.toggled.connect(lambda checked: self._handle_thumb_toggle(self.youtube_checkbox, checked))
        self.tiktok_checkbox.toggled.connect(lambda checked: self._handle_thumb_toggle(self.tiktok_checkbox, checked))
        self.facebook_checkbox.toggled.connect(lambda checked: self._handle_thumb_toggle(self.facebook_checkbox, checked))

        # Action buttons
        self.convert_btn.clicked.connect(self.convert_image)
        self.update_btn.clicked.connect(self.check_updates)

        # Output format checkboxes (update button state when changed)
        self.png_checkbox.stateChanged.connect(self._update_button_states)
        self.jpeg_checkbox.stateChanged.connect(self._update_button_states)
        self.ico_checkbox.stateChanged.connect(self._update_button_states)
        self.svg_checkbox.stateChanged.connect(self._update_button_states)


    def _handle_thumb_toggle(self, toggled_checkbox, checked):
        """ Ensures only one thumbnail checkbox can be checked at a time. """
        checkboxes = [self.youtube_checkbox, self.tiktok_checkbox, self.facebook_checkbox]
        if checked:
            # If a checkbox is checked, uncheck the others
            for checkbox in checkboxes:
                if checkbox is not toggled_checkbox:
                    checkbox.setChecked(False)
        # No need for an else block, unchecking one doesn't affect others directly

    def set_drop_label_style(self, style_type="default"):
        """ Helper to set the stylesheet for the drop label based on state. """
        if style_type == "default":
            self.drop_label.setStyleSheet("""
                QLabel {
                    border: 2px dashed #aaaaaa; border-radius: 8px; padding: 10px;
                    background: #f8f8f8; color: #555555; font-size: 11pt;
                }
                QLabel:hover { background: #eeeeee; border-color: #888888; }
            """)
        elif style_type == "active_drag":
            self.drop_label.setStyleSheet("""
                QLabel {
                    border: 3px dashed #4CAF50; border-radius: 8px; padding: 10px;
                    background: #E8F5E9; color: #2E7D32; font-size: 12pt; font-weight: bold;
                }
            """)
        elif style_type == "error":
             self.drop_label.setStyleSheet("""
                QLabel {
                    border: 2px dashed #F44336; border-radius: 8px; padding: 10px;
                    background: #FFEBEE; color: #C62828; font-size: 11pt; font-weight: bold;
                }
            """)
        elif style_type == "success":
            self.drop_label.setStyleSheet("""
                 QLabel {
                    border: 2px dashed #4CAF50; border-radius: 8px; padding: 10px;
                    background: #E8F5E9; color: #2E7D32; font-size: 11pt; font-weight: bold;
                }
            """)

    # --- Drag and Drop Event Handlers ---

    def dragEnterEvent(self, event: QDragEnterEvent):
        """ Handles drag enter events for the main window or drop label. """
        mime_data = event.mimeData()
        # Accept if the data contains URLs (for files) or image data
        if mime_data.hasUrls() or mime_data.hasImage():
            # Check if dropped files are of acceptable types
            valid_drop = False
            if mime_data.hasUrls():
                for url in mime_data.urls():
                    if url.isLocalFile():
                        file_path = url.toLocalFile().lower()
                        if file_path.endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.svg')):
                            valid_drop = True
                            break # Found at least one valid file
            elif mime_data.hasImage(): # Accept direct image data (e.g., from screenshot tool)
                valid_drop = True

            if valid_drop:
                event.acceptProposedAction()
                self.set_drop_label_style("active_drag") # Visual feedback
            else:
                event.ignore()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """ Resets the drop label style when the drag leaves the area. """
        self.set_drop_label_style("default")

    def dropEvent(self, event: QDropEvent):
        """ Handles the drop event, processing dropped files or image data. """
        self.set_drop_label_style("default") # Reset style first
        try:
            mime_data = event.mimeData()
            if mime_data.hasUrls():
                # Process the first valid file URL found
                for url in mime_data.urls():
                    if url.isLocalFile():
                        file_path = url.toLocalFile()
                        if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.svg')):
                            self.load_file(file_path)
                            event.acceptProposedAction()
                            return # Process only the first valid file
                # If loop finishes without finding a valid file
                self.show_error("Drop Error: No supported image or SVG files found.")
                event.ignore()

            elif mime_data.hasImage():
                # Handle image data dropped directly (e.g., from screenshot)
                image = QImage(mime_data.imageData())
                # Save to a temporary file to handle consistently
                temp_dir = os.path.join(os.path.expanduser('~'), "AppData", "Local", "Temp") # More standard temp location
                os.makedirs(temp_dir, exist_ok=True)
                temp_path = os.path.join(temp_dir, f'temp_dropped_image_{int(time.time())}.png')
                if image.save(temp_path, "PNG"):
                    self.load_file(temp_path)
                    event.acceptProposedAction()
                else:
                    self.show_error("Drop Error: Could not save dropped image data.")
                    event.ignore()
            else:
                event.ignore()
        except Exception as e:
            logging.exception("Error during drop event:")
            self.show_error(f"Drop Error: {str(e)}")
            event.ignore()

    # --- File Handling Methods ---

    def select_file(self, event=None): # Accept optional event argument
        """ Opens a file dialog to select an image or SVG file. """
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image or SVG File",
            self.last_input_dir, # Start in the last directory
            "Images & SVG (*.png *.jpg *.jpeg *.bmp *.gif *.svg);;SVG Files (*.svg);;Image Files (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)",
            options=QFileDialog.Option.DontUseNativeDialog # Use non-native for consistency/potential stability
        )
        if file_name:
            self.last_input_dir = os.path.dirname(file_name) # Remember directory
            self.settings.setValue("lastImageInputDir", self.last_input_dir)
            self.load_file(file_name)

    def load_file(self, file_path):
        """ Loads either an SVG or a raster image file and updates the preview. """
        logging.info(f"Attempting to load file: {file_path}")
        self.reset_ui() # Clear previous state
        self.current_image_path = file_path
        self.is_svg_input = file_path.lower().endswith('.svg')

        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError("File not found.")

            file_info = f"File: {os.path.basename(file_path)}\n"
            self.current_pixmap = None # Reset pixmap

            if self.is_svg_input:
                # --- Load SVG ---
                svg_renderer = QSvgRenderer(file_path)
                if not svg_renderer.isValid():
                    # This is where the original ValueError happened
                    raise ValueError("Invalid or unsupported SVG file.")

                # Get default size, provide fallback
                size = svg_renderer.defaultSize()
                if not size.isValid() or size.width() <= 0 or size.height() <= 0:
                    logging.warning("SVG has no valid default size, using fallback 200x200 for preview.")
                    size = QSize(200, 200) # Fallback size for rendering preview

                # Render SVG to QImage for preview
                image = QImage(size, QImage.Format.Format_ARGB32)
                image.fill(Qt.GlobalColor.transparent) # Fill with transparency
                painter = QPainter(image)
                svg_renderer.render(painter)
                painter.end() # Important to end painting

                self.current_pixmap = QPixmap.fromImage(image)
                file_info += f"Type: SVG\nDefault Size: {size.width()}x{size.height()}"
                # Enable SVG output only if input is SVG (copy)
                self.svg_checkbox.setEnabled(True)

            else:
                # --- Load Raster Image using Pillow (more robust) and convert to QPixmap ---
                with Image.open(file_path) as img:
                    img.load() # Load image data
                    img_format = img.format
                    width, height = img.size
                    file_info += f"Type: {img_format}\nDimensions: {width}x{height}"

                    # Convert Pillow Image to QImage/QPixmap for display
                    try:
                        # Handle different modes, ensure RGBA for QPixmap transparency
                        if img.mode == 'RGBA':
                            qimage = QImage(img.tobytes("raw", "RGBA"), width, height, QImage.Format.Format_RGBA8888)
                        elif img.mode == 'RGB':
                             qimage = QImage(img.tobytes("raw", "RGB"), width, height, QImage.Format.Format_RGB888)
                        else: # Convert other modes (like P, L) to RGBA
                            img = img.convert('RGBA')
                            qimage = QImage(img.tobytes("raw", "RGBA"), width, height, QImage.Format.Format_RGBA8888)

                        if qimage.isNull():
                             raise ValueError("Failed to convert Pillow image to QImage.")
                        self.current_pixmap = QPixmap.fromImage(qimage)

                    except Exception as conv_e:
                         logging.exception("Error converting Pillow Image to QPixmap:")
                         # Fallback: Try loading directly with QPixmap (less reliable)
                         self.current_pixmap = QPixmap(file_path)
                         if self.current_pixmap.isNull():
                              raise ValueError(f"Invalid or unsupported image format. Conversion failed: {conv_e}")


                # Enable SVG output (embedding) if input is raster
                self.svg_checkbox.setEnabled(True)


            if self.current_pixmap and not self.current_pixmap.isNull():
                 self.display_preview(self.current_pixmap)
                 self.details_label.setText(file_info)
                 self.set_drop_label_style("default") # Reset style after successful load
                 self.drop_label.setText("Loaded: " + os.path.basename(file_path)) # Show loaded filename
                 self._update_button_states() # Enable convert button etc.
            else:
                 raise ValueError("Could not create valid pixmap for preview.")


        except Exception as e:
            # This block catches the ValueError from SVG loading or other errors
            logging.exception(f"Error loading file: {file_path}")
            # Call show_error, which previously crashed due to missing status_label
            self.show_error(f"Error loading file:\n{os.path.basename(file_path)}\n{str(e)}")
            self.reset_ui() # Reset on error

    def display_preview(self, pixmap):
        """ Scales and displays the loaded image/SVG preview in the drop label. """
        if not pixmap or pixmap.isNull():
            logging.warning("Attempted to display null pixmap.")
            # Optionally clear the label or show placeholder text
            self.drop_label.clear()
            self.drop_label.setText("Preview failed")
            return

        try:
            # Scale pixmap to fit the drop label while maintaining aspect ratio
            label_size = self.drop_label.size()
            # Provide some padding inside the border
            preview_width = max(label_size.width() - 20, 10)
            preview_height = max(label_size.height() - 20, 10)

            scaled_pixmap = pixmap.scaled(
                preview_width,
                preview_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.drop_label.setPixmap(scaled_pixmap)
        except Exception as e:
             logging.exception("Error scaling/displaying preview:")
             self.drop_label.clear()
             self.drop_label.setText("Preview Error")

    def reset_ui(self):
        """ Resets the UI elements to their initial state. """
        self.current_image_path = None
        self.current_pixmap = None
        self.is_svg_input = False
        self.drop_label.clear() # Clear pixmap
        self.drop_label.setText("Drag and drop image or SVG here\nor click to select file")
        self.set_drop_label_style("default")
        self.details_label.setText("File Details: (Load a file)")
        self.convert_btn.setEnabled(False)
        self.progress.hide()
        self.progress.setValue(0)
        # Reset checkboxes (optional, maybe keep format selection?)
        # self.png_checkbox.setChecked(False)
        # self.jpeg_checkbox.setChecked(False)
        # self.ico_checkbox.setChecked(False)
        # self.svg_checkbox.setChecked(False)
        # self.youtube_checkbox.setChecked(False)
        # self.tiktok_checkbox.setChecked(False)
        # self.facebook_checkbox.setChecked(False)
        # Disable SVG checkbox until a file is loaded
        self.svg_checkbox.setEnabled(False)


    def _update_button_states(self):
        """ Enables/disables the convert button based on inputs. """
        # Enable convert button if an image is loaded AND at least one format is checked
        image_loaded = bool(self.current_image_path)
        format_selected = (self.png_checkbox.isChecked() or
                           self.jpeg_checkbox.isChecked() or
                           self.ico_checkbox.isChecked() or
                           self.svg_checkbox.isChecked())
        self.convert_btn.setEnabled(image_loaded and format_selected)


    # --- Conversion Logic ---

    def convert_image(self):
        """ Handles the conversion process based on input type and selected options. """
        if not self.current_image_path:
            self.show_error("No image loaded.")
            return

        # Determine selected output formats
        selected_formats = []
        if self.png_checkbox.isChecked(): selected_formats.append("PNG")
        if self.jpeg_checkbox.isChecked(): selected_formats.append("JPEG")
        if self.ico_checkbox.isChecked(): selected_formats.append("ICO")
        if self.svg_checkbox.isChecked(): selected_formats.append("SVG")

        if not selected_formats:
            self.show_error("Please select at least one output format.")
            return

        # Determine target size based on thumbnail checkboxes
        target_size = None
        size_suffix = ""
        if self.youtube_checkbox.isChecked():
            target_size = (1280, 720)
            size_suffix = "_youtube"
        elif self.tiktok_checkbox.isChecked():
            target_size = (1080, 1920)
            size_suffix = "_tiktok"
        elif self.facebook_checkbox.isChecked():
            target_size = (180, 180)
            size_suffix = "_facebook"

        # Get suggested output filename base
        suggested_name_base = os.path.splitext(os.path.basename(self.current_image_path))[0] + size_suffix

        # Show progress bar
        self.progress.setRange(0, len(selected_formats)) # Range based on number of formats
        self.progress.setValue(0)
        self.progress.setFormat("Converting... %p%")
        self.progress.show()
        QApplication.processEvents() # Update UI

        conversion_results = [] # To store paths of created files
        errors = []

        try:
            # --- SVG INPUT LOGIC ---
            if self.is_svg_input:
                logging.info(f"Processing SVG input: {self.current_image_path}")
                renderer = QSvgRenderer(self.current_image_path)
                if not renderer.isValid():
                    raise ValueError("Cannot load or render the input SVG.")

                # Determine render size for raster outputs
                render_size_q = None
                if target_size:
                    render_size_q = QSize(target_size[0], target_size[1])
                else:
                    render_size_q = renderer.defaultSize()
                    if not render_size_q.isValid() or render_size_q.width() <= 0 or render_size_q.height() <= 0:
                        logging.warning("SVG has no default size, rendering raster output at 512x512.")
                        render_size_q = QSize(512, 512) # Fallback render size

                render_width = render_size_q.width()
                render_height = render_size_q.height()

                for i, fmt in enumerate(selected_formats):
                    self.progress.setValue(i)
                    QApplication.processEvents()
                    # Ensure output directory exists
                    if not os.path.isdir(self.last_output_dir):
                         os.makedirs(self.last_output_dir, exist_ok=True)
                    save_path = os.path.join(self.last_output_dir, f"{suggested_name_base}.{fmt.lower()}")
                    logging.info(f"Converting SVG to {fmt} at {render_width}x{render_height}, saving to {save_path}")

                    try:
                        if fmt == "SVG": # Just copy the original SVG
                            import shutil
                            shutil.copy2(self.current_image_path, save_path)
                            conversion_results.append(save_path)
                        elif fmt == "PNG" or fmt == "JPEG":
                            # Render SVG to QImage
                            image = QImage(render_width, render_height, QImage.Format.Format_ARGB32)
                            # Fill background white for JPEG, transparent for PNG
                            bg_color = Qt.GlobalColor.white if fmt == "JPEG" else Qt.GlobalColor.transparent
                            image.fill(bg_color)
                            painter = QPainter(image)
                            # Render preserving aspect ratio within the target QImage size
                            target_rect = image.rect() # Target rectangle is the whole image
                            source_size = renderer.defaultSize() # Get SVG's natural size
                            if not source_size.isValid() or source_size.width() <= 0 or source_size.height() <= 0:
                                source_size = QSize(render_width, render_height) # Use render size if default is invalid

                            # Calculate aspect-ratio-preserving rectangle within target_rect
                            scaled_size = source_size.scaled(target_rect.size(), Qt.AspectRatioMode.KeepAspectRatio)
                            render_rect = QRect(QPoint(0,0), scaled_size)
                            render_rect.moveCenter(target_rect.center()) # Center the render area

                            renderer.render(painter, QRectF(render_rect)) # Render into the calculated rect using QRectF
                            painter.end()

                            # Save QImage
                            quality = 95 if fmt == "JPEG" else -1 # Set JPEG quality
                            if not image.save(save_path, fmt.upper(), quality): # Use upper case format string
                                raise IOError(f"Failed to save QImage as {fmt}.")
                            conversion_results.append(save_path)
                        elif fmt == "ICO":
                            # Render multiple sizes for ICO
                            ico_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
                            pil_images = []
                            source_size = renderer.defaultSize() # Get SVG's natural size once
                            if not source_size.isValid() or source_size.width() <= 0 or source_size.height() <= 0:
                                source_size = QSize(256, 256) # Use a default if SVG has no size

                            for ico_w, ico_h in ico_sizes:
                                logging.debug(f"Rendering ICO size: {ico_w}x{ico_h}")
                                ico_image = QImage(ico_w, ico_h, QImage.Format.Format_ARGB32)
                                ico_image.fill(Qt.GlobalColor.transparent)
                                painter = QPainter(ico_image)

                                # Calculate aspect-ratio-preserving rectangle
                                target_rect = ico_image.rect()
                                scaled_size = source_size.scaled(target_rect.size(), Qt.AspectRatioMode.KeepAspectRatio)
                                # Use QRect, QPoint which are now imported
                                render_rect_int = QRect(QPoint(0,0), scaled_size)
                                render_rect_int.moveCenter(target_rect.center())

                                renderer.render(painter, QRectF(render_rect_int))
                                painter.end()

                                # ***** FIX: Use QBuffer to save QImage to memory for Pillow *****
                                qt_buffer = QBuffer()
                                qt_buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                                # Save QImage to QBuffer as PNG
                                if not ico_image.save(qt_buffer, "PNG"):
                                    qt_buffer.close()
                                    raise IOError(f"Failed to save {ico_w}x{ico_h} QImage to buffer for ICO.")
                                qt_buffer.close()

                                # Create BytesIO for Pillow from QBuffer's data
                                pillow_buffer = BytesIO(qt_buffer.data())
                                pillow_buffer.seek(0) # Reset buffer position
                                pil_img = Image.open(pillow_buffer).convert("RGBA")
                                pil_images.append(pil_img)
                                # ***** End of FIX block *****

                            if not pil_images:
                                raise ValueError("No images generated for ICO file.")

                            # Save using Pillow (requires Pillow >= 9.1.0 for append_images)
                            try:
                                pil_images[0].save(save_path, format='ICO', sizes=[img.size for img in pil_images], append_images=pil_images[1:])
                            except TypeError: # Handle older Pillow versions without append_images
                                 logging.warning("Older Pillow version detected. Saving multi-size ICO might require Pillow >= 9.1.0. Saving only first size.")
                                 pil_images[0].save(save_path, format='ICO', sizes=[(ico_w, ico_h) for ico_w, ico_h in ico_sizes]) # Try saving with sizes arg

                            conversion_results.append(save_path)

                    except Exception as e:
                         logging.exception(f"Error converting SVG to {fmt}:")
                         errors.append(f"Failed to convert to {fmt}: {e}")

            # --- RASTER INPUT LOGIC ---
            else:
                logging.info(f"Processing Raster input: {self.current_image_path}")
                with Image.open(self.current_image_path) as img:
                    # Apply resizing based on thumbnail selection BEFORE saving/embedding
                    current_img_data = img.copy() # Work on a copy
                    if target_size:
                        logging.info(f"Resizing raster image to {target_size}")
                        current_img_data = current_img_data.resize(target_size, Image.Resampling.LANCZOS)
                    else:
                        # Use original size if no thumbnail selected
                        target_size = current_img_data.size # Needed for SVG embedding dimensions

                    # Process selected formats
                    for i, fmt in enumerate(selected_formats):
                        self.progress.setValue(i)
                        QApplication.processEvents()
                        # Ensure output directory exists
                        if not os.path.isdir(self.last_output_dir):
                            os.makedirs(self.last_output_dir, exist_ok=True)
                        save_path = os.path.join(self.last_output_dir, f"{suggested_name_base}.{fmt.lower()}")
                        logging.info(f"Converting Raster to {fmt}, saving to {save_path}")

                        try:
                            if fmt == "PNG":
                                current_img_data.save(save_path, format='PNG')
                                conversion_results.append(save_path)
                            elif fmt == "JPEG":
                                # Ensure image is RGB before saving as JPEG (handles transparency)
                                # Work on a copy to avoid modifying current_img_data used for other formats
                                rgb_img = current_img_data.convert('RGB')
                                rgb_img.save(save_path, format='JPEG', quality=95) # Add quality setting
                                conversion_results.append(save_path)
                            elif fmt == "ICO":
                                # Use standard sizes for ICO from raster
                                ico_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
                                current_img_data.save(save_path, format='ICO', sizes=ico_sizes)
                                conversion_results.append(save_path)
                            elif fmt == "SVG":
                                # Embed raster into SVG
                                logging.info("Embedding raster image into SVG.")
                                # Save potentially resized raster to PNG in memory buffer
                                buffer = BytesIO()
                                current_img_data.save(buffer, format="PNG") # Use the potentially resized image data
                                buffer.seek(0)
                                # Encode image data as Base64
                                encoded_string = base64.b64encode(buffer.read()).decode('utf-8')
                                data_uri = f"data:image/png;base64,{encoded_string}"

                                # Get dimensions for SVG tag (use dimensions of potentially resized image)
                                svg_width, svg_height = current_img_data.size

                                # Create SVG XML content
                                svg_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="{svg_width}px" height="{svg_height}px" viewBox="0 0 {svg_width} {svg_height}" version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
    <title>Embedded Image: {os.path.basename(self.current_image_path)}</title>
    <desc>Created by {APP_NAME} v{APP_VERSION}</desc>
    <image x="0" y="0" width="{svg_width}" height="{svg_height}" xlink:href="{data_uri}"/>
</svg>
"""
                                # Write SVG content to file
                                with open(save_path, 'w', encoding='utf-8') as f_svg:
                                    f_svg.write(svg_content)
                                conversion_results.append(save_path)

                        except Exception as e:
                             logging.exception(f"Error converting Raster to {fmt}:")
                             errors.append(f"Failed to convert to {fmt}: {e}")

            # --- Finalize ---
            self.progress.setValue(len(selected_formats)) # Mark progress as complete
            self.progress.setFormat("Done!")

            if errors:
                error_details = "\n".join(errors)
                self.show_error(f"Conversion completed with errors:\n{error_details}\n\nSuccessful conversions saved to:\n{self.last_output_dir}")
            elif conversion_results:
                 success_message = f"Conversion Complete!\nSaved {len(conversion_results)} file(s) to:\n{self.last_output_dir}\n\nDrag new file or click to select."
                 self.show_success(success_message)
            else:
                # Should not happen if formats were selected, but handle anyway
                 self.show_error("Conversion process finished, but no files were generated.")

            # Reset state after conversion to force user to reload for next operation
            self.current_image_path = None
            self.current_pixmap = None
            self.is_svg_input = False # Reset input type flag
            self._update_button_states() # Disable convert button


        except Exception as e:
            logging.exception("Critical error during conversion process:")
            self.show_error(f"Error converting image: {str(e)}")
            self.progress.hide() # Hide progress bar on critical error
            self._update_button_states() # Update button states


    # --- Update Check ---
    def check_updates(self):
        """ Checks GitHub releases for a newer version using a separate thread. """
        self.update_btn.setEnabled(False)
        self.update_btn.setText("Checking...")
        self.status_label.setText("Status: Checking for updates...")
        QApplication.processEvents()

        # --- Setup and start the worker thread for update check ---
        # Using a simple QThread approach here as well for consistency
        self.update_thread = QThread(self)
        self.update_worker = UpdateCheckWorker(GITHUB_REPO, APP_VERSION) # Pass global APP_VERSION
        self.update_worker.moveToThread(self.update_thread)

        # Connect signals
        self.update_worker.result_ready.connect(self.on_update_check_result)
        self.update_worker.finished.connect(self.update_thread.quit)
        self.update_worker.finished.connect(self.update_worker.deleteLater)
        self.update_thread.finished.connect(self.update_thread.deleteLater)
        self.update_thread.started.connect(self.update_worker.run)

        self.update_thread.start()

    def on_update_check_result(self, status, message, url=None):
        """ Slot to handle the result from the UpdateCheckWorker. """
        current_version_display = APP_VERSION # Use global constant

        self.status_label.setText(f"Status: {status}")
        if "Update Available" in status:
            self.version_label.setText(f'<a href="{url}">New version available: {message}</a>')
            self.version_label.setOpenExternalLinks(True)
            self.version_label.setStyleSheet("color: #2196F3; font-weight: bold; font-size: 9pt;")
            self.show_message("Update Available", f"A newer version ({message}) is available!\nClick the version number at the bottom right to go to the download page.")
        elif "Up to Date" in status:
             self.version_label.setText(f"Version: {current_version_display} (Latest)")
             self.version_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 9pt;")
             self.show_message("Up to Date", "You have the latest version of the application.")
        else: # Error case
             self.version_label.setText(f"Version: {current_version_display} ({status})")
             self.version_label.setStyleSheet("color: #F44336; font-weight: bold; font-size: 9pt;")
             self.show_error(message) # Show error message box

        # Re-enable button
        self.update_btn.setEnabled(True)
        self.update_btn.setText(" Check for Updates")
        # Clear thread references
        self.update_thread = None
        self.update_worker = None


    # --- Utility Methods ---

    def show_error(self, message):
        """ Displays an error message in the status label and a message box. """
        logging.error(f"Displaying error: {message}")
        # Check if status_label exists before using
        if hasattr(self, 'status_label'):
            self.status_label.setText(f"Status: Error - {message.splitlines()[0]}") # Show first line in status
        self.set_drop_label_style("error")
        # Display full error in drop label only if no image is currently loaded
        if not self.current_pixmap or self.current_pixmap.isNull():
            self.drop_label.setText(message)
        QMessageBox.critical(self, "Error", message) # Show critical message box

    def show_success(self, message):
        """ Displays a success message in the status label and a message box. """
        logging.info(f"Displaying success: {message}")
        # Check if status_label exists before using
        if hasattr(self, 'status_label'):
            self.status_label.setText(f"Status: {message.splitlines()[0]}") # Show first line
        self.set_drop_label_style("success")
         # Display full success message in drop label only if no image is currently loaded
        if not self.current_pixmap or self.current_pixmap.isNull():
             self.drop_label.setText(message)
        QMessageBox.information(self, "Success", message) # Show info message box

    def resizeEvent(self, event):
        """ Reloads the preview image when the window is resized. """
        super().resizeEvent(event)
        # Only redisplay if a valid pixmap exists
        if self.current_pixmap and not self.current_pixmap.isNull():
            self.display_preview(self.current_pixmap)

    def closeEvent(self, event):
        """ Saves settings when the application is closed. """
        logging.info("Saving settings on exit.")
        # Check attributes exist before saving (safer)
        if hasattr(self, 'last_input_dir'):
            self.settings.setValue("lastImageInputDir", self.last_input_dir)
        if hasattr(self, 'last_output_dir'): # Check attribute used for saving
            self.settings.setValue("lastImageOutputDir", self.last_output_dir)
        super().closeEvent(event)

# --- Worker Thread for Update Check ---
class UpdateCheckWorker(QObject):
    """ Worker to perform network request for update check off the main thread. """
    finished = pyqtSignal()
    # status, message, optional_url
    result_ready = pyqtSignal(str, str, str)

    def __init__(self, repo, current_version):
        super().__init__()
        self.repo = repo
        self.current_version = current_version

    def run(self):
        """ Performs the update check. """
        status = "Update check failed"
        message = "An unknown error occurred."
        url = None
        try:
            logging.info(f"Update worker: Checking https://api.github.com/repos/{self.repo}/releases/latest")
            response = requests.get(
                f"https://api.github.com/repos/{self.repo}/releases/latest",
                timeout=10
            )
            response.raise_for_status()
            latest_release = response.json()
            latest_version_str = latest_release["tag_name"].lstrip('v')
            # Use passed-in current_version
            current_version_str = self.current_version
            logging.info(f"Update worker: Current={current_version_str}, Latest={latest_version_str}")

            # Use packaging library for robust version comparison
            try:
                from packaging import version
            except ImportError:
                logging.error("Update worker: 'packaging' library not found. Cannot compare versions accurately. Please install it: pip install packaging")
                # Fallback to basic string comparison (less reliable)
                if latest_version_str > current_version_str:
                     status = "Update Available"
                     message = latest_version_str
                     url = latest_release.get("html_url", "#")
                else:
                     status = "Up to Date"
                     message = "Application is up to date."
                # Emit result and finish here for fallback
                self.result_ready.emit(status, message, url)
                self.finished.emit()
                return

            # Proceed with packaging comparison if import succeeded
            if version.parse(latest_version_str) > version.parse(current_version_str):
                status = "Update Available"
                message = latest_version_str # Send back the version number
                url = latest_release.get("html_url", "#")
            else:
                status = "Up to Date"
                message = "Application is up to date."

        except requests.exceptions.RequestException as e:
             logging.error(f"Update worker: Network error: {e}")
             status = "Update check failed (Network)"
             message = f"Could not connect to GitHub. Please check your internet connection.\nError: {e}"
        except Exception as e:
            logging.exception("Update worker: Error during update check:")
            status = "Update check failed (Error)"
            message = f"An error occurred while checking for updates:\n{e}"
        finally:
            # Ensure signals are emitted even if 'packaging' import fails but fallback runs
            if 'status' in locals(): # Check if status was set
                 self.result_ready.emit(status, message, url)
            self.finished.emit()


# --- Application Entry Point ---
if __name__ == "__main__":
    try:
        # --- Application Setup ---
        app = QApplication(sys.argv) # Create the core application object

        # Set organization and application names - used by QSettings
        app.setOrganizationName(ORGANIZATION_NAME)
        app.setApplicationName(APP_NAME)
        app.setApplicationVersion(APP_VERSION)

        # Set a default UI style - "Fusion" often provides a consistent look
        app.setStyle("Fusion")

        # --- Create and Show Main Window ---
        window = ImageConverterApp() # Instantiate the main window class
        window.show() # Make the window visible

        # --- Start Event Loop ---
        sys.exit(app.exec()) # Start the Qt event loop

    except Exception as e:
        # Log fatal errors that prevent app startup
        logging.critical(f"Fatal error starting application: {str(e)}", exc_info=True)
        # Optionally show a simple message box if possible (might fail if QApplication didn't init)
        try:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Fatal Error")
            msg_box.setText(f"A critical error occurred and the application cannot start:\n\n{e}\n\nPlease check logs or report the issue.")
            msg_box.exec()
        except:
            pass # Ignore if even message box fails
        sys.exit(1) # Exit with error code

