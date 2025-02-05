import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout, 
                            QWidget, QPushButton, QProgressBar)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap
from PIL import Image
import requests
import json

class ImageConverter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Converter - Zanz Softwares")
        self.setFixedSize(400, 500)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create drop area
        self.drop_label = QLabel("Drag and drop image here")
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 5px;
                padding: 20px;
                background: #f0f0f0;
            }
        """)
        self.drop_label.setMinimumHeight(200)
        layout.addWidget(self.drop_label)
        
        # Create convert button
        self.convert_btn = QPushButton("Convert to ICO")
        self.convert_btn.setEnabled(False)
        layout.addWidget(self.convert_btn)
        
        # Create progress bar
        self.progress = QProgressBar()
        self.progress.hide()
        layout.addWidget(self.progress)
        
        # Version info and update button
        self.version_label = QLabel("Version: 1.0.0")
        self.update_btn = QPushButton("Check for Updates")
        layout.addWidget(self.version_label)
        layout.addWidget(self.update_btn)
        
        # Set up drag and drop
        self.setAcceptDrops(True)
        
        # Connect signals
        self.convert_btn.clicked.connect(self.convert_image)
        self.update_btn.clicked.connect(self.check_updates)
        
        self.current_image = None

    def dragEnterEvent(self, event):
        if event.mimeData().hasImage() or event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            url = event.mimeData().urls()[0]
            image_path = url.toLocalFile()
            self.load_image(image_path)
        elif event.mimeData().hasImage():
            image = QImage(event.mimeData().imageData())
            self.load_image(image)

    def load_image(self, image_path):
        try:
            pixmap = QPixmap(image_path)
            scaled_pixmap = pixmap.scaled(QSize(180, 180), 
                                        Qt.AspectRatioMode.KeepAspectRatio)
            self.drop_label.setPixmap(scaled_pixmap)
            self.current_image = image_path
            self.convert_btn.setEnabled(True)
        except Exception as e:
            self.drop_label.setText(f"Error loading image: {str(e)}")

    def convert_image(self):
        if not self.current_image:
            return
            
        try:
            self.progress.show()
            self.progress.setValue(0)
            
            # Open and convert image
            img = Image.open(self.current_image)
            
            # Get save path
            save_path = os.path.splitext(self.current_image)[0] + ".ico"
            
            # Convert and save
            img.save(save_path, format='ICO')
            
            self.progress.setValue(100)
            self.drop_label.setText("Conversion Complete!\nDrag new image to convert")
            self.convert_btn.setEnabled(False)
            self.current_image = None
            
        except Exception as e:
            self.drop_label.setText(f"Error converting image: {str(e)}")
        finally:
            self.progress.hide()

    def check_updates(self):
        try:
            # Get latest release info from GitHub
            response = requests.get(
                "https://api.github.com/repos/yourusername/image-converter/releases/latest"
            )
            latest = json.loads(response.text)
            latest_version = latest["tag_name"]
            
            if latest_version > "1.0.0":  # Compare with current version
                self.version_label.setText(f"New version available: {latest_version}")
                # Here you can add auto-update functionality
            else:
                self.version_label.setText("You have the latest version")
        except:
            self.version_label.setText("Failed to check for updates")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageConverter()
    window.show()
    sys.exit(app.exec()) 