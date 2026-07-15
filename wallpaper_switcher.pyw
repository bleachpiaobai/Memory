#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
壁纸自动切换工具 - 根据时间自动切换壁纸
Q版+正常版为一组, 组内30秒切换, 每30分钟切换一组

启动方式:
  手动: 双击 start_wallpaper.bat
  自启: 双击 install_autostart.bat
  取消: 双击 uninstall_autostart.bat

维护: 编辑文件头部的配置区即可
'''

import os, sys, time, ctypes, logging, traceback, subprocess
from datetime import datetime
from pathlib import Path
from collections import OrderedDict

# ================================================================
# >>> 配置区 <<<
# ================================================================

BASE_DIR = Path(__file__).parent.resolve()
YAN_DIR = BASE_DIR / "YAN_Wallpaper"
XIA_DIR = BASE_DIR / "XIA_Wallpaper"
TOGGLE_INTERVAL = 30       # Q版 <-> 正常版 切换间隔(秒)
GROUP_INTERVAL = 1800       # 组间切换间隔(秒) = 30分钟

CHAR_CONFIG = OrderedDict([("YAN", YAN_DIR), ("XIA", XIA_DIR)])

# (start_hour, end_hour, [themes])
SCHEDULE = [
    (22, 24, ["Sleep"]),
    (0,   6, ["Sleep"]),
    (6,   8, ["Daily", "School"]),
    (8,  12, ["Business", "School"]),
    (12, 14, ["Daily", "Maid"]),
    (14, 17, ["Business", "School"]),
    (17, 19, ["Daily", "Seamen", "Kimono"]),
    (19, 22, ["Kimono", "Graduation", "Maid", "Seamen"]),
]

THEME_NAME_FIXES = {
    "Business": ["business", "bussiness"],
    "Sleep": ["sleep"], "Daily": ["daily"],
    "School": ["school"], "Kimono": ["kimono"],
    "Seamen": ["seamen"], "Graduation": ["graduation"],
    "Maid": ["maid"],
}

LOG_FILE = BASE_DIR / "wallpaper_switcher.log"

# ================================================================
# >>> 逻辑代码 <<<
# ================================================================

def setup_logging():
    from logging.handlers import RotatingFileHandler
    h = RotatingFileHandler(LOG_FILE, encoding="utf-8", maxBytes=512*1024, backupCount=2)
    h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    lg = logging.getLogger(__name__)
    lg.setLevel(logging.INFO); lg.addHandler(h)
    try:
        ch = logging.StreamHandler(); ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        lg.addHandler(ch)
    except: pass
    return lg

log = setup_logging()
LOCK_FILE = BASE_DIR / ".wallpaper_switcher.lock"

def acquire_lock():
    if LOCK_FILE.exists():
        try:
            old = int(LOCK_FILE.read_text().strip())
            r = subprocess.run(["tasklist","/FI",f"PID eq {old}","/NH","/FO","CSV"],
                               capture_output=True, text=True, creationflags=0x08000000)
            if str(old) in r.stdout:
                log.warning(f"Already running (PID {old})")
                return False
        except: pass
    LOCK_FILE.write_text(str(os.getpid()))
    return True

def release_lock():
    try:
        if LOCK_FILE.exists(): LOCK_FILE.unlink()
    except: pass

IMG = {".png",".jpg",".jpeg",".bmp",".gif",".tiff",".webp"}

def norm(raw):
    raw = raw.strip().lower().replace(" ","").replace("-","")
    for std, aliases in THEME_NAME_FIXES.items():
        for a in aliases:
            if a == raw or a in raw: return std
    return raw[0].upper()+raw[1:] if raw else raw

def scan_char(prefix, folder):
    if not folder.exists():
        log.warning(f"Folder not found: {folder}")
        return {}
    qf, nf = {}, {}
    for f in folder.iterdir():
        if not f.is_file() or f.suffix.lower() not in IMG: continue
        name = f.stem
        if name.upper().startswith("Q_") or name.upper().startswith("Q-"):
            qf[norm(name[2:])] = f
        elif name.upper().startswith(prefix.upper()):
            rest = name[len(prefix):]
            nf[norm(rest.lstrip("_").lstrip("-"))] = f
    all_t = set(qf.keys())|set(nf.keys())
    return {t:{"q":qf.get(t),"normal":nf.get(t)} for t in sorted(all_t)}

def scan_all():
    r = OrderedDict()
    for cp,fp in CHAR_CONFIG.items():
        t = scan_char(cp,fp)
        if t: r[cp]=t
    return r

def active():
    h = datetime.now().hour
    for s,e,themes in SCHEDULE:
        if s<e:
            if s<=h<e: return list(themes)
        else:
            if h>=s or h<e: return list(themes)
    return ["Daily"]

def playlist(all_wp, themes):
    """构建分组列表: 每组 = 同一角色+主题的Q版和正常版"""
    groups = []  # 每个元素: [(path, label), ...]  一组内2张(Q+正常)
    for theme in themes:
        for cn in CHAR_CONFIG:
            if cn not in all_wp or theme not in all_wp[cn]: continue
            v = all_wp[cn][theme]
            group = []
            if v["q"]: group.append((v["q"], f"{cn} Q {theme}"))
            if v["normal"]: group.append((v["normal"], f"{cn} N {theme}"))
            if group: groups.append(group)
    return groups

def set_wp(img):
    if not img or not img.exists():
        log.error(f"Missing: {img}"); return False
    try:
        ok = ctypes.windll.user32.SystemParametersInfoW(20,0,str(img.resolve()),1|2)
        if ok: log.info(f"WP: {img.name}")
        else: log.error(f"Failed: {img.name}")
        return bool(ok)
    except Exception as e:
        log.error(f"Error: {img.name} - {e}"); return False

def main():
    if not acquire_lock():
        print("Already running!")
        if sys.stdin and sys.stdin.isatty(): input("Press Enter...")
        return

    log.info("="*40)
    log.info(f"Wallpaper Switcher v1.0 - {datetime.now():%Y-%m-%d %H:%M:%S}")
    log.info(f"Toggle(Q↔N): {TOGGLE_INTERVAL}s | Group switch: {GROUP_INTERVAL}s ({GROUP_INTERVAL//60}min)")

    all_wp = scan_all()
    total = 0
    for cn,themes in all_wp.items():
        log.info(f"  [{cn}]")
        for t,v in themes.items():
            qn=v["q"].name if v["q"] else "-"
            nn=v["normal"].name if v["normal"] else "-"
            log.info(f"    {t:12s} Q={qn:25s} N={nn}")
            if v["q"]: total+=1
            if v["normal"]: total+=1
    log.info(f"Total: {total} images")

    if total==0:
        log.error("No images!"); release_lock(); return

    last_t=None; groups=[]; group_idx=0; toggle=0; group_start=0
    log.info("Starting loop...")

    try:
        while True:
            t = active()
            if t != last_t:
                log.info(f"--- {datetime.now():%H:%M} -> {t}")
                groups = playlist(all_wp, t)
                if groups:
                    for i, g in enumerate(groups):
                        names = ", ".join(d for _, d in g)
                        log.info(f"  G{i+1:2d}. [{names}]")
                else:
                    log.warning("Empty playlist!")
                last_t = t; group_idx = 0; toggle = 0; group_start = time.time()

            if groups:
                group = groups[group_idx]
                img, label = group[toggle % len(group)]
                log.info(f"WP: {img.name}  [{label}]  G{group_idx+1}/{len(groups)}")
                set_wp(img)

                # 等待30秒后切换Q/Normal，期间每秒检查时段是否变化
                waited = 0
                while waited < TOGGLE_INTERVAL:
                    time.sleep(1); waited += 1
                    if waited % 60 == 0 and active() != t:
                        break

                # 时段没变才推进切换
                if active() == t:
                    toggle += 1
                    # 30分钟到 → 切换到下一组
                    if time.time() - group_start >= GROUP_INTERVAL:
                        group_idx = (group_idx + 1) % len(groups)
                        toggle = 0
                        group_start = time.time()
                        log.info(f">>> 切换组 → G{group_idx+1}")
            else:
                time.sleep(TOGGLE_INTERVAL)
    except KeyboardInterrupt:
        log.info("Stopped.")
    except Exception as e:
        log.error(f"Error: {e}"); log.error(traceback.format_exc())
    finally:
        release_lock(); log.info("Bye.")

if __name__=="__main__":
    main()
