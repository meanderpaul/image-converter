import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout, 
                            QWidget, QPushButton, QProgressBar, QFileDialog)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap, QImage
from PIL import Image
import requests
import json

class ImageConverter(QMainWindow):
    VERSION = "1.0.1"
    GITHUB_REPO = "zanz-softwares/image-converter"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Converter - Zanz Softwares")
        self.setMinimumSize(400, 500)  # Set minimum size
        self.resize(500, 600)  # Default size
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)  # Add margins
        
        # Create drop area
        self.drop_label = QLabel("Drag and drop image here\nor click to select")
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #2196F3;
                border-radius: 8px;
                padding: 20px;
                background: #E3F2FD;
                color: #1565C0;
                font-size: 14px;
                font-weight: bold;
            }
            QLabel:hover {
                background: #BBDEFB;
                border-color: #1976D2;
            }
        """)
        self.drop_label.setMinimumHeight(300)
        self.drop_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.drop_label.mousePressEvent = self.select_file
        layout.addWidget(self.drop_label)
        
        # Create convert button
        self.convert_btn = QPushButton("Convert to ICO")
        self.convert_btn.setEnabled(False)
        self.convert_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        layout.addWidget(self.convert_btn)
        
        # Create progress bar
        self.progress = QProgressBar()
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #bbb;
                border-radius: 5px;
                text-align: center;
                height: 25px;
                font-size: 12px;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 4px;
            }
        """)
        self.progress.hide()
        layout.addWidget(self.progress)
        
        # Version info and update button
        version_layout = QVBoxLayout()
        self.version_label = QLabel(f"Version: {self.VERSION}")
        self.version_label.setStyleSheet("font-size: 12px; color: #666;")
        self.update_btn = QPushButton("Check for Updates")
        self.update_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px;
                border-radius: 5px;
                font-size: 13px;
                min-height: 35px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        version_layout.addWidget(self.version_label)
        version_layout.addWidget(self.update_btn)
        layout.addLayout(version_layout)
        
        # Set up drag and drop
        self.setAcceptDrops(True)
        
        # Connect signals
        self.convert_btn.clicked.connect(self.convert_image)
        self.update_btn.clicked.connect(self.check_updates)
        
        self.current_image = None

    def select_file(self, event):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)"
        )
        if file_name:
            self.load_image(file_name)

    def dragEnterEvent(self, event):
        if event.mimeData().hasImage() or event.mimeData().hasUrls():
            event.accept()
            self.drop_label.setStyleSheet("""
                QLabel {
                    border: 2px dashed #4CAF50;
                    border-radius: 8px;
                    padding: 20px;
                    background: #E8F5E9;
                    color: #2E7D32;
                    font-size: 14px;
                    font-weight: bold;
                }
            """)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.drop_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #2196F3;
                border-radius: 8px;
                padding: 20px;
                background: #E3F2FD;
                color: #1565C0;
                font-size: 14px;
                font-weight: bold;
            }
            QLabel:hover {
                background: #BBDEFB;
                border-color: #1976D2;
            }
        """)

    def dropEvent(self, event):
        try:
            if event.mimeData().hasUrls():
                url = event.mimeData().urls()[0]
                image_path = url.toLocalFile()
                self.load_image(image_path)
            elif event.mimeData().hasImage():
                image = QImage(event.mimeData().imageData())
                temp_path = os.path.join(os.path.expanduser('~'), 'temp_image.png')
                image.save(temp_path)
                self.load_image(temp_path)
        except Exception as e:
            self.show_error(f"Drop error: {str(e)}")

    def load_image(self, image_path):
        try:
            if not os.path.exists(image_path):
                raise FileNotFoundError("Image file not found")
                
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                raise ValueError("Invalid image format")
                
            # Calculate scaled size while maintaining aspect ratio
            label_size = self.drop_label.size()
            scaled_pixmap = pixmap.scaled(
                label_size.width() - 40,  # Subtract padding
                label_size.height() - 40,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            self.drop_label.setPixmap(scaled_pixmap)
            self.current_image = image_path
            self.convert_btn.setEnabled(True)
            
        except Exception as e:
            self.show_error(f"Error loading image: {str(e)}")

    def convert_image(self):
        if not self.current_image:
            return
            
        try:
            # Get save location from user
            suggested_name = os.path.splitext(os.path.basename(self.current_image))[0] + ".ico"
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Icon File",
                suggested_name,
                "Icon Files (*.ico);;All Files (*)"
            )
            
            if not save_path:  # User cancelled
                return
                
            self.progress.show()
            self.progress.setValue(0)
            
            # Open image
            img = Image.open(self.current_image)
            self.progress.setValue(20)
            
            # Prepare icon sizes
            sizes = [(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)]
            
            # Convert and save with multiple sizes
            img.save(save_path, format='ICO', sizes=sizes)
            self.progress.setValue(100)
            
            success_message = f"Conversion Complete!\nSaved to:\n{save_path}\n\nDrag new image to convert"
            self.show_success(success_message)
            self.convert_btn.setEnabled(False)
            self.current_image = None
            
        except Exception as e:
            self.show_error(f"Error converting image: {str(e)}")
        finally:
            self.progress.hide()

    def check_updates(self):
        try:
            self.update_btn.setEnabled(False)
            self.update_btn.setText("Checking...")
            
            response = requests.get(
                f"https://api.github.com/repos/{self.GITHUB_REPO}/releases/latest",
                timeout=5
            )
            response.raise_for_status()
            latest = response.json()
            latest_version = latest["tag_name"].replace('v', '')
            
            if latest_version > self.VERSION:
                self.version_label.setText(f"New version available: {latest_version}")
                self.version_label.setStyleSheet("color: #2196F3; font-weight: bold;")
            else:
                self.version_label.setText("You have the latest version")
                self.version_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        except Exception as e:
            self.version_label.setText("Failed to check for updates")
            self.version_label.setStyleSheet("color: #F44336; font-weight: bold;")
        finally:
            self.update_btn.setEnabled(True)
            self.update_btn.setText("Check for Updates")

    def show_error(self, message):
        self.drop_label.setText(message)
        self.drop_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #F44336;
                border-radius: 8px;
                padding: 20px;
                background: #FFEBEE;
                color: #C62828;
                font-size: 14px;
                font-weight: bold;
            }
        """)

    def show_success(self, message):
        self.drop_label.setText(message)
        self.drop_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #4CAF50;
                border-radius: 8px;
                padding: 20px;
                background: #E8F5E9;
                color: #2E7D32;
                font-size: 14px;
                font-weight: bold;
            }
        """)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.current_image:
            self.load_image(self.current_image)  # Reload image with new size

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        app.setStyle('Fusion')  # Use Fusion style for better look
        window = ImageConverter()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"Fatal error: {str(e)}")
