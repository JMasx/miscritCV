import pyautogui
import pytesseract
import time
from PIL import Image, ImageFilter

# === CONFIGURATION ===
BUSH_IMAGE = 'woolly.png'
THUMP_IMAGE = 'fprimo.png'
POISON_IMAGE = 'poison.png'
CONTINUE_IMAGE = 'continue.png'
CAPTURE_IMAGE = 'capture.png'
TRAIN_FLASH_IMAGE = 'train_nonflash.png'
TRAIN_NOW_IMAGE = 'train_now.png'
CLOSE_IMAGE = 'close.png'
LEVEL_UP_NOTICE_IMAGE = 'level_up_notice.png'
READY_TO_TRAIN_IMAGE = 'ready_to_train.png'

ARROW_RIGHT_IMAGE = 'arrow_right.png'

DEFAULT_CONFIDENCE = 0.65
BUSH_OFFSET = (0, 0)  

CAPTURE_THRESHOLD = 72          # When to attempt capture
POISON_START_THRESHOLD = 38     # When to switch from Thump to Poison
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
        pyautogui.moveRel(0, 0)  # forces position update
        time.sleep(0.1)
        pyautogui.mouseDown()
        time.sleep(0.1)
        pyautogui.mouseUp()
        return True
    return False

# === OCR UTILITIES ===
def read_capture_percent_once(capture_box, offset_y=8, height=30, width_reduction=100):
    x, y, w, h = capture_box
    capture_x = int(x) + 45
    capture_y = int(y + h + offset_y)
    capture_w = int(w - width_reduction)
    capture_h = int(height)

    screenshot = pyautogui.screenshot(region=(capture_x, capture_y, capture_w, capture_h))

    # Resize to improve OCR accuracy
    screenshot = screenshot.resize((screenshot.width * 3, screenshot.height * 3))

    gray = screenshot.convert('L')
    filtered = gray.filter(ImageFilter.MedianFilter(3))

    config = '--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789'
    text = pytesseract.image_to_string(filtered, config=config)

    text = text.strip().replace('%', '').replace(' ', '')

    if text.isdigit():
        val = int(text)
        if 0 <= val <= 100:
            return val
    return None

def read_capture_percent_confident(capture_box, attempts=5):
    readings = []
    for _ in range(attempts):
        val = read_capture_percent_once(capture_box)
        if val is not None:
            readings.append(val)
        time.sleep(0.15)

    if not readings:
        return None, 0.0

    readings.sort()
    median = readings[len(readings)//2]
    agreement = sum(1 for r in readings if abs(r - median) <= 2)
    confidence = agreement / len(readings)
    return median, confidence

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

# === OCR SANITY CHECK ===
def is_suspicious(new, last, mode):
    if last is None:
        return False
    delta = new - last
    if mode == "poison":
        return delta < 0 or delta > 12
    if mode == "thump":
        return abs(delta) > 50
    return False

# === CAPTURE MODE ===
def should_enter_capture_mode():
    box = wait_for_image(CAPTURE_IMAGE, timeout=3)
    if not box:
        return False

    percent, _ = read_capture_percent_confident(box)
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

    last_percent = None
    attack_mode = "thump"

    while True:
        box = wait_for_image(CAPTURE_IMAGE, timeout=5)
        if not box:
            print("❌ Capture button not found.")
            return

        percent, confidence = read_capture_percent_confident(box)

        if percent is None:
            print("⚠️ OCR failed, retrying...")
            continue

        # Determine mode
        if percent >= POISON_START_THRESHOLD:
            attack_mode = "poison"
        else:
            attack_mode = "thump"

        # Check for suspicious read
        if is_suspicious(percent, last_percent, attack_mode) or confidence < 0.6:
            print(f"⚠️ Uncertain OCR ({percent}%, conf={confidence:.2f}) → rechecking...")
            time.sleep(0.5)
            retry_percent, retry_conf = read_capture_percent_confident(box)
            if retry_percent is not None and retry_conf >= 0.6:
                print(f"✅ Recovered OCR: {retry_percent}%")
                percent = retry_percent
                confidence = retry_conf
            else:
                print("❌ OCR still unreliable → using safe action")
                click_image(THUMP_IMAGE, timeout=4)
                time.sleep(3)
                continue

        print(f"📈 Current capture chance: {percent}% (conf {confidence:.2f})")
        last_percent = percent

        # Attempt capture if threshold met
        if percent >= CAPTURE_THRESHOLD:
            print("🎯 Threshold met! Attempting capture...")

            # Wait until capture button is fully interactable
            retry_attempts = 3
            for _ in range(retry_attempts):
                fresh_box = pyautogui.locateOnScreen(CAPTURE_IMAGE, confidence=0.7)
                if fresh_box:
                    break
                print("⚠️ Waiting for capture button to appear...")
                time.sleep(0.5)
            else:
                print("❌ Capture button never appeared, skipping turn")
                continue

            # Move and click multiple times to ensure registration
            center = pyautogui.center(fresh_box)
            pyautogui.moveTo(center.x, center.y, duration=0.3)
            time.sleep(0.5)  # extra wait for poison animations
            for _ in range(2):
                pyautogui.mouseDown()
                time.sleep(0.1)
                pyautogui.mouseUp()
                time.sleep(0.2)

            print("✅ Capture click executed")
            time.sleep(1)

            handle_post_capture()
            return

        # Attack logic
        if percent < POISON_START_THRESHOLD:
            if not click_image(THUMP_IMAGE, timeout=4):
                print("⚠️ Failed to click Thump")
                return
        else:
            if not use_poison_attack():
                print("⚠️ Failed to click Poison")
                return
        time.sleep(3)

# === POST-CAPTURE / POST-BATTLE ===
def handle_post_capture():
    click_image("okay.png", timeout=5)
    time.sleep(2)
    if click_image("keep.png", timeout=5):
        print("🎉 Capture successful, kept Miscrit!")
        time.sleep(2)
    else:
        print("❌ Capture failed or keep button not found.")

    for _ in range(3):
        if click_image(CONTINUE_IMAGE, timeout=5):
            time.sleep(2)
        else:
            break

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