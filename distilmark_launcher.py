"""Entry point for the prebuilt Distilmark executable.

Lives at the repo root so PyInstaller treats the parent directory as
sys.path[0], which makes the `distilmark` package importable. The package's
own `__main__.py` uses a relative import that only works under
`python -m distilmark`.
"""
import sys


def _close_pyi_splash() -> None:
    """If the .exe was built with PyInstaller --splash, dismiss the splash
    image as soon as Python's running. Harmless no-op in dev / non-frozen mode."""
    try:
        import pyi_splash  # type: ignore  # only present in frozen --splash bundles
        pyi_splash.close()
    except Exception:
        pass


def _set_windows_app_id() -> None:
    """Tell Windows this process is its own app, not a generic Python host —
    needed for the taskbar icon and Alt-Tab to show our .ico instead of the
    fallback Python interpreter icon."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "Hesamsamani.Distilmark"
        )
    except Exception:
        pass


if __name__ == "__main__":
    _set_windows_app_id()
    _close_pyi_splash()
    from distilmark.app import main
    main()
