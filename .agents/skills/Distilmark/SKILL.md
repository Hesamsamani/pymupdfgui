```markdown
# Distilmark Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill teaches you the core development patterns and workflows used in the Distilmark Python codebase. You'll learn the project's coding conventions, how to update branding and icons, refresh documentation screenshots, and bundle assets for releases. These patterns ensure consistency, maintainability, and a professional appearance for the application.

## Coding Conventions

### File Naming
- Use **camelCase** for file names.
  - Example: `iconBuilder.py`, `appMain.py`

### Import Style
- Use **relative imports** within the package.
  - Example:
    ```python
    from .utils import parseConfig
    from .styles import sidebarStyle
    ```

### Export Style
- Use **named exports** (explicitly define what is exported).
  - Example:
    ```python
    __all__ = ['AppWindow', 'Sidebar', 'loadIcons']
    ```

### Commit Messages
- Freeform, no strict prefix.
- Average length: ~66 characters.
  - Example: `Update icon assets and refresh sidebar layout`

## Workflows

### Update Branding and App Icons
**Trigger:** When you want to update the app's branding, logo, or icons for a new look or improved platform integration.  
**Command:** `/update-branding`

1. Create or update `icon.png` and `icon.ico` with new branding assets.
2. Update sidebar or header layout in `distilmark/styles.py` and `distilmark/app.py` to use the new branding.
3. Ensure the app and bundled executables load the updated icons, including fallback logic if needed.
4. Update the release workflow (`.github/workflows/release.yml`) to bundle the new icons with the executable.
5. Refresh screenshots in the `README.md` or `docs` to reflect the new branding.

**Example:**
```python
# In distilmark/app.py
from .styles import appIcon

window.setWindowIcon(appIcon('icon.ico'))
```

### Release Workflow: Icon Bundling
**Trigger:** When releasing a new version with updated icons or branding.  
**Command:** `/bundle-icons`

1. Run the script `scripts/build_icon.py` to generate `icon.ico` from `icon.png` with all required sizes.
2. Update the release workflow to run the icon build script before packaging.
3. Bundle the new icon assets into the executable using PyInstaller's `--add-data` option.
4. Verify that the bundled app displays the correct icons in the window and taskbar.

**Example:**
```bash
python scripts/build_icon.py
pyinstaller distilmark/app.py --add-data "icon.ico;."
```

### Refresh README and Screenshots After UI Change
**Trigger:** When you change the UI layout, branding, or visual appearance and want documentation to match.  
**Command:** `/refresh-doc-screenshots`

1. Take new screenshots of the updated UI.
2. Replace outdated screenshot files in the `screenshots/` directory.
3. Update `README.md` to reference the new screenshots.

**Example:**
```markdown
![New UI](screenshots/convert-dark.png)
```

## Testing Patterns

- **Framework:** Unknown (not explicitly detected).
- **Test file pattern:** Files follow the `*.test.*` naming convention.
  - Example: `app.test.py`, `utils.test.py`
- **How to write tests:** Follow the naming pattern and keep tests close to the code they verify.

## Commands

| Command                 | Purpose                                                      |
|-------------------------|--------------------------------------------------------------|
| /update-branding        | Refresh branding, icons, and update app visuals              |
| /bundle-icons           | Build and bundle icon assets for release                     |
| /refresh-doc-screenshots| Update README and screenshots after UI or branding changes   |
```