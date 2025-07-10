import pyautogui
import time

# === CONFIGURATION ===
BUSH_IMAGE = 'bush.png'
THUMP_IMAGE = 'thump2.png'
CONTINUE_IMAGE = 'continue.png'
DEFAULT_CONFIDENCE = 0.65
BUSH_OFFSET = (30, 30)  # Offset click for bush: (right, down)

def wait_for_image(image_path, timeout=15, confidence=DEFAULT_CONFIDENCE, check_interval=0.5):
    """
    Waits for an image to appear on screen until timeout.
    Returns the location if found, else None.
    """
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
    """
    Waits for an image, moves to (center + offset), hovers, then performs a realistic click.
    Returns True if clicked, False otherwise.
    """
    location = wait_for_image(image_path, timeout=timeout, confidence=confidence)
    if location:
        center = pyautogui.center(location)
        corrected_x = center.x + offset[0]
        corrected_y = center.y + offset[1]
        
        pyautogui.moveTo(corrected_x, corrected_y, duration=0.7)
        time.sleep(1.0)  # longer hover over bush

        pyautogui.mouseDown()
        time.sleep(0.15)  # mimic real click delay
        pyautogui.mouseUp()
        
        return True
    return False


def fight_sequence():
    print("💥 Battle started! Attacking with Thump...")
    while True:
        if click_image(THUMP_IMAGE, timeout=4):
            print("➡️ Clicked Thump")
            time.sleep(3)

        else:
            print("⚠️ Thump button missing, ending fight sequence.")
            time.sleep(2)
            continue_loc = wait_for_image(CONTINUE_IMAGE, timeout=3)
            if continue_loc:
                center = pyautogui.center(continue_loc)
                pyautogui.moveTo(center.x, center.y, duration=0.9)  # hover slower
                time.sleep(1.0)  # longer hover before clicking

                pyautogui.mouseDown()
                time.sleep(0.2)  # hold click longer
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
