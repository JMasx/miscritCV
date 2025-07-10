import pyautogui
import pytesseract
import time
from PIL import Image

# === CONFIGURATION ===
BUSH_IMAGE = 'bush.png'
THUMP_IMAGE = 'thump2.png'
CONTINUE_IMAGE = 'continue.png'
CAPTURE_IMAGE = 'capture.png'
OKAY_IMAGE = 'okayCapture.png'
KEEP_IMAGE = 'keep.png'
DEFAULT_CONFIDENCE = 0.65
BUSH_OFFSET = (30, 30)
CAPTURE_THRESHOLD = 83  # Only capture if >= 86%
RARE_INITIAL_THRESHOLDS = [27, 28] + list(range(0, 21))  # Exactly 27% or ≤ 20%
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

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

def read_capture_percent(capture_box, offset_y=8, height=30, width_reduction=25):
    """
    Capture region slightly below the capture button,
    with reduced width and a small delay before screenshot.
    """
    x, y, w, h = capture_box
    capture_x = int(x)
    capture_y = int(y + h + offset_y)
    capture_w = int(w - width_reduction)  # reduce width from right side
    capture_h = int(height)

    time.sleep(0.8)  # wait for screen to stabilize

    percent_region = (capture_x, capture_y, capture_w, capture_h)
    screenshot = pyautogui.screenshot(region=percent_region)
    screenshot.save('debug_capture_percent.png')  # for debugging

    gray = screenshot.convert('L').point(lambda px: 0 if px < 140 else 255)
    text = pytesseract.image_to_string(gray, config='--psm 7 -c tessedit_char_whitelist=0123456789%')

    try:
        return int(text.strip().replace('%', '').replace(' ', ''))
    except ValueError:
        return None

def should_enter_capture_mode():
    """
    Reads the initial capture percentage and decides if it's a rare Miscrit.
    """
    box = wait_for_image(CAPTURE_IMAGE, timeout=3)
    if not box:
        return False

    percent = read_capture_percent(box)
    if percent is not None:
        print(f"🔎 Initial capture chance: {percent}%")
        return percent in RARE_INITIAL_THRESHOLDS
    else:
        print("⚠️ Failed to read initial capture percentage.")
        return False

def attempt_capture_when_ready():
    """
    Enter capture mode: attack repeatedly and read capture % each time.
    Attempt capture ONLY when capture chance >= CAPTURE_THRESHOLD (86%).
    """
    print("🎯 In capture mode. Weakening Miscrit...")

    while True:
        # Locate capture button box fresh every loop to get current position
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
                time.sleep(3)
                return
            else:
                print("❌ Capture chance below threshold, attacking again...")
        else:
            print("❓ Couldn't read capture %, attacking anyway...")

        # Attack with Thump
        if not click_image(THUMP_IMAGE, timeout=4):
            print("⚠️ Failed to click Thump, aborting capture mode.")
            return

        time.sleep(3)  # wait between attacks

def click_okay(timeout=10):
    print("⏳ Waiting for 'Okay' button after capture...")
    if click_image(OKAY_IMAGE, timeout=timeout, offset=(10, 0)):
        print("✅ Clicked 'Okay'")
        time.sleep(2)
        return True
    print("⚠️ 'Okay' button not found.")
    return False

def click_keep(timeout=10):
    print("⏳ Waiting for 'Keep' button to keep the captured Miscrit...")
    if click_image(KEEP_IMAGE, timeout=timeout):
        print("✅ Clicked 'Keep'")
        time.sleep(2)
        return True
    print("⚠️ 'Keep' button not found.")
    return False

def fight_sequence():
    print("💥 Battle started! Attacking with Thump...")

    if should_enter_capture_mode():
        attempt_capture_when_ready()

        # After capture attempt, handle the follow-up screens
        if click_okay():
            if click_image(CONTINUE_IMAGE, timeout=7):
                print("✅ Clicked 'Continue' after 'Okay' screen")
                time.sleep(3)
                if click_keep():
                    print("✅ Miscrit kept successfully!")
                else:
                    print("⚠️ Failed to click 'Keep' button.")
            else:
                print("⚠️ Failed to click 'Continue' after 'Okay' screen.")
        else:
            print("⚠️ Failed to click 'Okay' after capture.")
        return

    while True:
        if click_image(THUMP_IMAGE, timeout=6):
            print("➡️ Clicked Thump")
            time.sleep(3)
        else:
            print("⚠️ Thump button missing, checking for Continue...")
            time.sleep(2)
            continue_loc = wait_for_image(CONTINUE_IMAGE, timeout=3)
            if continue_loc:
                center = pyautogui.center(continue_loc)
                pyautogui.moveTo(center.x, center.y, duration=0.9)
                time.sleep(1.0)
                pyautogui.mouseDown()
                time.sleep(0.2)
                pyautogui.mouseUp()
                print("🏆 Clicked Continue — fight over.")
                time.sleep(2)
                return

def main():
    print("🎮 Starting Miscrits auto-farm bot...")
    while True:
        print("🔍 Looking for bush...")
        if click_image(BUSH_IMAGE, timeout=10, offset=BUSH_OFFSET):
            print("🌿 Clicked bush (with offset).")
            time.sleep(3)

            thump_found = wait_for_image(THUMP_IMAGE, timeout=5)
            if thump_found:
                fight_sequence()
            else:
                print("💰 No fight started (coin/item drop). Waiting 30 seconds cooldown.")
                time.sleep(30)
        else:
            print("❌ Bush not found on screen. Retrying in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    main()
