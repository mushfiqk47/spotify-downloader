"""StreamRip Core - backend launcher (serves UI.html)."""
import webbrowser
from server import app


def main():
    url = "http://127.0.0.1:5050"
    print(f"StreamRip backend on {url}")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    app.run(host="127.0.0.1", port=5050, debug=False, threaded=True)


if __name__ == "__main__":
    main()
