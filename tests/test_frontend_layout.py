"""Tests for frontend layout, navigation tab vertical positioning, and container spacing."""
import re
from pathlib import Path

def test_tabs_parent_container_vertical_positioning():
    """
    Verifies that FinQuery's top navigation tabs have appropriate top margin/padding
    on their parent container to move them down by 20-30px, preventing top clipping.
    """
    app_py_path = Path("frontend/app.py")
    assert app_py_path.exists(), "frontend/app.py must exist"
    
    content = app_py_path.read_text(encoding="utf-8")
    
    # 1. Verify parent container selector targeting stTabs
    assert 'div[data-testid="stTabs"]' in content or '.stTabs' in content, (
        "CSS should target the tabs' parent container via 'div[data-testid=\"stTabs\"]' or '.stTabs'"
    )
    
    # 2. Extract the CSS block for tabs
    tab_css_match = re.search(
        r'(?:div\[data-testid="stTabs"\]|\.stTabs)[^{]*\{([^}]+)\}',
        content
    )
    assert tab_css_match, "Must have CSS rules for the tabs parent container"
    tab_rules = tab_css_match.group(1)
    
    # 3. Verify top margin or padding is present
    spacing_match = re.search(r'(margin-top|padding-top)\s*:\s*(\d+)px', tab_rules)
    assert spacing_match, "Should specify margin-top or padding-top in pixels"
    
    prop, val_px = spacing_match.group(1), int(spacing_match.group(2))
    assert 20 <= val_px <= 30, (
        f"Top spacing on tabs parent container ({prop}: {val_px}px) must be approximately 20-30px, got {val_px}px"
    )

def test_sidebar_remains_untouched():
    """Verifies that the sidebar is not moved, shifted, or resized."""
    content = Path("frontend/app.py").read_text(encoding="utf-8")
    
    # Ensure no disruptive margin or position overrides on sidebar
    assert 'data-testid="stSidebar" { margin-top' not in content
    assert '.stSidebar { margin-top' not in content
    assert 'data-testid="stSidebar" { padding-top' not in content

def test_tabs_horizontal_alignment_preserved():
    """Verifies that tab horizontal layout is not broken by flex-direction overrides."""
    content = Path("frontend/app.py").read_text(encoding="utf-8")
    
    # Verify we did not force flex-direction: column or block on tabs
    tab_list_match = re.search(r'data-baseweb="tab-list"[^{]*\{([^}]+)\}', content)
    if tab_list_match:
        rules = tab_list_match.group(1)
        assert "flex-direction: column" not in rules
        assert "display: block" not in rules
