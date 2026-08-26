#!/usr/bin/env python3
"""DeepSeek 余额小宠物 - a tiny desktop pet that shows DeepSeek balance."""

import os
import sys
import json
import threading
import urllib.request
import urllib.error
import tkinter as tk
from tkinter import messagebox

from PIL import Image, ImageDraw, ImageFont, ImageTk

# keep the pet crisp on high-DPI screens
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

PROJ = os.path.dirname(os.path.abspath(__file__))
CONF = os.path.join(PROJ, "config.json")
DEFAULTS = {"api_key": "", "poll_seconds": 60, "bubble_x": 120, "bubble_y": 154,
            "circles_x": 188, "circles_y": 290, "locked": False, "scale": 1.0}

# transparent key color (shows through as fully transparent on Windows)
TRANS = "#ff00ff"
NAVY = (47, 68, 92)
SLATE_LABEL = (150, 158, 168)
SLATE_AMOUNT = (167, 188, 208)
BUBBLE_W, BUBBLE_H = 320, 200


def load_config():
    cfg = dict(DEFAULTS)
    try:
        with open(CONF, "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    if not cfg.get("api_key"):
        cfg["api_key"] = os.environ.get("DEEPSEEK_API_KEY", "")
    return cfg


def save_config(cfg):
    with open(CONF, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def fetch_balance(api_key):
    """Return (is_ok: bool, display: str, raw_error: str)."""
    if not api_key:
        return False, "未配置 API Key\n右键设置", ""
    req = urllib.request.Request(
        "https://api.deepseek.com/user/balance",
        headers={"Authorization": "Bearer " + api_key, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.loads(r.read().decode("utf-8"))
        infos = data.get("balance_infos") or []
        if not infos:
            return True, "余额 0.00", ""
        info = infos[0]
        total = info.get("total_balance", "0.00")
        cur = info.get("currency", "CNY")
        sym = "\u00a5" if cur in ("CNY", "RMB", "") else cur + " "
        return True, f"{sym} {total}", ""
    except urllib.error.HTTPError as e:
        return False, "获取失败", f"HTTP {e.code}"
    except Exception as e:
        return False, "网络错误", str(e)


def build_bubble_pil(amount_text, label="DeepSeek 余额", scale=1.0):
    """Return a PIL RGBA image of a soft thought-bubble with current balance."""
    ss = 2.0
    W = int(BUBBLE_W * scale * ss)
    H = int(BUBBLE_H * scale * ss)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # ellipse (thought-cloud) geometry
    cx = W / 2
    cy = int(92 * scale * ss)
    rx = int(W / 2 - 18 * scale * ss)
    ry = int(80 * scale * ss)
    # layered outline: navy outer -> light bevel -> white core
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry],
              fill=(255, 255, 255, 255), outline=NAVY + (255,), width=int(9 * scale * ss))
    d.ellipse([cx - rx + 9 * scale * ss, cy - ry + 9 * scale * ss,
               cx + rx - 9 * scale * ss, cy + ry - 9 * scale * ss],
              outline=(176, 189, 202, 255), width=int(4 * scale * ss))

    # text
    def font(sz):
        return ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc", int(sz * scale * ss))

    line1 = label
    f1 = font(26)
    l1w = d.textlength(line1, font=f1)
    d.text(((W - l1w) / 2, cy - 34 * scale * ss), line1, font=f1, fill=SLATE_LABEL + (255,))

    lines = amount_text.split("\n")
    if len(lines) == 1:
        f_body = font(42)
        bw = d.textlength(lines[0], font=f_body)
        d.text(((W - bw) / 2, cy - 6 * scale * ss), lines[0], font=f_body, fill=SLATE_AMOUNT + (255,))
    else:
        f_body = font(27)
        y = cy - 10 * scale * ss
        for ln in lines:
            bw = d.textlength(ln, font=f_body)
            d.text(((W - bw) / 2, y), ln, font=f_body, fill=SLATE_AMOUNT + (255,))
            y += int(31 * scale * ss)

    img = img.resize((int(W / ss), int(H / ss)), Image.LANCZOS)
    # harden edge alpha so it never picks up the transparent window colour
    alpha = img.split()[3].point(lambda v: 255 if v > 110 else 0)
    img.putalpha(alpha)
    return img


def make_bubble(amount_text, label="DeepSeek 余额", scale=1.0):
    """Return an RGBA PhotoImage of the chat bubble with current balance."""
    return ImageTk.PhotoImage(build_bubble_pil(amount_text, label, scale))


def build_circles_pil(scale=1.0):
    """Return a PIL RGBA image of the two trailing thought-bubbles (movable)."""
    ss = 2.0
    W = H = int(160 * scale * ss)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for (x, y, r) in [(52, 60, 18), (100, 118, 10)]:
        d.ellipse([x*scale*ss - r*scale*ss, y*scale*ss - r*scale*ss,
                   x*scale*ss + r*scale*ss, y*scale*ss + r*scale*ss],
                  fill=(255, 255, 255, 255), outline=NAVY + (255,), width=int(7*scale*ss))
    img = img.resize((int(160 * scale), int(160 * scale)), Image.LANCZOS)
    alpha = img.split()[3].point(lambda v: 255 if v > 110 else 0)
    img.putalpha(alpha)
    return img


class BalancePet:
    def __init__(self, root):
        self.root = root
        self.cfg = load_config()
        self.poll = int(self.cfg.get("poll_seconds") or 60)
        self.state = "loading"
        self.display = "加载中…"

        # window
        self.scale = float(self.cfg.get("scale", 1.0))
        self.scale = min(max(self.scale, 0.5), 2.5)
        self.scale_var = tk.DoubleVar(value=self.scale)
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-transparentcolor", TRANS)
        root.configure(bg=TRANS)
        try:
            root.attributes("-toolwindow", True)
        except Exception:
            pass

        self.W = int(540 * self.scale)
        self.H = int(560 * self.scale)
        self.bubble_x = int(self.cfg.get("bubble_x", 120))
        self.bubble_y = int(self.cfg.get("bubble_y", 60))
        self.pet_x = int(285 * self.scale)
        self.pet_y = int(305 * self.scale)
        root.geometry(f"{self.W}x{self.H}+80+120")

        self.canvas = tk.Canvas(root, width=self.W, height=self.H, bg=TRANS,
                                highlightthickness=0, bd=0)
        self.canvas.pack()

        # load pet frames
        self.pet = ImageTk.PhotoImage(self._load("pet.png", self.scale))
        self.pw = self.pet.width()
        self.ph = self.pet.height()
        self.bubble = None
        self.circles = ImageTk.PhotoImage(build_circles_pil(self.scale))
        self.circles_cw = self.circles.width()
        self.circles_ch = self.circles.height()
        self.circles_x = int(self.cfg.get("circles_x", 188))
        self.circles_y = int(self.cfg.get("circles_y", 290))
        self.bubble_w = int(BUBBLE_W * self.scale)
        self.bubble_h = int(BUBBLE_H * self.scale)
        self.locked = bool(self.cfg.get("locked", False))

        self.id_pet = self.canvas.create_image(0, 0, anchor="nw", image=self.pet)
        self.id_bubble = self.canvas.create_image(0, 0, anchor="nw", image=self.bubble)
        self.id_circles = self.canvas.create_image(0, 0, anchor="nw", image=self.circles)
        self._place()

        # events
        self._drag_mode = None
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.canvas.bind("<Button-3>", self._menu)

        self._refresh_async()
        self.root.after(int(self.poll * 1000), self._schedule_poll)

    def _load(self, name, scale=1.0):
        im = Image.open(os.path.join(PROJ, name)).convert("RGBA")
        tgt = int(240 * scale)
        tw = tgt if im.width > im.height else int(tgt * im.width / im.height)
        im = im.resize((tw, int(im.height * tw / im.width)), Image.LANCZOS)
        # crisp opaque edge so it looks clean on any desktop background
        alpha = im.split()[3].point(lambda a: 255 if a > 120 else 0)
        im.putalpha(alpha)
        return im

    def _place(self):
        self.canvas.coords(self.id_pet, self.pet_x, self.pet_y)
        if self.bubble:
            self.canvas.coords(self.id_bubble, self.bubble_x, self.bubble_y)
        self.canvas.coords(self.id_circles, self.circles_x, self.circles_y)

    def _press(self, e):
        if self.locked:
            self._drag_mode = "window"
            self._dx = e.x_root - self.root.winfo_x()
            self._dy = e.y_root - self.root.winfo_y()
            return
        item = self.canvas.find_withtag("current")
        if self.bubble and item and item[0] == self.id_bubble:
            self._drag_mode = "bubble"
            self._dx = e.x - self.bubble_x
            self._dy = e.y - self.bubble_y
        elif item and item[0] == self.id_circles:
            self._drag_mode = "circles"
            self._dx = e.x - self.circles_x
            self._dy = e.y - self.circles_y
        else:
            self._drag_mode = "window"
            self._dx = e.x_root - self.root.winfo_x()
            self._dy = e.y_root - self.root.winfo_y()

    def _drag(self, e):
        if self._drag_mode == "bubble":
            x = min(max(e.x - self._dx, 0), max(0, self.W - self.bubble_w))
            y = min(max(e.y - self._dy, 0), max(0, self.H - self.bubble_h))
            self.bubble_x, self.bubble_y = int(x), int(y)
            self.canvas.coords(self.id_bubble, self.bubble_x, self.bubble_y)
        elif self._drag_mode == "circles":
            x = min(max(e.x - self._dx, 0), max(0, self.W - self.circles_cw))
            y = min(max(e.y - self._dy, 0), max(0, self.H - self.circles_ch))
            self.circles_x, self.circles_y = int(x), int(y)
            self.canvas.coords(self.id_circles, self.circles_x, self.circles_y)
        elif self._drag_mode == "window":
            self.root.geometry(f"+{e.x_root - self._dx}+{e.y_root - self._dy}")

    def _release(self, e):
        if self._drag_mode == "bubble":
            self.cfg["bubble_x"] = self.bubble_x
            self.cfg["bubble_y"] = self.bubble_y
            save_config(self.cfg)
        elif self._drag_mode == "circles":
            self.cfg["circles_x"] = self.circles_x
            self.cfg["circles_y"] = self.circles_y
            save_config(self.cfg)
        self._drag_mode = None

    def _menu(self, e):
        m = tk.Menu(self.root, tearoff=0)
        m.add_command(label="刷新余额", command=self._refresh_async)
        m.add_command(label="隐藏气泡与圆点" if self.state != "hidden" else "显示气泡与圆点",
                      command=self._toggle_bubble)
        m.add_separator()
        size = tk.Menu(m, tearoff=0)
        for label, val in (("缩小 (0.8x)", 0.8),
                           ("标准 (1.0x)", 1.0),
                           ("放大 (1.2x)", 1.2),
                           ("更大 (1.5x)", 1.5),
                           ("超大 (2.0x)", 2.0)):
            size.add_radiobutton(label=label, variable=self.scale_var, value=val,
                                 command=self._on_scale)
        m.add_cascade(label="调整大小", menu=size)
        m.add_separator()
        m.add_command(label="设置 API Key…", command=self._set_key)
        m.add_command(label="解锁调整" if self.locked else "锁定位置", command=self._toggle_lock)
        m.add_command(label="重置位置", command=self._reset_bubble)
        m.add_command(label="退出", command=self.root.destroy)
        m.tk_popup(e.x_root, e.y_root)

    def _on_scale(self):
        self._set_scale(float(self.scale_var.get()))

    def _set_scale(self, new):
        new = min(max(float(new), 0.5), 2.5)
        if abs(new - self.scale) < 1e-9:
            return
        ratio = new / self.scale
        self.bubble_x = int(round(self.bubble_x * ratio))
        self.bubble_y = int(round(self.bubble_y * ratio))
        self.circles_x = int(round(self.circles_x * ratio))
        self.circles_y = int(round(self.circles_y * ratio))
        self.pet_x = int(round(self.pet_x * ratio))
        self.pet_y = int(round(self.pet_y * ratio))
        self.scale = new
        self.scale_var.set(new)
        self.W = int(540 * new)
        self.H = int(560 * new)
        self.bubble_w = int(BUBBLE_W * new)
        self.bubble_h = int(BUBBLE_H * new)
        try:
            px, py = self.root.winfo_x(), self.root.winfo_y()
        except Exception:
            px, py = 80, 120
        self.root.geometry(f"{self.W}x{self.H}+{px}+{py}")
        self.canvas.config(width=self.W, height=self.H)
        self.pet = ImageTk.PhotoImage(self._load("pet.png", new))
        self.pw = self.pet.width()
        self.ph = self.pet.height()
        self.circles = ImageTk.PhotoImage(build_circles_pil(new))
        self.circles_cw = self.circles.width()
        self.circles_ch = self.circles.height()
        self.canvas.itemconfigure(self.id_pet, image=self.pet)
        self.canvas.itemconfigure(self.id_circles, image=self.circles)
        if self.bubble:
            self.bubble = make_bubble(self.display, scale=new)
            self.canvas.itemconfigure(self.id_bubble, image=self.bubble)
        self._place()
        self.cfg["scale"] = new
        self.cfg["bubble_x"] = self.bubble_x
        self.cfg["bubble_y"] = self.bubble_y
        self.cfg["circles_x"] = self.circles_x
        self.cfg["circles_y"] = self.circles_y
        save_config(self.cfg)

    def _toggle_lock(self):
        self.locked = not self.locked
        self.cfg["locked"] = self.locked
        save_config(self.cfg)

    def _reset_bubble(self):
        self.bubble_x = int(DEFAULTS["bubble_x"] * self.scale)
        self.bubble_y = int(DEFAULTS["bubble_y"] * self.scale)
        self.circles_x = int(DEFAULTS["circles_x"] * self.scale)
        self.circles_y = int(DEFAULTS["circles_y"] * self.scale)
        self.cfg["bubble_x"] = self.bubble_x
        self.cfg["bubble_y"] = self.bubble_y
        self.cfg["circles_x"] = self.circles_x
        self.cfg["circles_y"] = self.circles_y
        save_config(self.cfg)
        self.canvas.coords(self.id_bubble, self.bubble_x, self.bubble_y)
        self.canvas.coords(self.id_circles, self.circles_x, self.circles_y)

    def _toggle_bubble(self):
        if self.state == "hidden":
            self.state = "shown"
            self.canvas.itemconfigure(self.id_bubble, state="normal")
            self.canvas.itemconfigure(self.id_circles, state="normal")
        else:
            self.state = "hidden"
            self.canvas.itemconfigure(self.id_bubble, state="hidden")
            self.canvas.itemconfigure(self.id_circles, state="hidden")

    def _set_key(self):
        import tkinter.simpledialog as sd
        key = sd.askstring("设置 DeepSeek API Key",
                           "粘贴你的 DeepSeek API Key（sk-…）：",
                           initialvalue=self.cfg.get("api_key", ""), show="*")
        if key is not None:
            key = key.strip()
            self.cfg["api_key"] = key
            save_config(self.cfg)
            self._refresh_async()

    def _schedule_poll(self):
        self._refresh_async()
        self.root.after(int(self.poll * 1000), self._schedule_poll)

    def _refresh_async(self):
        key = self.cfg.get("api_key", "")
        threading.Thread(target=self._worker, args=(key,), daemon=True).start()

    def _worker(self, key):
        ok, display, err = fetch_balance(key)
        self.root.after(0, self._apply_result, ok, display, err)

    def _apply_result(self, ok, display, err):
        self.display = display
        self.bubble = make_bubble(display, scale=self.scale)
        self.canvas.itemconfigure(self.id_bubble, image=self.bubble)
        self._place()


def main():
    root = tk.Tk()
    BalancePet(root)
    root.mainloop()


if __name__ == "__main__":
    main()
