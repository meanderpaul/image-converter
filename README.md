Here's a simplified README focused on usage and future development plans:

```markdown:README.md
# Image Converter

A desktop application for converting images between different formats. Currently supports conversion to ICO format, with plans to expand to other formats.

## Current Features

- Convert images to ICO format
- Drag and drop interface
- Supports input formats: PNG, JPG, JPEG, BMP, GIF
- Creates ICO files with multiple sizes (256x256, 128x128, 64x64, 32x32, 16x16)
- Automatic update checking

## Installation

1. Install Python 3.6 or higher
2. Install required packages:
```
pip install PyQt6 Pillow requests
```

## Usage

1. Run the application:
```
python main.py
```

2. Load an image by either:
   - Dragging and dropping it onto the application window
   - Clicking the window to open file selection dialog

3. Click "Convert to ICO" button
4. Choose where to save your ICO file
5. Your icon file will be created with all size variants

## Roadmap

### Phase 1 - Additional Format Support
- [ ] PNG conversion
- [ ] JPEG conversion
- [ ] WebP conversion
- [ ] SVG conversion
- [ ] PDF to image conversion

### Phase 2 - Enhanced Features
- [ ] Batch conversion support
- [ ] Custom size options for ICO files
- [ ] Image compression options
- [ ] Preview of converted images
- [ ] Save conversion preferences

### Phase 3 - Advanced Features
- [ ] Image editing capabilities (resize, crop, rotate)
- [ ] Color adjustments
- [ ] Format-specific optimization options
- [ ] Command-line interface
- [ ] Conversion profiles

## Contributing

Contributions are welcome! If you'd like to add support for a new format or enhance existing features, please:

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Support

For issues and feature requests, please create an issue in the repository.
```

This README focuses on:
1. Essential features and usage instructions
2. Clear roadmap for future development
3. How others can contribute to expanding the converter's capabilities

The roadmap is structured to progressively add more functionality, starting with basic format conversions and moving toward more advanced features.
