import pyautogui
import pytesseract
import time
from PIL import Image, ImageFilter

# === CONFIGURATION ===
BUSH_IMAGE = 'aquarion.png'
THUMP_IMAGE = 'fprimo.png'
CONTINUE_IMAGE = 'continue.png'
CAPTURE_IMAGE = 'capture.png'
TRAIN_FLASH_IMAGE = 'train_nonflash.png'
TRAIN_NOW_IMAGE = 'train_now.png'
CLOSE_IMAGE = 'close.png'
LEVEL_UP_NOTICE_IMAGE = 'level_up_notice.png'
READY_TO_TRAIN_IMAGE = 'ready_to_train.png'

ARROW_RIGHT_IMAGE = 'arrow_right.png'
POISON_IMAGE = 'poison.png'

DEFAULT_CONFIDENCE = 0.65
BUSH_OFFSET = (0, 0)  

CAPTURE_THRESHOLD = 91          # When to attempt capture
POISON_START_THRESHOLD = 70     # When to switch from Thump to Poison
RARE_INITIAL_THRESHOLDS = list(range(0, 8))  # Rare chance to trigger capture mode

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Region for OCRing the Miscrit's name
CAPTURE_NAME_REGION = (1700, 60, 100, 35)

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
# ✅ Capture percent reader restored to your original high accuracy pipeline
def read_capture_percent(capture_box, offset_y=8, height=30, width_reduction=100):
    x, y, w, h = capture_box
    capture_x = int(x) + 45
    capture_y = int(y + h + offset_y)
    capture_w = int(w - width_reduction)
    capture_h = int(height)

    time.sleep(0.8)
    screenshot = pyautogui.screenshot(region=(capture_x, capture_y, capture_w, capture_h))
    screenshot.save('debug_capture_percent.png')

    gray = screenshot.convert('L')
    filtered = gray.filter(ImageFilter.MedianFilter(3))
    sharpened = filtered.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
    enhanced = sharpened.point(lambda px: 255 if px > 120 else 0)

    config = '--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789%'
    text = pytesseract.image_to_string(enhanced, config=config)
    text = text.strip().replace('%', '').replace(' ', '')

    if text.isdigit():
        capture_percent = int(text)
        if 0 <= capture_percent <= 100:
            return capture_percent
    return None

def read_miscrit_name(region):
    screenshot = pyautogui.screenshot(region=region)
    screenshot.save('debug_miscrit_name.png')

    gray = screenshot.convert('L')
    enhanced = gray.point(lambda px: 255 if px > 120 else 0)

    config = '--psm 6 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    text = pytesseract.image_to_string(enhanced, config=config)
    return text.strip()

# === LOGGING ===
def log_miscrit_encounter(miscrit_name, capture_percent):
    utc = time.gmtime()
    mountain = time.localtime(time.mktime(utc) - 7*3600)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", mountain)
    with open('captureFull_log.txt', 'a') as log_file:
        log_file.write(f"{timestamp} - Miscrit: {miscrit_name}, Capture Chance: {capture_percent}%\n")

# === ATTACK UTILITIES ===
def use_poison_attack():
    click_image(ARROW_RIGHT_IMAGE, timeout=3)
    time.sleep(0.5)
    click_image(ARROW_RIGHT_IMAGE, timeout=3)
    time.sleep(0.5)
    return click_image(POISON_IMAGE, timeout=3)

# === CAPTURE MODE ===
def should_enter_capture_mode():
    box = wait_for_image(CAPTURE_IMAGE, timeout=3)
    if not box:
        return False

    percent = read_capture_percent(box)
    if percent is not None:
        miscrit_name = read_miscrit_name(CAPTURE_NAME_REGION)
        if miscrit_name:
            log_miscrit_encounter(miscrit_name, percent)
            print(f"👁️ Seen Miscrit: {miscrit_name} ({percent}%)")
        if percent in RARE_INITIAL_THRESHOLDS:
            print("🎯 Rare threshold met! Entering capture mode.")
            return True
    return False

def attempt_capture_when_ready():
    print("🎯 Capture mode active")

    while True:
        # Wait for capture button at start of turn
        box = wait_for_image(CAPTURE_IMAGE, timeout=5)
        if not box:
            print("❌ Capture button not found.")
            return

        percent = read_capture_percent(box)
        if percent is None:
            print("⚠️ Couldn't read capture %, defaulting to 0")
            percent = 0

        print(f"📈 Current capture chance: {percent}%")

        # Attempt capture if threshold reached
        if percent >= CAPTURE_THRESHOLD:
            print("🎯 Threshold met! Attempting capture...")
            center = pyautogui.center(box)
            pyautogui.moveTo(center.x, center.y, duration=0.7)
            time.sleep(0.8)
            pyautogui.mouseDown()
            time.sleep(0.15)
            pyautogui.mouseUp()
            handle_post_capture()
            return

        # Decide attack type
        if percent < POISON_START_THRESHOLD:
            if not click_image(THUMP_IMAGE, timeout=4):
                print("⚠️ Failed to click Thump")
                return
        else:
            if not use_poison_attack():
                print("⚠️ Failed to click Poison")
                return

        time.sleep(3)

# === POST-CAPTURE ===
def handle_post_capture():
    click_image("okay.png", timeout=8)
    time.sleep(3)
    click_image(CONTINUE_IMAGE, timeout=8)
    time.sleep(2)
    click_image(CONTINUE_IMAGE, timeout=8)
    time.sleep(3)
    click_image("keep.png", timeout=8)

# === TRAINING MODE ===
def handle_training_mode():
    if click_image(TRAIN_FLASH_IMAGE, timeout=5, confidence=0.5):
        click_image(TRAIN_NOW_IMAGE, timeout=5, confidence=0.45)
        click_image(CONTINUE_IMAGE, timeout=3, confidence=0.5)
        time.sleep(2)
        click_image(CONTINUE_IMAGE, timeout=3, confidence=0.5)
        click_image(CLOSE_IMAGE, timeout=5)

# === FIGHT SEQUENCE ===
def fight_sequence():
    ready_to_train_detected = False

    if should_enter_capture_mode():
        attempt_capture_when_ready()
        return

    if wait_for_image(READY_TO_TRAIN_IMAGE, timeout=0.5):
        ready_to_train_detected = True

    while True:
        if click_image(THUMP_IMAGE, timeout=4):
            time.sleep(3)
        else:
            if click_image(CONTINUE_IMAGE, timeout=3):
                time.sleep(3)
                if wait_for_image(LEVEL_UP_NOTICE_IMAGE, timeout=2) or ready_to_train_detected:
                    handle_training_mode()
                return
            time.sleep(2)

# === MAIN LOOP ===
def main():
    print("🎮 Starting Miscrits auto-farm logger...")
    while True:
        if click_image(BUSH_IMAGE, timeout=10, offset=BUSH_OFFSET, confidence=0.8):
            time.sleep(3)
            if wait_for_image(THUMP_IMAGE, timeout=7):
                fight_sequence()
            else:
                time.sleep(30)
        else:
            time.sleep(5)

if __name__ == "__main__":
    main()