import pyautogui
import pytesseract
import time
from PIL import Image

# === CONFIGURATION ===
BUSH_IMAGE = 'bush.png'
THUMP_IMAGE = 'mightybash.png'
CONTINUE_IMAGE = 'continue.png'
CAPTURE_IMAGE = 'capture.png'
TRAIN_FLASH_IMAGE = 'train_flash.png'
TRAIN_NOW_IMAGE = 'train_now.png'
CLOSE_IMAGE = 'close.png'
DEFAULT_CONFIDENCE = 0.65
BUSH_OFFSET = (30, 30)
CAPTURE_THRESHOLD = 86
RARE_INITIAL_THRESHOLDS = [27] + list(range(0, 21))  # 27% or ≤ 20%
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

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

def read_capture_percent(capture_box, offset_y=8, height=30, width_reduction=25):
    x, y, w, h = capture_box
    capture_x = int(x)
    capture_y = int(y + h + offset_y)
    capture_w = int(w - width_reduction)
    capture_h = int(height)

    time.sleep(0.8)
    screenshot = pyautogui.screenshot(region=(capture_x, capture_y, capture_w, capture_h))
    screenshot.save('debug_capture_percent.png')

    gray = screenshot.convert('L').point(lambda px: 0 if px < 140 else 255)
    text = pytesseract.image_to_string(gray, config='--psm 7 -c tessedit_char_whitelist=0123456789%')

    try:
        return int(text.strip().replace('%', '').replace(' ', ''))
    except ValueError:
        return None

# === CAPTURE MODE ===

def should_enter_capture_mode():
    box = wait_for_image(CAPTURE_IMAGE, timeout=3)
    if not box:
        return False
    percent = read_capture_percent(box)
    if percent is not None:
        print(f"🔎 Initial capture chance: {percent}%")
        return percent in RARE_INITIAL_THRESHOLDS
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

    if click_image(TRAIN_FLASH_IMAGE, timeout=5):
        print("✅ Clicked flashing Train button.")
        time.sleep(2)

        if click_image(TRAIN_NOW_IMAGE, timeout=5):
            print("💪 Clicked Train Now.")
            time.sleep(2)

            if click_image(CONTINUE_IMAGE, timeout=5):
                print("➡️ Clicked Continue 1.")
                time.sleep(2)
                if click_image(CONTINUE_IMAGE, timeout=5):
                    print("➡️ Clicked Continue 2.")

            if click_image(CLOSE_IMAGE, timeout=5):
                print("❌ Closed training window.")
        else:
            print("⚠️ Train Now button not found.")
    else:
        print("🚫 Train button not flashing.")

# === MAIN FLOW ===

def fight_sequence():
    print("💥 Battle started! Attacking with Thump...")

    if should_enter_capture_mode():
        attempt_capture_when_ready()
        return

    while True:
        if click_image(THUMP_IMAGE, timeout=4):
            print("➡️ Clicked Thump")
            time.sleep(3)
        else:
            print("⚠️ Thump missing, checking for Continue or Training...")
            time.sleep(2)

            if click_image(CONTINUE_IMAGE, timeout=3):
                print("🏆 Clicked Continue — fight over.")
                time.sleep(3)
                if wait_for_image(TRAIN_FLASH_IMAGE, timeout=4):
                    handle_training_mode()
                return

def main():
    print("🎮 Starting Miscrits auto-farm bot...")
    while True:
        if wait_for_image(TRAIN_FLASH_IMAGE, timeout=4):
            handle_training_mode()

        print("🔍 Looking for bush...")
        if click_image(BUSH_IMAGE, timeout=10, offset=BUSH_OFFSET):
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
