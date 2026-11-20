import pathlib
import re

path = pathlib.Path("app.py")
src = path.read_text(encoding="utf-8")

src = re.sub(r'<div id="(?:centeredLogoOnly|centeredHeroLogo|inlineBrandBar)"[^>]*>.*?</div>\s*', "", src, flags=re.S)

big_logo = (
    '<img src="/static/logo.png" alt="Tiny Capital Club Logo" '
    'style="width:88px;height:88px;min-width:88px;border-radius:50%;object-fit:cover;'
    'border:2px solid #f59e0b;flex-shrink:0;" />'
)

heading_pattern = re.compile(
    r'(<h[1-3][^>]*>\s*)(?:Tiny\s*Capital\s*Club\s*StockPulse\s*Pro|TinyCapitalCapital\s*StockPulse\s*Pro)(\s*</h[1-3]>)',
    flags=re.S | re.I,
)

replacement = (
    r'<div id="inlineBrandBar" style="display:flex;align-items:center;justify-content:flex-start;'
    r'gap:14px;margin:6px 0 12px 0;">'
    + big_logo
    + r'\1Tiny Capital Club StockPulse Pro\2'
    + r'</div>'
)

if heading_pattern.search(src):
    src = heading_pattern.sub(replacement, src, count=1)
else:
    src = src.replace("Tiny Capital Club StockPulse Pro", f"{big_logo}<span>Tiny Capital Club StockPulse Pro</span>", 1)

path.write_text(src, encoding="utf-8")
print("Updated logo to 88px inline with Tiny Capital Club StockPulse Pro.")
