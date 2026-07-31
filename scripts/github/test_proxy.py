import argparse
import re
import sys

import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait


def normalize_proxy(proxy: str) -> str:
    proxy = proxy.strip()

    if not proxy:
        raise ValueError("Proxy is empty")

    # Already has scheme
    if "://" in proxy:
        return proxy

    # host:port
    parts = proxy.split(":")

    if len(parts) == 2:
        host, port = parts
        return f"http://{host}:{port}"

    # host:port:user:password
    if len(parts) >= 4:
        host = parts[0]
        port = parts[1]
        username = parts[2]
        password = ":".join(parts[3:])

        return f"http://{username}:{password}@{host}:{port}"

    raise ValueError(f"Unsupported proxy format: {proxy}")


def detect_chrome_version(chrome_binary: str):
    import plistlib
    from pathlib import Path

    chrome_path = Path(chrome_binary)

    # /Applications/Google Chrome.app/Contents/MacOS/Google Chrome
    app_path = chrome_path.parent.parent

    plist_path = app_path / "Info.plist"

    if not plist_path.exists():
        raise RuntimeError(
            f"Chrome Info.plist not found: {plist_path}"
        )

    with plist_path.open("rb") as f:
        plist = plistlib.load(f)

    version = plist.get("CFBundleShortVersionString")

    if not version:
        raise RuntimeError(
            f"CFBundleShortVersionString not found in {plist_path}"
        )

    match = re.search(r"(\d+)\.", version)

    if not match:
        raise RuntimeError(
            f"Could not detect Chrome major version from: {version}"
        )

    return int(match.group(1))


def test_proxy(proxy: str, chrome_binary: str):
    proxy_url = normalize_proxy(proxy)

    print("=" * 60)
    print("Proxy Test")
    print("=" * 60)
    print(f"Original : {proxy}")
    print(f"Normalized: {proxy_url}")
    print()

    chrome_version = detect_chrome_version(chrome_binary)

    print(f"Chrome version: {chrome_version}")

    options = uc.ChromeOptions()

    options.binary_location = chrome_binary

    options.add_argument(
        f"--proxy-server={proxy_url}"
    )

    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--window-size=1280,800")

    print(f"Chrome proxy: {proxy_url}")
    print("Starting Chrome...")

    driver = None

    try:
        driver = uc.Chrome(
            options=options,
            version_main=chrome_version,
            browser_executable_path=chrome_binary,
        )

        driver.set_page_load_timeout(30)

        print("Chrome started.")
        print("Opening IP-check page...")

        driver.get("https://api.ipify.org")

        WebDriverWait(driver, 15).until(
            lambda d: d.execute_script(
                "return document.readyState"
            ) == "complete"
        )

        ip = driver.find_element("tag name", "body").text.strip()

        print()
        print("=" * 60)
        print("RESULT")
        print("=" * 60)
        print(f"Observed IP: {ip}")
        print("=" * 60)

        return True

    except Exception as exc:
        print()
        print("=" * 60)
        print("FAILED")
        print("=" * 60)
        print(type(exc).__name__)
        print(str(exc))
        print("=" * 60)

        return False

    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(
        description="Test HTTP proxy connectivity through Chrome"
    )

    parser.add_argument(
        "--proxy",
        required=True,
        help="Proxy in host:port or host:port:user:password format",
    )

    parser.add_argument(
        "--chrome-binary",
        required=True,
        help="Path to Chrome binary",
    )

    args = parser.parse_args()

    success = test_proxy(
        proxy=args.proxy,
        chrome_binary=args.chrome_binary,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()