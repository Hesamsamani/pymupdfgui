# -*- coding: utf-8 -*-
"""Stylesheets for Distilmark.

Design system: **PyOneDark structure × PyDracula palette**

Structural patterns adopted from Wanderson Magalhães' PyOneDark widgets
(``Wanderson-Magalhaes/PyOneDark_Qt_Widgets_Modern_GUI``):
  • collapsible left icon-rail sidebar
  • per-tier surface stack: window → sidebar → sub-surface (inputs/tabs) → card
  • left-edge accent bar on the active navigation item
  • bottom-edge accent bar on the active tab
  • generous rounded corners (10–13 px on surfaces, 8–10 px on controls)

Colours pulled verbatim from PyDracula's ``themes/py_dracula_dark.qss``
(``Wanderson-Magalhaes/Modern_GUI_PyDracula_PySide6_or_PyQt6``) and the
canonical Dracula spec at https://draculatheme.com/contribute :

  Window         #282C34   Sidebar rail   #21252B   Sub-surface   #1B1D23
  Card / panel   #2C313C   Border         #2C313A   Border hover  #404758
  Primary text   #F8F8F2   Secondary      #ABB2BF   Description   #717E95
  Comment muted  #6272A4
  Accent purple  #BD93F9   hover #C4A1F9  pressed #B48DEE   (selection + focus)
  Accent pink    #FF79C6   hover #FF8BCD  pressed #E66CB8   (primary CTA)
  Cyan info      #8BE9FD   Green ok #50FA7B   Yellow warn #F1FA8C   Red err #FF5555

The light variant keeps Dracula's signature **purple + pink accents** on a
soft cool-grey paper (#E5E9F0 → #ECEFF4 → #FFFFFF) so the brand stays
recognisable across themes.
"""

_FONT = '"Inter", "Segoe UI Variable", "Segoe UI", "SF Pro Text", sans-serif'

# ---------------------------------------------------------------------------
# DARK — PyDracula
# ---------------------------------------------------------------------------

DARK = f"""
* {{ font-family: {_FONT}; font-size: 13px; }}
QMainWindow, QWidget {{ background-color: #282C34; color: #F8F8F2; }}

/* ---- Sidebar rail ---- */
QFrame#Sidebar {{ background-color: #21252B; border-right: 1px solid #2C313A; }}
QLabel#Logo {{ color: #F8F8F2; font-size: 20px; font-weight: 800; padding: 20px 18px 0 18px; }}
QLabel#Subtitle {{ color: #717E95; padding: 2px 18px 18px 18px; font-size: 11px; }}
QPushButton#Brand {{ background: transparent; border: none; padding: 0; margin: 0; text-align: center; }}
QPushButton#Brand:hover {{ background: #1B1D23; }}
QLabel#SectionLabel {{
    color: #6272A4; font-size: 10px; font-weight: 700;
    padding: 18px 18px 8px 18px; letter-spacing: 1.4px;
}}

/* ---- Buttons (secondary / default) ---- */
QPushButton {{
    background-color: #2C313C;
    color: #F8F8F2;
    border: 1px solid #353A45;
    border-radius: 8px;
    padding: 9px 16px;
    font-weight: 500;
}}
QPushButton:hover {{ background-color: #394150; border-color: #3D4656; }}
QPushButton:pressed {{ background-color: #232831; border-color: #2B323D; }}
QPushButton:disabled {{ color: #4F5B6E; background-color: #21252B; border-color: #2C313A; }}

/* ---- Primary CTA (Dracula pink) — Convert, Save, single per screen ---- */
QPushButton#Primary {{
    background-color: #FF79C6;
    color: #21252B;
    border: none;
    font-weight: 800;
    padding: 11px 26px;
}}
QPushButton#Primary:hover {{ background-color: #FF8BCD; }}
QPushButton#Primary:pressed {{ background-color: #E66CB8; }}
QPushButton#Primary:disabled {{ background-color: #6A4A5C; color: #21252B; }}

/* ---- Accent action (Dracula purple) — Save settings, secondary CTA ---- */
QPushButton#Accent {{
    background-color: #BD93F9;
    color: #21252B;
    border: none;
    font-weight: 700;
}}
QPushButton#Accent:hover {{ background-color: #C4A1F9; }}
QPushButton#Accent:pressed {{ background-color: #B48DEE; }}
QPushButton#Accent:disabled {{ background-color: #565068; color: #21252B; }}

QPushButton#Ghost {{ background: transparent; border: 1px solid #353A45; color: #ABB2BF; }}
QPushButton#Ghost:hover {{ background-color: #2C313C; color: #F8F8F2; border-color: #404758; }}

QPushButton#Danger {{ background: transparent; border: 1px solid #6E2A30; color: #FF5555; }}
QPushButton#Danger:hover {{ background-color: #3A1B22; border-color: #FF5555; color: #FF7B7B; }}
QPushButton#Danger:disabled {{ color: #4F5B6E; border-color: #2C313A; }}

/* ---- Nav items (icon rail) ---- */
QPushButton#NavItem {{
    text-align: left;
    background: transparent;
    border: none;
    border-left: 3px solid transparent;     /* accent bar lives here */
    border-radius: 8px;
    padding: 11px 14px;
    margin: 2px 10px;
    color: #ABB2BF;
    font-weight: 500;
}}
QPushButton#NavItem:hover {{ background-color: #2C313C; color: #F8F8F2; }}
QPushButton#NavItem:checked {{
    background-color: #2C313C;
    color: #F8F8F2;
    border-left: 3px solid #BD93F9;          /* signature purple accent bar */
    font-weight: 700;
}}

/* ---- Inputs ---- */
QLineEdit, QComboBox, QSpinBox, QTextEdit, QPlainTextEdit {{
    background-color: #1B1D23;
    border: 1px solid #2C313A;
    border-radius: 8px;
    padding: 8px 11px;
    color: #F8F8F2;
    selection-background-color: #BD93F9;
    selection-color: #21252B;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus,
QTextEdit:focus, QPlainTextEdit:focus {{ border-color: #BD93F9; }}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover {{ border-color: #404758; }}

QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #717E95;
    margin-right: 11px;
}}
QComboBox QAbstractItemView {{
    background-color: #272C36;
    border: 1px solid #2C313A;
    border-radius: 8px;
    selection-background-color: #BD93F9;
    selection-color: #21252B;
    padding: 5px;
    outline: none;
}}
QSpinBox::up-button, QSpinBox::down-button {{ width: 18px; border: none; background: #2C313C; }}
QSpinBox::up-button {{ border-top-right-radius: 8px; }}
QSpinBox::down-button {{ border-bottom-right-radius: 8px; }}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background: #394150; }}
QSpinBox::up-arrow {{ border-left: 4px solid transparent; border-right: 4px solid transparent; border-bottom: 5px solid #717E95; }}
QSpinBox::down-arrow {{ border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid #717E95; }}

/* ---- Lists ---- */
QListWidget {{
    background-color: #1B1D23;
    border: 1px solid #2C313A;
    border-radius: 12px;
    padding: 6px;
    outline: none;
    alternate-background-color: #21252B;
}}
QListWidget::item {{ padding: 11px; border-radius: 6px; color: #ABB2BF; }}
QListWidget::item:hover {{ background-color: #2C313C; color: #F8F8F2; }}
QListWidget::item:selected {{ background-color: #3A2F4F; color: #BD93F9; }}

/* ---- Tree (Courses library) ---- */
QTreeWidget, QTreeView {{
    background-color: #1B1D23;
    alternate-background-color: #21252B;
    border: 1px solid #2C313A;
    border-radius: 12px;
    padding: 4px;
    outline: none;
}}
QTreeWidget::item, QTreeView::item {{ padding: 6px 4px; color: #ABB2BF; border-radius: 4px; }}
QTreeWidget::item:hover, QTreeView::item:hover {{ background-color: #2C313C; color: #F8F8F2; }}
QTreeWidget::item:selected, QTreeView::item:selected {{ background-color: #3A2F4F; color: #F8F8F2; }}
QHeaderView::section {{
    background-color: #21252B;
    color: #717E95;
    padding: 7px 10px;
    border: none;
    border-bottom: 1px solid #2C313A;
    font-weight: 700;
    letter-spacing: 0.6px;
}}
QTreeWidget::branch {{ background: transparent; }}

/* ---- Progress bar (purple → pink Dracula gradient) ---- */
QProgressBar {{
    background-color: #1B1D23;
    border: none;
    border-radius: 5px;
    height: 10px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    border-radius: 5px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #BD93F9, stop:1 #FF79C6);
}}

/* ---- Group boxes (cards) ---- */
QGroupBox {{
    background-color: #2C313C;
    border: 1px solid #353A45;
    border-radius: 13px;
    margin-top: 18px;
    padding: 18px 16px 14px 16px;
    font-weight: 700;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 16px;
    top: 2px;
    padding: 2px 9px;
    color: #BD93F9;
    background-color: #282C34;
    border-radius: 6px;
}}

/* ---- Tabs (Preview) ---- */
QTabWidget::pane {{
    border: 1px solid #2C313A;
    border-radius: 12px;
    top: -1px;
    background: #1B1D23;
}}
QTabBar::tab {{
    background: transparent;
    color: #717E95;
    padding: 10px 18px;
    margin-right: 4px;
    border: none;
    border-bottom: 2px solid transparent;   /* PyOneDark-style active underline */
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 600;
}}
QTabBar::tab:hover {{ color: #F8F8F2; background: #2C313C; }}
QTabBar::tab:selected {{
    color: #BD93F9;
    background: #1B1D23;
    border-bottom: 2px solid #BD93F9;
}}

/* ---- Status text helpers ---- */
QLabel#StatusOk   {{ color: #50FA7B; }}
QLabel#StatusErr  {{ color: #FF5555; }}
QLabel#StatusWarn {{ color: #F1FA8C; }}
QLabel#Hint       {{ color: #6272A4; font-size: 11px; }}
QLabel#H1         {{ font-size: 24px; font-weight: 800; color: #F8F8F2; }}
QLabel#H2         {{ color: #717E95; font-size: 13px; }}

/* ---- Checkboxes ---- */
QCheckBox {{ padding: 5px; spacing: 9px; color: #ABB2BF; }}
QCheckBox::indicator {{
    width: 18px; height: 18px; border: 1px solid #404758; border-radius: 4px; background-color: #1B1D23;
}}
QCheckBox::indicator:hover {{ border-color: #BD93F9; }}
QCheckBox::indicator:checked {{ background-color: #BD93F9; border-color: #BD93F9; }}

/* ---- Radio buttons ---- */
QRadioButton {{ padding: 5px; spacing: 9px; color: #ABB2BF; }}
QRadioButton::indicator {{
    width: 16px; height: 16px; border: 1px solid #404758; border-radius: 8px; background-color: #1B1D23;
}}
QRadioButton::indicator:hover {{ border-color: #BD93F9; }}
QRadioButton::indicator:checked {{ background-color: #BD93F9; border: 4px solid #1B1D23; }}

/* ---- Status bar ---- */
QStatusBar {{ background-color: #21252B; color: #717E95; border-top: 1px solid #2C313A; }}
QStatusBar::item {{ border: none; }}

/* ---- Tooltips ---- */
QToolTip {{
    background-color: #21252B;
    color: #F8F8F2;
    border: 1px solid #BD93F9;
    border-radius: 6px;
    padding: 6px 10px;
}}

/* ---- Splitter handles ---- */
QSplitter::handle {{ background: transparent; }}
QSplitter::handle:horizontal {{ width: 4px; }}
QSplitter::handle:vertical   {{ height: 4px; }}
QSplitter::handle:hover {{ background: #BD93F9; }}

/* ---- Menus (for context menus on the Courses tree) ---- */
QMenu {{
    background-color: #272C36;
    border: 1px solid #2C313A;
    border-radius: 8px;
    padding: 4px;
    color: #F8F8F2;
}}
QMenu::item {{ padding: 7px 18px; border-radius: 4px; }}
QMenu::item:selected {{ background-color: #BD93F9; color: #21252B; }}
QMenu::separator {{ height: 1px; background: #2C313A; margin: 4px 6px; }}

/* ---- Scrollbars ---- */
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 12px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #404758; border-radius: 5px; min-height: 36px; }}
QScrollBar::handle:vertical:hover {{ background: #BD93F9; }}
QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: #404758; border-radius: 5px; min-width: 36px; }}
QScrollBar::handle:horizontal:hover {{ background: #BD93F9; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
"""


# ---------------------------------------------------------------------------
# LIGHT — Dracula-themed light variant
# ---------------------------------------------------------------------------

LIGHT = f"""
* {{ font-family: {_FONT}; font-size: 13px; }}
QMainWindow, QWidget {{ background-color: #E5E9F0; color: #282A36; }}

/* ---- Sidebar rail ---- */
QFrame#Sidebar {{ background-color: #D8DEE9; border-right: 1px solid #C3CCDF; }}
QLabel#Logo {{ color: #282A36; font-size: 20px; font-weight: 800; padding: 20px 18px 0 18px; }}
QLabel#Subtitle {{ color: #6272A4; padding: 2px 18px 18px 18px; font-size: 11px; }}
QPushButton#Brand {{ background: transparent; border: none; padding: 0; margin: 0; text-align: center; }}
QPushButton#Brand:hover {{ background: #C3CCDF; }}
QLabel#SectionLabel {{
    color: #8A95AA; font-size: 10px; font-weight: 700;
    padding: 18px 18px 8px 18px; letter-spacing: 1.4px;
}}

/* ---- Buttons (secondary / default) ---- */
QPushButton {{
    background-color: #FFFFFF;
    color: #282A36;
    border: 1px solid #C3CCDF;
    border-radius: 8px;
    padding: 9px 16px;
    font-weight: 500;
}}
QPushButton:hover {{ background-color: #ECEFF4; border-color: #A6B0C2; }}
QPushButton:pressed {{ background-color: #D8DEE9; }}
QPushButton:disabled {{ color: #A6B0C2; background-color: #ECEFF4; border-color: #C3CCDF; }}

QPushButton#Primary {{
    background-color: #FF79C6; color: #21252B; border: none; font-weight: 800; padding: 11px 26px;
}}
QPushButton#Primary:hover  {{ background-color: #FF8BCD; }}
QPushButton#Primary:pressed{{ background-color: #E66CB8; }}
QPushButton#Primary:disabled {{ background-color: #F5C0DD; color: #FFFFFF; }}

QPushButton#Accent {{
    background-color: #BD93F9; color: #21252B; border: none; font-weight: 700;
}}
QPushButton#Accent:hover  {{ background-color: #C4A1F9; }}
QPushButton#Accent:pressed{{ background-color: #B48DEE; }}

QPushButton#Ghost {{ background: transparent; border: 1px solid #C3CCDF; color: #4B5263; }}
QPushButton#Ghost:hover {{ background-color: #ECEFF4; color: #282A36; }}

QPushButton#Danger {{ background: transparent; border: 1px solid #F3C2CB; color: #C53939; }}
QPushButton#Danger:hover {{ background-color: #FBE6E9; border-color: #C53939; }}
QPushButton#Danger:disabled {{ color: #A6B0C2; border-color: #C3CCDF; }}

QPushButton#NavItem {{
    text-align: left; background: transparent; border: none; border-left: 3px solid transparent;
    border-radius: 8px; padding: 11px 14px; margin: 2px 10px; color: #4B5263; font-weight: 500;
}}
QPushButton#NavItem:hover {{ background-color: #ECEFF4; color: #282A36; }}
QPushButton#NavItem:checked {{
    background-color: #F1E9FF; color: #6E3FC9; border-left: 3px solid #BD93F9; font-weight: 700;
}}

QLineEdit, QComboBox, QSpinBox, QTextEdit, QPlainTextEdit {{
    background-color: #FFFFFF; border: 1px solid #C3CCDF; border-radius: 8px; padding: 8px 11px;
    color: #282A36; selection-background-color: #BD93F9; selection-color: #FFFFFF;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus, QPlainTextEdit:focus {{ border-color: #BD93F9; }}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover {{ border-color: #A6B0C2; }}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox::down-arrow {{ border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid #8A95AA; margin-right: 11px; }}
QComboBox QAbstractItemView {{
    background-color: #FFFFFF; border: 1px solid #C3CCDF; border-radius: 8px;
    selection-background-color: #F1E9FF; selection-color: #6E3FC9; padding: 5px; outline: none;
}}
QSpinBox::up-button, QSpinBox::down-button {{ width: 18px; border: none; background: #ECEFF4; }}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background: #D8DEE9; }}
QSpinBox::up-arrow {{ border-left: 4px solid transparent; border-right: 4px solid transparent; border-bottom: 5px solid #8A95AA; }}
QSpinBox::down-arrow {{ border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid #8A95AA; }}

QListWidget {{ background-color: #FFFFFF; border: 1px solid #C3CCDF; border-radius: 12px; padding: 6px; outline: none; alternate-background-color: #F5F6F9; }}
QListWidget::item {{ padding: 11px; border-radius: 6px; color: #3B4252; }}
QListWidget::item:hover {{ background-color: #ECEFF4; }}
QListWidget::item:selected {{ background-color: #F1E9FF; color: #6E3FC9; }}

QTreeWidget, QTreeView {{
    background-color: #FFFFFF; alternate-background-color: #F5F6F9;
    border: 1px solid #C3CCDF; border-radius: 12px; padding: 4px; outline: none;
}}
QTreeWidget::item, QTreeView::item {{ padding: 6px 4px; color: #3B4252; border-radius: 4px; }}
QTreeWidget::item:hover, QTreeView::item:hover {{ background-color: #ECEFF4; }}
QTreeWidget::item:selected, QTreeView::item:selected {{ background-color: #F1E9FF; color: #6E3FC9; }}
QHeaderView::section {{
    background-color: #ECEFF4; color: #6B7280; padding: 7px 10px; border: none;
    border-bottom: 1px solid #C3CCDF; font-weight: 700; letter-spacing: 0.6px;
}}

QProgressBar {{ background-color: #ECEFF4; border: none; border-radius: 5px; height: 10px; text-align: center; color: transparent; }}
QProgressBar::chunk {{ border-radius: 5px; background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #BD93F9, stop:1 #FF79C6); }}

QGroupBox {{
    background-color: #FFFFFF; border: 1px solid #C3CCDF; border-radius: 13px;
    margin-top: 18px; padding: 18px 16px 14px 16px; font-weight: 700;
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 16px; top: 2px; padding: 2px 9px; color: #6E3FC9; background-color: #E5E9F0; border-radius: 6px; }}

QTabWidget::pane {{ border: 1px solid #C3CCDF; border-radius: 12px; top: -1px; background: #FFFFFF; }}
QTabBar::tab {{
    background: transparent; color: #6B7280; padding: 10px 18px; margin-right: 4px; border: none;
    border-bottom: 2px solid transparent; border-top-left-radius: 8px; border-top-right-radius: 8px; font-weight: 600;
}}
QTabBar::tab:hover {{ color: #282A36; background: #ECEFF4; }}
QTabBar::tab:selected {{ color: #6E3FC9; background: #FFFFFF; border-bottom: 2px solid #BD93F9; }}

QLabel#StatusOk   {{ color: #2EAB55; }}
QLabel#StatusErr  {{ color: #C53939; }}
QLabel#StatusWarn {{ color: #D9A93C; }}
QLabel#Hint       {{ color: #6272A4; font-size: 11px; }}
QLabel#H1         {{ font-size: 24px; font-weight: 800; color: #161A26; }}
QLabel#H2         {{ color: #6272A4; font-size: 13px; }}

QCheckBox {{ padding: 5px; spacing: 9px; color: #3B4252; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border: 1px solid #A6B0C2; border-radius: 4px; background-color: #FFFFFF; }}
QCheckBox::indicator:hover {{ border-color: #BD93F9; }}
QCheckBox::indicator:checked {{ background-color: #BD93F9; border-color: #BD93F9; }}

QRadioButton {{ padding: 5px; spacing: 9px; color: #3B4252; }}
QRadioButton::indicator {{ width: 16px; height: 16px; border: 1px solid #A6B0C2; border-radius: 8px; background-color: #FFFFFF; }}
QRadioButton::indicator:hover {{ border-color: #BD93F9; }}
QRadioButton::indicator:checked {{ background-color: #BD93F9; border: 4px solid #FFFFFF; }}

QStatusBar {{ background-color: #D8DEE9; color: #6272A4; border-top: 1px solid #C3CCDF; }}
QStatusBar::item {{ border: none; }}

QToolTip {{
    background-color: #FFFFFF; color: #282A36; border: 1px solid #BD93F9; border-radius: 6px; padding: 6px 10px;
}}

QSplitter::handle {{ background: transparent; }}
QSplitter::handle:horizontal {{ width: 4px; }}
QSplitter::handle:vertical   {{ height: 4px; }}
QSplitter::handle:hover {{ background: #BD93F9; }}

QMenu {{
    background-color: #FFFFFF; border: 1px solid #C3CCDF; border-radius: 8px; padding: 4px; color: #282A36;
}}
QMenu::item {{ padding: 7px 18px; border-radius: 4px; }}
QMenu::item:selected {{ background-color: #BD93F9; color: #FFFFFF; }}
QMenu::separator {{ height: 1px; background: #C3CCDF; margin: 4px 6px; }}

QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 12px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #C3CCDF; border-radius: 5px; min-height: 36px; }}
QScrollBar::handle:vertical:hover {{ background: #BD93F9; }}
QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: #C3CCDF; border-radius: 5px; min-width: 36px; }}
QScrollBar::handle:horizontal:hover {{ background: #BD93F9; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
"""
