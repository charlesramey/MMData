from playwright.sync_api import sync_playwright, expect

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # Open the app
    page.goto("http://localhost:8000")

    # Wait for splitters to be visible
    splitter = page.locator("#split-1")
    expect(splitter).to_be_visible()

    # Get initial height of spectrogram container (below split-1)
    # The structure is: video-container, split-1, spectrogram-container, split-2, sensor-container
    spec_container = page.locator("#spectrogram-container")
    video_container = page.locator("#video-container")

    initial_h = spec_container.evaluate("el => el.getBoundingClientRect().height")
    print(f"Initial Spectrogram Height: {initial_h}")

    # Perform Drag on split-1
    # Move mouse to splitter
    box = splitter.bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.down()
    # Drag down by 50px (should increase video height, decrease spectrogram height)
    # Wait, split-1 is between video (prev) and spectrogram (next).
    # Dragging DOWN increases prev (video) and decreases next (spectrogram).
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2 + 50)
    page.mouse.up()

    # Check new height
    new_h = spec_container.evaluate("el => el.getBoundingClientRect().height")
    print(f"New Spectrogram Height: {new_h}")

    # Verify change
    if abs(initial_h - new_h) > 10:
        print("Resizing verification PASSED")
    else:
        print("Resizing verification FAILED")

    # Take screenshot
    page.screenshot(path="/tmp/verification.png")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)
