#!/usr/bin/env python3
"""GE STARR Design: rebrand this fork of SolidCraft (MIT OR Apache-2.0 as of a34756830, 10 Nov 2026).

Idempotent; run from the repository root after merging upstream changes: python3 gestarr/rebrand.py
MIT/Apache grant no rights to the SolidCraft name or logo, so both go; the copyright and licence notices stay
(LICENSE-MIT, LICENSE-APACHE, NOTICE, THIRD-PARTY-LICENSES.txt, and the credits line in Help > About).
"""
import json, pathlib, re, shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent
NAME = "GE STARR Design"
TEXT_DIRS = ["crates/ui-egui/src", "crates/ui-kit/src", "crates/theme/src", "apps/solidcraft-web/src"]
BRAND = ROOT / "gestarr" / "brand"


def sub_name(s: str) -> str:
    # The product name only: lower-case ids (solidcraft_canvas, .solidcraft files, crate names) and URLs stay.
    return re.sub(r"(?<!Built on )\bSolidCraft\b", NAME, s)  # keeps the credit line


def text_files():
    for d in TEXT_DIRS:
        for p in (ROOT / d).rglob("*.rs"):
            yield p


def main():
    n = 0
    for p in text_files():
        s = p.read_text()
        t = sub_name(s)
        if t != s:
            p.write_text(t); n += 1
    # Locales: keys are the English source strings the code looks up, so keys and values change together.
    for p in (ROOT / "assets/locales").rglob("*.json"):
        s = p.read_text()
        t = sub_name(s)
        if t != s:
            json.loads(t); p.write_text(t); n += 1
    # The web shell.
    web = ROOT / "apps/solidcraft-web"
    html = (web / "index.html").read_text()
    head_meta = re.compile(r"  <title>.*?</title>\n.*?(?=  <link data-trunk rel=\"rust\")", re.S)
    html = head_meta.sub(f"  <title>{NAME}</title>\n  <meta name=\"description\" content=\"{NAME}: design and edit sheet-metal and fabricated parts for GE STARR Engineering.\">\n  <meta name=\"robots\" content=\"noindex\">\n", html)
    html = re.sub(r"\.\./\.\./assets/icons/app/linux/exports/hicolor/(\d+)x\d+/apps/io\.tangencylabs\.solidcraft\.png", r"../../gestarr/brand/mark-\1.png", html)
    html = re.sub(r"icons/(\d+)x\d+/io\.tangencylabs\.solidcraft\.png", r"icons/\1x\1/mark-\1.png", html)
    html = html.replace("../../assets/styles/web/loading-logo.svg", "../../gestarr/brand/loading-logo.svg")
    html = sub_name(html).replace('content="#343840"', 'content="#2E3D4F"')
    (web / "index.html").write_text(html)
    m = json.loads((web / "manifest.webmanifest").read_text())
    m.update(name=NAME, short_name="GS Design", description=f"{NAME}: parts for GE STARR Engineering.", theme_color="#2E3D4F", background_color="#FFFFFF")
    m["icons"] = [{"src": f"icons/{s}x{s}/mark-{s}.png", "sizes": f"{s}x{s}", "type": "image/png"} for s in (32, 256, 512)]
    (web / "manifest.webmanifest").write_text(json.dumps(m, indent=2) + "\n")
    css = ROOT / "assets/styles/web/loading.css"
    css.write_text(css.read_text().replace("#e8ebf0", "#ffffff").replace("#4a5060", "#2e3d4f"))
    shutil.copy(BRAND / "mark.svg", BRAND / "loading-logo.svg")
    # Colours: GE STARR navy #2E3D4F app bar, slate #4A5E72 accent, steel #C2CDD6.
    pal = ROOT / "crates/theme/src/palettes.rs"
    s = pal.read_text()
    for a, b in [("app_bar: Color32::from_rgb(52, 56, 64)", "app_bar: Color32::from_rgb(46, 61, 79)"),
                 ("app_bar_tab_active: Color32::from_rgb(53, 59, 71)", "app_bar_tab_active: Color32::from_rgb(74, 94, 114)"),
                 ("accent: Color32::from_rgb(38, 120, 218)", "accent: Color32::from_rgb(46, 61, 79)"),
                 ("accent_soft: Color32::from_rgb(214, 230, 250)", "accent_soft: Color32::from_rgb(222, 229, 235)"),
                 ("t.app_bar = Color32::from_rgb(28, 31, 38)", "t.app_bar = Color32::from_rgb(30, 41, 54)"),
                 ("t.accent = Color32::from_rgb(58, 136, 238)", "t.accent = Color32::from_rgb(86, 116, 146)"),
                 ("t.accent_soft = Color32::from_rgb(42, 70, 110)", "t.accent_soft = Color32::from_rgb(58, 74, 92)"),
                 # The app bar's GS badge: steel badge, navy letters.
                 ("logo: [Color32::from_rgb(96, 158, 236), Color32::from_rgb(58, 136, 238), Color32::from_rgb(55, 108, 197)]",
                  "logo: [Color32::from_rgb(194, 205, 214), Color32::from_rgb(74, 94, 114), Color32::from_rgb(46, 61, 79)]")]:
        s = s.replace(a, b)
    pal.write_text(s)
    # Help > About: say what this is built on (the licence texts below it come from the engine, unchanged).
    help_rs = ROOT / "crates/ui-egui/src/help.rs"
    h = help_rs.read_text().replace('"Open-source parametric 3D CAD in Rust. Licensed MIT OR Apache-2.0."',
                                    '"GE STARR Engineering. Built on SolidCraft (github.com/tangency-labs/solidcraft), MIT OR Apache-2.0."')
    help_rs.write_text(h)
    # Links: help and problem reports go to TRACK, never to SolidCraft's site or public issue tracker (a report
    # carries the customer's diagnostics). The update check is already off in the browser build.
    for rel, a, b in [("crates/ui-egui/src/help.rs", '"https://docs.solidcraft.io/"', '"https://app.gestarr.co.uk/design/help/"'),
                      ("crates/ui-egui/src/update.rs", '"https://github.com/tangency-labs/solidcraft/releases"', '"https://app.gestarr.co.uk/design/help/"'),
                      ("crates/ui-egui/src/issue_report.rs", '"https://github.com/tangency-labs/solidcraft/issues/new"', '"https://app.gestarr.co.uk/design/report"')]:
        f = ROOT / rel
        f.write_text(f.read_text().replace(a, b))
    print(f"rebranded {n} files as {NAME}")


if __name__ == "__main__":
    main()
