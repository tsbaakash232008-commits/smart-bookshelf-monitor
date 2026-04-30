# Smart Bookshelf Monitor 📚👁️

An automated, computer-vision-based inventory tracking system for physical bookshelves. 

This project uses an Arduino-based sensor (like an ultrasonic distance sensor) to detect when a person is interacting with a shelf. It triggers a camera to capture images before and after the interaction, utilizing OpenCV to analyze pixel differences and determine exactly which books were added or removed without the need for RFID tags or barcodes.

## ⚙️ How It Works (Modules)

The project is divided into three distinct modules to separate hardware integration from the core computer vision logic:

### 1. Detection Model (`MODEL_2_PC_IMAGES`)
The core computer vision engine. It loads a `before.png` and `after.png` image, crops the Region of Interest (the shelf), and divides the shelf width into 11 predefined slots. By calculating the absolute difference between the images, it identifies specific slots where activity occurred and maps them to a dictionary of known book titles (e.g., "Intro to Astrophysics", "Quantum Mechanics").

### 2. Capture Model (`MODEL_3_CAPTURE_ONLY`)
A manual utility for system calibration and testing. It allows a developer to capture reference `before` and `after` frames using a standard webcam by simply pressing the SPACE bar. This is useful for testing the environment lighting and camera angles without needing the Arduino hardware.

### 3. Integrated Model (`MODEL_1_FULL_SYSTEM`)
The end-to-end production pipeline. It establishes a serial connection with an Arduino microcontroller. When the Arduino detects a physical trigger (e.g., a hand reaching for a book), it sends a signal over Serial to capture the first frame. A subsequent trigger captures the second frame, and the system immediately calculates if a shelf change occurred.

## 🛠️ Tech Stack

* **Language:** Python 3.x
* **Computer Vision:** OpenCV (`cv2`)
* **Matrix Operations:** NumPy
* **Hardware Communication:** PySerial (Arduino integration)

## 📁 Folder Structure

```text
smart-bookshelf-monitor/
├── MODEL_1_FULL_SYSTEM/
│   └── model1_full_system.py        # End-to-end hardware + CV pipeline
├── MODEL_2_PC_IMAGES/
│   └── model2_detection_pc_images.py  # Core detection & slot mapping logic
├── MODEL_3_CAPTURE_ONLY/
│   └── model3_capture_only.py       # Manual capture utility
├── before.png                       # Sample pre-activity reference image
├── after.png                        # Sample post-activity reference image
├── README.md
└── .gitignore
