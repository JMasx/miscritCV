import pyautogui
import pytesseract
import time
from PIL import Image, ImageFilter

# === CONFIGURATION ===
BUSH_IMAGE = 'f_croak.png'
THUMP_IMAGE = 'thump2.png'
CONTINUE_IMAGE = 'continue.png'
CAPTURE_IMAGE = 'capture.png'
TRAIN_FLASH_IMAGE = 'train_nonflash.png'
TRAIN_NOW_IMAGE = 'train_now.png'
CLOSE_IMAGE = 'close.png'
LEVEL_UP_NOTICE_IMAGE = 'level_up_notice.png'     # Added for level up screen detection
READY_TO_TRAIN_IMAGE = 'ready_to_train.png'       # Added for "READY TO TRAIN" bar during fight
DEFAULT_CONFIDENCE = 0.65
BUSH_OFFSET = (0, 0)  # (30, 30)
CAPTURE_THRESHOLD = 79
RARE_INITIAL_THRESHOLDS = [27, 28] + list(range(0, 26))  # Exactly 27% or ≤ 20%
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# === CONFIGURATION FOR MISCRIT NAME OCR ===
CAPTURE_NAME_REGION = (1700, 60, 100, 35)  # Region to capture the Miscrit's name (top-right section)

# === IMAGE UTILITIES ===

def wait_for_image(image_path, timeout=15, confidence=DEFAULT_CONFIDENCE, check_interval=0.5):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            location = pyautogui.locateOnScreen(image_path, confidence=confidence)
            if location:
                return location
        except pyautogui.ImageNotFoundException:
            pass
        time.sleep(check_interval)
    return None

def click_image(image_path, timeout=5, confidence=DEFAULT_CONFIDENCE, offset=(0, 0)):
    location = wait_for_image(image_path, timeout=timeout, confidence=confidence)
    if location:
        center = pyautogui.center(location)
        corrected_x = center.x + offset[0]
        corrected_y = center.y + offset[1]
        pyautogui.moveTo(corrected_x, corrected_y, duration=0.7)
        time.sleep(1.0)
        pyautogui.mouseDown()
        time.sleep(0.15)
        pyautogui.mouseUp()
        return True
    return False

# === OCR UTILITIES ===

def read_capture_percent(capture_box, offset_y=8, height=30, width_reduction=100):
    x, y, w, h = capture_box
    capture_x = int(x) + 45
    capture_y = int(y + h + offset_y)
    capture_w = int(w - width_reduction)
    capture_h = int(height)

    time.sleep(0.8)
    screenshot = pyautogui.screenshot(region=(capture_x, capture_y, capture_w, capture_h))
    screenshot.save('debug_capture_percent.png')  # Debugging step: save the image

    # Preprocessing: Apply adaptive thresholding or sharpen the image to improve OCR accuracy
    gray = screenshot.convert('L')  # Convert to grayscale

    # Apply a median filter to reduce noise, and sharpen the image to make text clearer
    filtered = gray.filter(ImageFilter.MedianFilter(3))
    sharpened = filtered.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))

    # Adaptive thresholding (optional but can improve OCR in some cases)
    enhanced = sharpened.point(lambda px: 255 if px > 120 else 0)

    # Use pytesseract to extract the text
    config = '--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789%'  # Tesseract config to handle percentages
    text = pytesseract.image_to_string(enhanced, config=config)

    # Debugging: Show the OCR result for inspection
    print(f"OCR Result: {text.strip()}")  # Print the result

    # Clean up OCR result
    text = text.strip().replace('%', '').replace(' ', '')

    # Check if the value is reasonable (between 0 and 100)
    if text.isdigit():
        capture_percent = int(text)
        if 0 <= capture_percent <= 100:
            return capture_percent
        else:
            print(f"⚠️ Invalid capture percentage detected: {capture_percent}%")
            return None
    else:
        print(f"⚠️ Failed to parse capture percent: {text}")
        return None

def read_miscrit_name(region):
    # Capture the image of the top-right section where the Miscrit's name is located
    screenshot = pyautogui.screenshot(region=region)
    screenshot.save('debug_miscrit_name.png')  # Save for debugging

    # Convert to grayscale
    gray = screenshot.convert('L')

    # Apply thresholding to improve OCR
    enhanced = gray.point(lambda px: 255 if px > 120 else 0)

    # Use pytesseract to extract the text (name of the Miscrit)
    config = '--psm 6 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    text = pytesseract.image_to_string(enhanced, config=config)

    # Debugging: Print the OCR result
    # print(f"OCR Result (Miscrit Name): {text.strip()}")  # Not displaying the name in the console

    return text.strip()

# === LOGGING FUNCTION ===

def log_capture_event(miscrit_name, capture_percent):
    utc = time.gmtime()  # Get the current UTC time
    mountain = time.localtime(time.mktime(utc) - 7*3600)
        
    # Open the log file in append mode
    with open('capture_log.txt', 'a') as log_file:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", mountain)  # Format the time in local time
        log_file.write(f"{timestamp} - Miscrit: {miscrit_name}, Capture Chance: {capture_percent}%\n")

# === CAPTURE MODE ===

def should_enter_capture_mode():
    box = wait_for_image(CAPTURE_IMAGE, timeout=3)
    if not box:
        return False
    percent = read_capture_percent(box)
    if percent is not None:
        print(f"🔎 Initial capture chance: {percent}%")
        if percent in RARE_INITIAL_THRESHOLDS:
            miscrit_name = read_miscrit_name(CAPTURE_NAME_REGION)
            if miscrit_name:
                log_capture_event(miscrit_name, percent)  # Log the capture event to the file
                # print(f"🎯 Capture mode triggered by Miscrit: {miscrit_name}")  # No longer printing to console
            else:
                print("⚠️ Failed to read Miscrit name.")
            return True
    print("⚠️ Failed to read initial capture percentage.")
    return False

def attempt_capture_when_ready():
    print("🎯 In capture mode. Weakening Miscrit...")
    while True:
        box = wait_for_image(CAPTURE_IMAGE, timeout=3, confidence=DEFAULT_CONFIDENCE)
        if not box:
            print("❌ Capture button not found, aborting capture mode.")
            return
        percent = read_capture_percent(box)
        if percent is not None:
            print(f"📈 Current capture chance: {percent}%")
            if percent >= CAPTURE_THRESHOLD:
                print("🎯 Threshold met! Attempting capture...")
                center = pyautogui.center(box)
                pyautogui.moveTo(center.x, center.y, duration=0.7)
                time.sleep(0.8)
                pyautogui.mouseDown()
                time.sleep(0.15)
                pyautogui.mouseUp()
                print("✅ Attempted capture!")
                handle_post_capture()
                return
            else:
                print("❌ Capture chance below threshold, attacking again...")
        else:
            print("❓ Couldn't read capture %, attacking anyway...")

        if not click_image(THUMP_IMAGE, timeout=4):
            print("⚠️ Failed to click Thump, aborting capture mode.")
            return
        time.sleep(3)

# === POST-CAPTURE ===

def handle_post_capture():
    print("📦 Handling capture aftermath...")
    if click_image("okay.png", timeout=8):
        print("✅ Clicked Okay after capture.")
    else:
        print("❌ Failed to detect 'Okay'.")

    time.sleep(3)
    if click_image(CONTINUE_IMAGE, timeout=8):
        print("➡️ Clicked Continue 1.")
    time.sleep(2)
    if click_image(CONTINUE_IMAGE, timeout=8):
        print("➡️ Clicked Continue 2.")

    time.sleep(3)
    if click_image("keep.png", timeout=8):
        print("🛡️ Clicked Keep.")

# === TRAINING MODE ===

def handle_training_mode():
    print("📚 Entering training mode...")

    if click_image(TRAIN_FLASH_IMAGE, timeout=5, confidence=0.5):
        print("✅ Clicked flashing Train button.")
        time.sleep(2)

        if click_image(TRAIN_NOW_IMAGE, timeout=5, confidence=0.45):
            print("💪 Clicked Train Now.")
            time.sleep(2)

            if click_image(CONTINUE_IMAGE, timeout=3, confidence=0.5):
                print("➡️ Clicked Continue 1.")
                time.sleep(2)
                if click_image(CONTINUE_IMAGE, timeout=3, confidence=0.5):
                    print("➡️ Clicked Continue 2.")

            if click_image(CLOSE_IMAGE, timeout=5):
                print("❌ Closed training window.")
        else:
            print("⚠️ Train Now button not found.")
    else:
        print("🚫 Train button not flashing.")

# === FIGHT SEQUENCE ===

def fight_sequence():
    print("💥 Battle started! Attacking with Thump...")
    ready_to_train_detected = False

    # Check if we should enter capture mode first
    if should_enter_capture_mode():
        attempt_capture_when_ready()
        return

    # Check for "Ready to Train" at the start of the fight
    ready_to_train_found = wait_for_image(READY_TO_TRAIN_IMAGE, timeout=0.5)
    if ready_to_train_found:
        print("📈 'READY TO TRAIN' detected at the start of the fight!")
        ready_to_train_detected = True

    while True:
        # Continue attacking with Thump
        if click_image(THUMP_IMAGE, timeout=4):
            print("➡️ Clicked Thump")
            time.sleep(3)
        else:
            print("⚠️ Thump missing, checking for Continue...")

            # Check if opponent is dead, and click Continue
            if click_image(CONTINUE_IMAGE, timeout=3):
                print("🏆 Clicked Continue — fight over.")
                time.sleep(3)

                # Check if Ready to Train was detected or Level Up notice after fight
                if wait_for_image(LEVEL_UP_NOTICE_IMAGE, timeout=2) or ready_to_train_detected:
                    print("📈 Level up detected or 'Ready to Train' flag set! Entering training mode...")
                    handle_training_mode()
                return

            time.sleep(2)

# === MAIN LOOP ===

def main():
    print("🎮 Starting Miscrits auto-farm bot...")
    while True:
        print("🔍 Looking for bush...")
        if click_image(BUSH_IMAGE, timeout=10, offset=BUSH_OFFSET, confidence=0.8):
            print("🌿 Clicked bush.")
            time.sleep(3)

            if wait_for_image(THUMP_IMAGE, timeout=5):
                fight_sequence()
            else:
                print("💰 No fight. Waiting 30 seconds cooldown.")
                time.sleep(30)
        else:
            print("❌ Bush not found. Retrying in 5 seconds.")
            time.sleep(5)

if __name__ == "__main__":
    main()
