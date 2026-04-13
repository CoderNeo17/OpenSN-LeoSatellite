from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.firefox.launch(headless=True)
    page = browser.new_page()

    # capture all console output to file
    with open("/output/console.log", "w") as f:
        def handle_console(msg):
            f.write(f"[{msg.type}] {msg.text}\n")
            f.flush()

        page.on("console", handle_console)

        page.goto("http://172.17.0.1:8081")
        page.wait_for_timeout(30000)  # wait 5min for any async console output

    browser.close()