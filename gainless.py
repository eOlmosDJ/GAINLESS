import os

import sys

import re

import math

import json

import shutil

import subprocess

import threading

import queue

from datetime import datetime

from pathlib import Path

import tkinter as tk

from tkinter import filedialog, messagebox



from mutagen import File as MutagenFile

from mutagen.id3 import ID3, ID3NoHeaderError

from mutagen.flac import FLAC

from mutagen.wave import WAVE

from mutagen.aiff import AIFF

from mutagen.mp4 import MP4



SUPPORTED_EXTS = {'.mp3', '.flac', '.wav', '.aiff', '.aif', '.m4a', '.mp4', '.ogg', '.opus', '.aac', '.wma'}

WIN_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0



BG_CHASSIS = "#08090B"

BG_PANEL = "#0B0C0E"

BG_SCREEN_INTERIOR = "#22252C"

BORDER_SUBTLE = "#1C1E24"

TEXT_WHITE = "#F4F6F8"

TEXT_SILVER = "#B0B5C0"

TEXT_DIM = "#686D78"

FONT_MAIN = "Arial"





def resource_path(relative_path):

    """Obtiene la ruta del recurso tanto en desarrollo como dentro del .exe de PyInstaller."""

    if hasattr(sys, "_MEIPASS"):

        return os.path.join(sys._MEIPASS, relative_path)

    return os.path.join(os.path.abspath("."), relative_path)





def set_windows_app_id():

    """Asigna un AppUserModelID único para que Windows muestre el logo de GAINLESS en la barra de tareas."""

    if os.name == "nt":

        try:

            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("gainless.audio.normalizer.v1")

        except Exception:

            pass





def apply_dark_titlebar(window):

    """Fuerza el marco y la barra de título de Windows a color negro/oscuro."""

    if os.name != "nt":

        return

    try:

        import ctypes

        window.update_idletasks()

        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())

        if not hwnd:

            hwnd = window.winfo_id()

        dark_mode = ctypes.c_int(1)

        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark_mode), ctypes.sizeof(dark_mode))

        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(dark_mode), ctypes.sizeof(dark_mode))

        caption_col = ctypes.c_int(0x000B0908)

        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(caption_col), ctypes.sizeof(caption_col))

        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(caption_col), ctypes.sizeof(caption_col))

    except Exception:

        pass





def interpolate_hex(c1, c2, t):

    t = max(0.0, min(1.0, t))

    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)

    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)

    r = int(r1 + (r2 - r1) * t)

    g = int(g1 + (g2 - g1) * t)

    b = int(b1 + (b2 - b1) * t)

    return f"#{r:02x}{g:02x}{b:02x}"





class HeaderGainlessLogo(tk.Canvas):

    """Mini logo vectorial de GAINLESS (Knob gris + letra G + puntero en 0dB) para la barra superior."""

    def __init__(self, parent, size=28):

        super().__init__(parent, width=size, height=size, bg="#050507", highlightthickness=0)

        self.s = size

        self._draw()



    def _draw(self):

        cx, cy = self.s / 2, self.s / 2

        r_g = self.s * 0.40

        r_knob = self.s * 0.25

        # Arco exterior blanco formando la G

        self.create_arc(

            cx - r_g, cy - r_g, cx + r_g, cy + r_g,

            start=42, extent=295, style=tk.ARC, outline="#F4F6F8", width=2.2

        )

        # Patita vertical derecha de la G

        self.create_line(cx + r_g, cy, cx + r_g, cy + r_g * 0.48, fill="#F4F6F8", width=2.2, capstyle=tk.ROUND)

        # Cuerpo gris del knob central

        self.create_oval(cx - r_knob, cy - r_knob, cx + r_knob, cy + r_knob, fill="#6A6E78", outline="#9499A3", width=1)

        # Línea blanca horizontal del knob que forma el travesaño de la G apuntando a 0dB

        self.create_line(cx, cy, cx + r_g, cy, fill="#FFFFFF", width=2.2, capstyle=tk.ROUND)

        # Punto verde-lima de 0dB a la derecha

        self.create_oval(cx + r_g + 1.5, cy - 1.5, cx + r_g + 4.5, cy + 1.5, fill="#CBE600", outline="")





class DarkScrollbar(tk.Canvas):

    """Barra de desplazamiento 100% oscura."""

    def __init__(self, parent, command, width=14):

        super().__init__(parent, width=width, bg="#0A0B0E", highlightthickness=1, highlightbackground="#1C1E24")

        self.command = command

        self.w = width

        self.lo = 0.0

        self.hi = 1.0

        self.hovered = False

        self.dragging = False

        self.drag_start_y = 0

        self.drag_start_lo = 0.0



        self.bind("<Configure>", lambda e: self._draw())

        self.bind("<Enter>", lambda e: self._set_hover(True))

        self.bind("<Leave>", lambda e: self._set_hover(False))

        self.bind("<ButtonPress-1>", self._on_press)

        self.bind("<B1-Motion>", self._on_drag)

        self.bind("<ButtonRelease-1>", self._on_release)



    def set(self, lo, hi):

        self.lo = max(0.0, min(1.0, float(lo)))

        self.hi = max(0.0, min(1.0, float(hi)))

        self._draw()



    def _set_hover(self, val):

        self.hovered = val

        self._draw()



    def _on_press(self, event):

        h = max(1, self.winfo_height())

        y1 = self.lo * h

        y2 = self.hi * h

        if y1 <= event.y <= y2:

            self.dragging = True

            self.drag_start_y = event.y

            self.drag_start_lo = self.lo

        else:

            span = self.hi - self.lo

            target_lo = max(0.0, min(1.0 - span, (event.y / h) - span / 2))

            if self.command:

                self.command("moveto", target_lo)

        self._draw()



    def _on_drag(self, event):

        if not self.dragging:

            return

        h = max(1, self.winfo_height())

        span = self.hi - self.lo

        if span >= 1.0:

            return

        dy_ratio = (event.y - self.drag_start_y) / h

        new_lo = max(0.0, min(1.0 - span, self.drag_start_lo + dy_ratio))

        if self.command:

            self.command("moveto", new_lo)



    def _on_release(self, _event):

        self.dragging = False

        self._draw()



    def _draw(self):

        self.delete("all")

        h = max(20, self.winfo_height())

        w = self.w

        self.create_rectangle(0, 0, w, h, fill="#0A0B0E", outline="")



        y1 = max(3, int(self.lo * h) + 2)

        y2 = min(h - 3, max(y1 + 24, int(self.hi * h) - 2))



        thumb_col = "#505666" if (self.dragging or self.hovered) else "#2E323C"

        cx = w / 2

        self.create_line(cx, y1 + 4, cx, y2 - 4, width=w - 6, fill=thumb_col, capstyle=tk.ROUND)





class HardwareRotaryKnob(tk.Canvas):

    """Potenciómetro realista con aro blanco (TARGET LUFS) o gris (TOLERANCE) y rueda superior dentada."""

    def __init__(self, parent, label_text, min_val, max_val, init_val, step=0.5,

                 left_range_text="-18", right_range_text="-6", knob_style="eq", size=110, on_change=None):

        super().__init__(parent, width=size, height=size + 38, bg=BG_PANEL, highlightthickness=0, cursor="sb_v_double_arrow")

        self.label_text = label_text

        self.min_val = min_val

        self.max_val = max_val

        self.val = init_val

        self.default_val = init_val

        self.step = step

        self.left_range_text = left_range_text

        self.right_range_text = right_range_text

        self.knob_style = knob_style

        self.size = size

        self.on_change = on_change

        self._drag_y = None



        self.bind("<ButtonPress-1>", self._on_press)

        self.bind("<B1-Motion>", self._on_drag)

        self.bind("<MouseWheel>", self._on_wheel)

        self.bind("<Double-Button-1>", self._reset_default)

        self._draw()



    def get(self):

        return self.val



    def set(self, new_val):

        clamped = max(self.min_val, min(self.max_val, new_val))

        steps = round((clamped - self.min_val) / self.step)

        self.val = round(self.min_val + steps * self.step, 2)

        self._draw()

        if self.on_change:

            self.on_change(self.val)



    def _reset_default(self, _event=None):

        self.set(self.default_val)



    def _on_press(self, event):

        self._drag_y = event.y



    def _on_drag(self, event):

        if self._drag_y is None:

            return

        dy = self._drag_y - event.y

        if abs(dy) >= 3:

            delta = (dy // 3) * self.step

            self.set(self.val + delta)

            self._drag_y = event.y



    def _on_wheel(self, event):

        direction = 1 if event.delta > 0 else -1

        self.set(self.val + direction * self.step)



    def _val_to_angle(self, v):

        norm = (v - self.min_val) / (self.max_val - self.min_val)

        return 215.0 - norm * 250.0



    def _draw(self):

        self.delete("all")

        cx = self.size / 2

        cy = self.size / 2 + 12



        r_dots = self.size * 0.39

        r_black_base = self.size * 0.33

        r_ring = self.size * 0.31

        r_skirt = self.size * 0.255

        r_teeth = self.size * 0.225

        r_top_inner = self.size * 0.185



        self.create_text(cx, 10, text=self.label_text, fill=TEXT_WHITE, font=(FONT_MAIN, 8, "bold"))



        total_marks = 11

        for i in range(total_marks):

            ang_deg = 215.0 - (i / (total_marks - 1)) * 250.0

            rad = math.radians(ang_deg)



            if i == total_marks // 2:

                x1, y1 = cx + (r_ring + 1) * math.cos(rad), cy - (r_ring + 1) * math.sin(rad)

                x2, y2 = cx + (r_dots + 4) * math.cos(rad), cy - (r_dots + 4) * math.sin(rad)

                self.create_line(x1, y1, x2, y2, fill="#FFFFFF", width=2)

            elif i in (0, total_marks - 1):

                x1, y1 = cx + (r_ring + 1) * math.cos(rad), cy - (r_ring + 1) * math.sin(rad)

                x2, y2 = cx + (r_dots + 5) * math.cos(rad), cy - (r_dots + 5) * math.sin(rad)

                self.create_line(x1, y1, x2, y2, fill="#FFFFFF", width=2)

            else:

                dx = cx + r_dots * math.cos(rad)

                dy = cy - r_dots * math.sin(rad)

                self.create_oval(dx - 1.6, dy - 1.6, dx + 1.6, dy + 1.6, fill="#FFFFFF", outline="")



        self.create_text(cx - r_dots * 0.72, cy + r_dots * 0.85, text=self.left_range_text, fill=TEXT_WHITE, font=(FONT_MAIN, 8, "bold"))

        self.create_text(cx + r_dots * 0.72, cy + r_dots * 0.85, text=self.right_range_text, fill=TEXT_WHITE, font=(FONT_MAIN, 8, "bold"))



        self.create_oval(

            cx - r_black_base, cy - r_black_base, cx + r_black_base, cy + r_black_base,

            fill="#040405", outline="#16181C", width=1

        )



        if self.knob_style == "eq":

            self.create_oval(cx - r_ring, cy - r_ring, cx + r_ring, cy + r_ring, fill="#D0D3D8", outline="#FFFFFF", width=1)

            self.create_oval(cx - r_ring + 2, cy - r_ring + 2, cx + r_ring - 2, cy + r_ring - 2, fill="#ECEEF2", outline="")

            self.create_oval(cx - r_skirt, cy - r_skirt, cx + r_skirt, cy + r_skirt, fill="#151619", outline="#2C2E34", width=1.5)

            tooth_fill = "#2B2D33"

            tooth_outline = "#3C3F47"

            cap_fill = "#1C1D21"

        else:

            self.create_oval(cx - r_ring, cy - r_ring, cx + r_ring, cy + r_ring, fill="#404246", outline="#2A2C30", width=1)

            self.create_oval(cx - r_skirt, cy - r_skirt, cx + r_skirt, cy + r_skirt, fill="#56585E", outline="#686B72", width=1.5)

            tooth_fill = "#6A6D74"

            tooth_outline = "#858890"

            cap_fill = "#787B82"



        knob_angle_deg = self._val_to_angle(self.val)

        knob_angle_rad = math.radians(knob_angle_deg)

        poly_points = []

        num_teeth = 10

        steps_poly = 90

        for s in range(steps_poly):

            theta = (2 * math.pi * s) / steps_poly

            r_mod = r_teeth + 1.6 * math.cos(num_teeth * (theta - knob_angle_rad))

            px = cx + r_mod * math.cos(theta)

            py = cy - r_mod * math.sin(theta)

            poly_points.extend([px, py])



        self.create_polygon(poly_points, fill=tooth_fill, outline=tooth_outline, width=1.2, smooth=True)

        self.create_oval(

            cx - r_top_inner, cy - r_top_inner, cx + r_top_inner, cy + r_top_inner,

            fill=cap_fill, outline=tooth_outline, width=1

        )



        x_tip_outer = cx + (r_skirt - 1) * math.cos(knob_angle_rad)

        y_tip_outer = cy - (r_skirt - 1) * math.sin(knob_angle_rad)

        x_tip_white = cx + (r_teeth - 1) * math.cos(knob_angle_rad)

        y_tip_white = cy - (r_teeth - 1) * math.sin(knob_angle_rad)



        self.create_line(cx, cy, x_tip_outer, y_tip_outer, fill="#9A9EA6", width=3.8, capstyle=tk.ROUND)

        self.create_line(cx, cy, x_tip_white, y_tip_white, fill="#FFFFFF", width=3.0, capstyle=tk.ROUND)



        unit_txt = "LUFS" if self.knob_style == "eq" else "dB"

        self.create_text(

            cx, self.size + 25,

            text=f"{self.val:.1f} {unit_txt}",

            fill="#00E5FF" if self.knob_style == "eq" else "#D0D4DC",

            font=(FONT_MAIN, 9, "bold")

        )





class InputFolderSelectorKnob(tk.Canvas):

    """Perilla selectora rotativa SOURCE (STAND BY / FOLDER / TRACK)."""

    def __init__(self, parent, on_select_folder, on_select_files):

        super().__init__(parent, width=190, height=148, bg=BG_PANEL, highlightthickness=0, cursor="hand2")

        self.on_select_folder = on_select_folder

        self.on_select_files = on_select_files

        self.mode = "IDLE"

        self.source_label = "STAND BY"

        self.bind("<Button-1>", self._on_click)

        self._draw()



    def set_source(self, mode, label_text):

        self.mode = mode

        clean = label_text.strip()

        if len(clean) > 20:

            clean = "..." + clean[-17:]

        self.source_label = clean

        self._draw()



    def _on_click(self, event):

        if event.x > 120:

            self.on_select_files()

        else:

            self.on_select_folder()



    def _draw(self):

        self.delete("all")

        cx, cy = 95, 74

        r_knob = 25



        self.create_text(95, 11, text="SOURCE", fill=TEXT_WHITE, font=(FONT_MAIN, 9, "bold"))



        positions = [

            ("STAND BY", 150, "IDLE"),

            ("FOLDER", 90, "FOLDER"),

            ("TRACK", 30, "FILES"),

        ]



        for label, ang_deg, code in positions:

            rad = math.radians(ang_deg)

            tx = cx + (r_knob + 11) * math.cos(rad)

            ty = cy - (r_knob + 11) * math.sin(rad)

            lx = cx + (r_knob + 25) * math.cos(rad)

            ly = cy - (r_knob + 20) * math.sin(rad)

            active = (self.mode == code)

            self.create_line(

                cx + (r_knob + 3) * math.cos(rad), cy - (r_knob + 3) * math.sin(rad),

                tx, ty, fill="#FFFFFF" if active else TEXT_DIM, width=2

            )

            self.create_text(

                lx, ly, text=label,

                fill="#FFFFFF" if active else TEXT_DIM,

                font=(FONT_MAIN, 7, "bold")

            )



        self.create_oval(cx - r_knob - 4, cy - r_knob - 4, cx + r_knob + 4, cy + r_knob + 4, fill="#040405", outline="#22242A")

        self.create_oval(cx - r_knob, cy - r_knob, cx + r_knob, cy + r_knob, fill="#1B1C20", outline="#484B54", width=1.5)



        angle_map = {"IDLE": 150, "FOLDER": 90, "FILES": 30}

        ang_rad = math.radians(angle_map.get(self.mode, 150))

        perp_rad = ang_rad + math.pi / 2



        w = 5.0

        x_tip = cx + (r_knob - 2) * math.cos(ang_rad)

        y_tip = cy - (r_knob - 2) * math.sin(ang_rad)

        x_tail = cx - (r_knob - 5) * math.cos(ang_rad)

        y_tail = cy + (r_knob - 5) * math.sin(ang_rad)



        poly = [

            x_tip + w * math.cos(perp_rad), y_tip - w * math.sin(perp_rad),

            x_tip - w * math.cos(perp_rad), y_tip + w * math.sin(perp_rad),

            x_tail - w * math.cos(perp_rad), y_tail + w * math.sin(perp_rad),

            x_tail + w * math.cos(perp_rad), y_tail - w * math.sin(perp_rad),

        ]

        self.create_polygon(poly, fill="#2E3038", outline="#686C78")

        self.create_line(cx, cy, x_tip, y_tip, fill="#FFFFFF", width=2.6, capstyle=tk.ROUND)



        self.create_rectangle(8, 114, 182, 140, fill="#16181D", outline="#2E323B")

        color = "#FFFFFF" if self.mode != "IDLE" else TEXT_DIM

        self.create_text(95, 127, text=self.source_label, fill=color, font=(FONT_MAIN, 8, "bold"))





class BacklitRubberButtonsPanel(tk.Canvas):

    """Panel puntilleado TOOLS con 6 botones de goma translúcida iluminada."""

    def __init__(self, parent, buttons_spec, width=326, height=148):

        super().__init__(parent, width=width, height=height, bg="#38393D", highlightthickness=1, highlightbackground="#52545A")

        self.w = width

        self.h = height

        self.buttons_spec = buttons_spec

        self.btn_rects = []

        self.hovered_idx = None

        self.pressed_idx = None



        self.bind("<Motion>", self._on_motion)

        self.bind("<Leave>", self._on_leave)

        self.bind("<ButtonPress-1>", self._on_press)

        self.bind("<ButtonRelease-1>", self._on_release)

        self._draw()



    def _draw_rounded_rect(self, x1, y1, x2, y2, r, **kwargs):

        points = [

            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,

            x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,

            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1

        ]

        return self.create_polygon(points, smooth=True, **kwargs)



    def _draw(self):

        self.delete("all")

        self.create_rectangle(0, 0, self.w, self.h, fill="#35363A", outline="")

        dot_spacing = 6

        for y in range(6, self.h - 4, dot_spacing):

            for x in range(6, self.w - 4, dot_spacing):

                self.create_rectangle(x, y, x + 1, y + 1, fill="#6C6E74", outline="")



        self.create_text(

            self.w / 2, self.h / 2,

            text="TOOLS",

            fill="#EAECEF", font=(FONT_MAIN, 10, "bold")

        )



        bw, bh = 88, 43

        col_xs = [14, 119, 224]

        row_ys = [12, 93]

        self.btn_rects.clear()



        for idx, (label, _cmd) in enumerate(self.buttons_spec):

            col = idx % 3

            row = idx // 3

            x1 = col_xs[col]

            y1 = row_ys[row]

            x2 = x1 + bw

            y2 = y1 + bh

            self.btn_rects.append((x1, y1, x2, y2))



            is_hover = (self.hovered_idx == idx)

            is_press = (self.pressed_idx == idx)



            self._draw_rounded_rect(x1 - 2, y1 - 2, x2 + 2, y2 + 2, r=8, fill="#141518", outline="#23252A")



            if is_press:

                layers = ["#707278", "#90949A", "#B4B8BE", "#D2D6DC", "#E4E8EE"]

            elif is_hover:

                layers = ["#9A9EA6", "#BEC2CA", "#DEE2E8", "#F4F6FA", "#FFFFFF"]

            else:

                layers = ["#7C7E84", "#9FA2A8", "#C2C5CC", "#E0E3E8", "#F4F6F9"]



            for step_i, col_hex in enumerate(layers):

                inset = step_i * 1.25

                self._draw_rounded_rect(

                    x1 + inset, y1 + inset, x2 - inset, y2 - inset,

                    r=max(3, 7 - step_i), fill=col_hex, outline=""

                )



            cx1, cy1, cx2, cy2 = x1 + 7, y1 + 7, x2 - 7, y2 - 7

            self.create_rectangle(cx1, cy1, cx2, cy2, fill="#1B1C20", outline="#484B52", width=1)



            if "\n" in label:

                lines = label.split("\n")

                self.create_text((cx1 + cx2) / 2, (cy1 + cy2) / 2 - 5, text=lines[0], fill="#FFFFFF", font=(FONT_MAIN, 7, "bold"))

                self.create_text((cx1 + cx2) / 2, (cy1 + cy2) / 2 + 5, text=lines[1], fill="#FFFFFF", font=(FONT_MAIN, 7, "bold"))

            else:

                self.create_text((cx1 + cx2) / 2, (cy1 + cy2) / 2, text=label, fill="#FFFFFF", font=(FONT_MAIN, 7, "bold"))



    def _hit_test(self, x, y):

        for idx, (x1, y1, x2, y2) in enumerate(self.btn_rects):

            if x1 <= x <= x2 and y1 <= y <= y2:

                return idx

        return None



    def _on_motion(self, event):

        idx = self._hit_test(event.x, event.y)

        if idx != self.hovered_idx:

            self.hovered_idx = idx

            self.configure(cursor="hand2" if idx is not None else "")

            self._draw()



    def _on_leave(self, _event):

        self.hovered_idx = None

        self.pressed_idx = None

        self.configure(cursor="")

        self._draw()



    def _on_press(self, event):

        idx = self._hit_test(event.x, event.y)

        if idx is not None:

            self.pressed_idx = idx

            self._draw()



    def _on_release(self, event):

        idx = self._hit_test(event.x, event.y)

        was_pressed = self.pressed_idx

        self.pressed_idx = None

        self._draw()

        if was_pressed is not None and idx == was_pressed:

            _label, cmd = self.buttons_spec[idx]

            if cmd:

                cmd()





class BacklitOrangeAnalyzeButton(tk.Canvas):

    """Botón naranja retroiluminado para ANALYZE."""

    def __init__(self, parent, command, width=124, height=54):

        super().__init__(parent, width=width, height=height, bg=BG_PANEL, highlightthickness=0, cursor="hand2")

        self.command = command

        self.w = width

        self.h = height

        self.active = False

        self.hovered = False

        self.enabled = True



        self.bind("<Enter>", lambda e: self._hover(True))

        self.bind("<Leave>", lambda e: self._hover(False))

        self.bind("<Button-1>", self._click)

        self._draw()



    def set_active(self, active):

        self.active = active

        self._draw()



    def set_enabled(self, enabled):

        self.enabled = enabled

        self._draw()



    def _hover(self, val):

        self.hovered = val

        self._draw()



    def _click(self, _event):

        if self.enabled and self.command:

            self.command()



    def _draw(self):

        self.delete("all")

        self.create_rectangle(2, 2, self.w - 2, self.h - 2, fill="#040405", outline="#24262C", width=1.5)



        if not self.enabled and not self.active:

            outer_c, mid_c, core_c = "#5E2B06", "#7A3B0C", "#944A12"

        elif self.active or self.hovered:

            outer_c, mid_c, core_c = "#E85D00", "#FF851B", "#FFC470"

        else:

            outer_c, mid_c, core_c = "#C84B00", "#F06A00", "#FFA040"



        self.create_rectangle(6, 6, self.w - 6, self.h - 6, fill=outer_c, outline="#FFA94D", width=1.5)

        self.create_rectangle(10, 10, self.w - 10, self.h - 10, fill=mid_c, outline="")

        self.create_rectangle(16, 13, self.w - 16, self.h - 13, fill=core_c, outline="")



        self.create_text(self.w / 2, 21, text="ANALYZE", fill="#1A0900", font=(FONT_MAIN, 10, "bold"))

        self.create_text(self.w / 2, 36, text="FILTER LIBRARY", fill="#260E00", font=(FONT_MAIN, 7, "bold"))





class BlueGradientNormalizeButton(tk.Canvas):

    """Botón circular azul con domo en gradiente suave para NORMALIZE."""

    def __init__(self, parent, command, size=88):

        super().__init__(parent, width=size + 20, height=size + 28, bg=BG_PANEL, highlightthickness=0, cursor="hand2")

        self.command = command

        self.size = size

        self.blinking = False

        self.blink_phase = False

        self.hovered = False

        self.enabled = True



        self.bind("<Enter>", lambda e: self._hover(True))

        self.bind("<Leave>", lambda e: self._hover(False))

        self.bind("<Button-1>", self._click)

        self._draw()



    def set_blinking(self, blinking):

        self.blinking = blinking

        self.blink_phase = True

        self._draw()



    def toggle_blink_phase(self):

        if self.blinking:

            self.blink_phase = not self.blink_phase

            self._draw()



    def set_enabled(self, enabled):

        self.enabled = enabled

        self._draw()



    def _hover(self, val):

        self.hovered = val

        self._draw()



    def _click(self, _event):

        if self.enabled and self.command:

            self.command()



    def _draw(self):

        self.delete("all")

        cx = (self.size + 20) / 2

        cy = (self.size + 28) / 2 + 8

        r_housing = self.size * 0.45

        r_blue_rim = self.size * 0.40

        r_dome = self.size * 0.33



        self.create_text(cx, 11, text="NORMALIZE", fill="#FFFFFF", font=(FONT_MAIN, 9, "bold"))



        self.create_oval(

            cx - r_housing - 2, cy - r_housing - 2, cx + r_housing + 2, cy + r_housing + 2,

            fill="#020203", outline="#1E2026", width=1.5

        )

        self.create_arc(

            cx - r_housing, cy - r_housing, cx + r_housing, cy + r_housing,

            start=-55, extent=110, style=tk.ARC, outline="#686E7A", width=2

        )



        is_lit = (self.blinking and self.blink_phase) or (not self.blinking and self.enabled)

        if not self.enabled and not self.blinking:

            rim_col = "#06153D"

            edge_dome = "#0A225E"

            center_dome = "#2E62A6"

        elif self.blinking and not self.blink_phase:

            rim_col = "#051336"

            edge_dome = "#091E54"

            center_dome = "#1C4987"

        elif self.hovered or (self.blinking and self.blink_phase):

            rim_col = "#0B2B80"

            edge_dome = "#1656C8"

            center_dome = "#BCE6FF"

        else:

            rim_col = "#09236B"

            edge_dome = "#1248B0"

            center_dome = "#9ED8FF"



        self.create_oval(

            cx - r_blue_rim, cy - r_blue_rim, cx + r_blue_rim, cy + r_blue_rim,

            fill=rim_col, outline="#041030", width=1.5

        )



        steps = 24

        for i in range(steps):

            t = i / (steps - 1)

            r_curr = r_dome * (1.0 - t * 0.88)

            col = interpolate_hex(edge_dome, center_dome, t ** 0.85)

            ox = -1.4 * t

            oy = -1.4 * t

            self.create_oval(

                cx + ox - r_curr, cy + oy - r_curr,

                cx + ox + r_curr, cy + oy + r_curr,

                fill=col, outline=""

            )



        if is_lit:

            r_ref = r_dome * 0.78

            self.create_arc(

                cx - r_ref, cy - r_ref, cx + r_ref, cy + r_ref,

                start=100, extent=85, style=tk.ARC, outline="#C8ECFF", width=1.5

            )





class StatusScreenAndHighResWaveform(tk.Canvas):

    """Pantalla con interior gris oscuro (#22252C) sobre chasis negro y onda RGB de alta densidad."""

    def __init__(self, parent, height=132):

        super().__init__(parent, height=height, bg=BG_CHASSIS, highlightthickness=0)

        self.mode_title = "STAND BY"

        self.track_text = "Select 'LOAD FOLDER' or 'LOAD TRACK' to begin"

        self.lufs_readout = "-12.0"

        self.db_count = 0



        self.target_progress = 0.0

        self.display_progress = 0.0

        self.active_ceiling = 0.0



        self.wave_bars = self._generate_detailed_waveform(420)

        self.bind("<Configure>", lambda e: self._draw())



    def _generate_detailed_waveform(self, n):

        bars = []

        for i in range(n):

            pos = i / n

            beat_pulse = abs(math.sin(i * 0.55)) * (0.65 + 0.35 * math.cos(i * 0.17))

            micro_transient = 0.25 if (i % 4 == 0) else (0.08 if (i % 2 == 0) else 0.18)



            if pos < 0.09 or pos > 0.92:

                amp = (0.18 + 0.32 * beat_pulse) * micro_transient * 2.4

                col = "#3698FF" if i % 2 == 0 else "#7B68EE"

            elif 0.24 <= pos <= 0.33 or 0.60 <= pos <= 0.69:

                amp = 0.15 + 0.42 * abs(math.sin(i * 0.38))

                if pos > 0.60:

                    col = "#38F28E" if i % 3 != 0 else "#22C8E5"

                else:

                    col = "#4DA6FF" if i % 2 == 0 else "#B8A9FF"

            else:

                valley = 0.22 if (i % 5 == 0) else 1.0

                amp = (0.35 + 0.62 * beat_pulse) * valley

                if amp > 0.72:

                    col = "#FF4B2B" if (i % 7 < 4) else "#FF7B29"

                elif amp > 0.48:

                    col = "#E85C9E" if (i % 3 == 0) else "#F279B8"

                else:

                    col = "#C878E8"



            bars.append((max(0.06, min(0.96, amp)), col))

        return bars



    def update_display(self, mode_title=None, track_text=None, lufs_readout=None, db_count=None, progress=None, ceiling=None):

        if mode_title is not None:

            self.mode_title = mode_title

        if track_text is not None:

            self.track_text = track_text

        if lufs_readout is not None:

            self.lufs_readout = lufs_readout

        if db_count is not None:

            self.db_count = db_count

        if progress is not None:

            self.target_progress = max(0.0, min(100.0, float(progress)))

            if self.target_progress == 0.0:

                self.display_progress = 0.0

                self.active_ceiling = 0.0

        if ceiling is not None:

            self.active_ceiling = max(self.target_progress, min(100.0, float(ceiling)))

        self._draw()



    def step_smooth_animation(self, is_running):

        changed = False

        if self.display_progress < self.target_progress:

            diff = self.target_progress - self.display_progress

            step = max(0.25, diff * 0.22)

            self.display_progress = min(self.target_progress, self.display_progress + step)

            changed = True

        elif is_running and self.display_progress < self.active_ceiling:

            self.display_progress = min(self.active_ceiling, self.display_progress + 0.12)

            changed = True



        if changed:

            self._draw()



    def _draw(self):

        self.delete("all")

        w = max(self.winfo_width(), 600)

        h = max(self.winfo_height(), 132)



        oled_top = 4

        oled_bottom = 58

        self.create_rectangle(4, oled_top, w - 4, oled_bottom, fill=BG_SCREEN_INTERIOR, outline="#343842", width=1.5)



        self.create_text(18, 19, text=self.mode_title, anchor="w", fill="#FFFFFF", font=(FONT_MAIN, 12, "bold"))



        self.create_rectangle(195, 10, 375, 28, fill="#EAECEF", outline="")

        self.create_text(285, 19, text=f"DATABASE: {self.db_count} TRACKS", fill="#121317", font=(FONT_MAIN, 8, "bold"))



        self.create_text(w - 18, 19, text=f"{self.lufs_readout} LUFS", anchor="e", fill="#FFFFFF", font=(FONT_MAIN, 13, "bold"))



        self.create_line(14, 33, w - 14, 33, fill="#353944")

        self.create_text(18, 45, text=self.track_text, anchor="w", fill="#FFFFFF", font=(FONT_MAIN, 9))

        self.create_text(w - 18, 45, text=f"{self.display_progress:5.1f}%", anchor="e", fill="#7CC6FF", font=(FONT_MAIN, 9, "bold"))



        wave_top = 64

        wave_bottom = h - 4

        wave_mid = (wave_top + wave_bottom) / 2

        max_amp = (wave_bottom - wave_top) / 2 - 4



        self.create_rectangle(4, wave_top, w - 4, wave_bottom, fill="#0D0E11", outline="#262930", width=1)

        self.create_line(8, wave_mid, w - 8, wave_mid, fill="#1A1C22")



        usable_w = w - 24

        n_bars = len(self.wave_bars)

        bar_step = usable_w / n_bars

        prog_ratio = self.display_progress / 100.0



        for g_idx in range(1, 14):

            gx = 12 + (g_idx / 14) * usable_w

            self.create_line(gx, wave_top + 2, gx, wave_bottom - 2, fill="#2A2D35", width=1)



        for idx, (amp, rgb_color) in enumerate(self.wave_bars):

            bar_ratio = idx / n_bars

            bx = 12 + idx * bar_step

            bh = max(1.5, amp * max_amp)



            if bar_ratio <= prog_ratio and self.display_progress > 0:

                color = rgb_color

            else:

                color = "#4C505A" if amp > 0.65 else ("#363940" if amp > 0.35 else "#25272C")



            self.create_line(bx, wave_mid - bh, bx, wave_mid + bh, fill=color, width=1.5)



        playhead_x = 12 + prog_ratio * usable_w

        self.create_line(playhead_x, wave_top + 1, playhead_x, wave_bottom - 1, fill="#FF3B1F", width=2)





class DarkTrackTable(tk.Frame):

    """Tabla oscura con scrollbar negro propio, scroll manual libre y vúmetros en forma de pastilla."""

    def __init__(self, parent):

        super().__init__(parent, bg=BG_CHASSIS)

        self.rows = []

        self.row_map = {}

        self.row_height = 30

        self.target_lufs = -12.0



        self.header = tk.Canvas(self, height=28, bg="#14161A", highlightthickness=0)

        self.header.pack(fill=tk.X)



        body = tk.Frame(self, bg=BG_CHASSIS)

        body.pack(fill=tk.BOTH, expand=True)



        self.canvas = tk.Canvas(body, bg="#08090B", highlightthickness=1, highlightbackground="#22252C")

        self.scrollbar = DarkScrollbar(body, command=self._on_scrollbar, width=14)

        self.canvas.configure(yscrollcommand=self.scrollbar.set)



        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)



        self.canvas.bind("<Configure>", lambda e: self.redraw())

        self.canvas.bind("<MouseWheel>", self._on_mousewheel)

        self.header.bind("<Configure>", lambda e: self._draw_header())



    def set_target_reference(self, target_lufs):

        self.target_lufs = target_lufs

        self.redraw()



    def clear(self):

        self.rows.clear()

        self.row_map.clear()

        self.canvas.yview_moveto(0)

        self.redraw()



    def insert_row(self, row_id, artist, title, fmt, lufs_str, gain_str, status, lufs_num=None):

        row = {

            "id": row_id,

            "artist": artist,

            "title": title,

            "fmt": fmt,

            "lufs_str": lufs_str,

            "gain_str": gain_str,

            "status": status,

            "lufs_num": lufs_num,

        }

        self.rows.append(row)

        self.row_map[row_id] = row

        self._update_scrollregion()

        self.redraw()



    def update_row(self, row_id, lufs_str=None, gain_str=None, status=None, lufs_num=None):

        row = self.row_map.get(row_id)

        if not row:

            return

        if lufs_str is not None:

            row["lufs_str"] = lufs_str

        if gain_str is not None:

            row["gain_str"] = gain_str

        if status is not None:

            row["status"] = status

        if lufs_num is not None:

            row["lufs_num"] = lufs_num

        self.redraw()



    def remove_row(self, row_id):

        row = self.row_map.pop(row_id, None)

        if row and row in self.rows:

            self.rows.remove(row)

            self._update_scrollregion()

            self.redraw()



    def _update_scrollregion(self):

        total_h = max(len(self.rows) * self.row_height, self.canvas.winfo_height())

        self.canvas.configure(scrollregion=(0, 0, self.canvas.winfo_width(), total_h))



    def _on_scrollbar(self, *args):

        self.canvas.yview(*args)

        self.redraw()



    def _on_mousewheel(self, event):

        if len(self.rows) * self.row_height > self.canvas.winfo_height():

            self.canvas.yview_scroll(-1 * (event.delta // 120), "units")

            self.redraw()



    def _col_positions(self, w):

        return [

            ("ARTIST", 12, int(w * 0.17)),

            ("TITLE / TRACK", int(w * 0.18), int(w * 0.23)),

            ("FORMAT", int(w * 0.42), int(w * 0.06)),

            ("LUFS", int(w * 0.49), int(w * 0.08)),

            ("GAIN", int(w * 0.58), int(w * 0.08)),

            ("LEVEL METER (-30 dB  ➔  CLIP)", int(w * 0.67), int(w * 0.19)),

            ("STATUS", int(w * 0.87), int(w * 0.12)),

        ]



    def _draw_header(self):

        self.header.delete("all")

        w = max(self.header.winfo_width(), 800)

        for title, x, _cw in self._col_positions(w):

            self.header.create_text(x, 14, text=title, anchor="w", fill=TEXT_WHITE, font=(FONT_MAIN, 8, "bold"))

        self.header.create_line(0, 27, w, 27, fill="#2A2D35")



    def _draw_horizontal_vumeter(self, x, y, w, h, lufs_val):

        num_segs = 15

        clip_w = 32

        slot_w = max(80, w - clip_w - 10)

        cy = y + h / 2



        self.canvas.create_line(

            x + 4, cy, x + slot_w - 4, cy,

            width=h - 8, fill="#030304", capstyle=tk.ROUND

        )



        usable_slot = slot_w - 10

        step_x = usable_slot / num_segs

        pill_thickness = max(3.5, min(6.0, step_x * 0.56))

        pill_top = y + 8.5

        pill_bot = y + h - 8.5



        lit_segments = 0

        is_clip = False

        if lufs_val is not None:

            diff_over_target = lufs_val - self.target_lufs

            lit_segments = int(round(10 + diff_over_target * 1.35))

            lit_segments = max(1, min(num_segs, lit_segments))

            if diff_over_target > 0.2:

                is_clip = True



        for i in range(num_segs):

            px = x + 7 + i * step_x + step_x * 0.35



            if i < lit_segments:

                if i < 10:

                    outer_col, core_col = "#CBE600", "#EAFF4D"

                elif i < 14:

                    outer_col, core_col = "#FF8C1A", "#FFC266"

                else:

                    outer_col, core_col = "#FF1A3C", "#FF667D"



                self.canvas.create_line(px, pill_top, px, pill_bot, width=pill_thickness, fill=outer_col, capstyle=tk.ROUND)

                if pill_thickness >= 4.5:

                    self.canvas.create_line(px, pill_top + 1, px, pill_bot - 1, width=pill_thickness * 0.45, fill=core_col, capstyle=tk.ROUND)

            else:

                self.canvas.create_line(px, pill_top, px, pill_bot, width=pill_thickness, fill="#2A2C30", capstyle=tk.ROUND)



        cx1 = x + slot_w + 4

        cy1 = y + 5

        cy2 = y + h - 5

        self.canvas.create_rectangle(

            cx1, cy1, cx1 + clip_w, cy2,

            fill="#1C0608" if is_clip else "#060709",

            outline="#FF2836" if is_clip else "#22242A",

            width=1

        )

        self.canvas.create_text(

            cx1 + clip_w / 2, y + h / 2,

            text="CLIP",

            fill="#FF2E2E" if is_clip else "#482226",

            font=(FONT_MAIN, 6, "bold")

        )



    def redraw(self):

        self.canvas.delete("all")

        self._update_scrollregion()

        w = max(self.canvas.winfo_width(), 800)

        h = max(self.canvas.winfo_height(), 200)



        if not self.rows:

            self.canvas.create_text(

                w / 2, h / 2,

                text="QUEUE EMPTY — SELECT 'LOAD FOLDER' OR 'LOAD TRACK' TO BEGIN",

                fill=TEXT_DIM, font=(FONT_MAIN, 10, "bold")

            )

            return



        top_y = self.canvas.canvasy(0)

        bottom_y = top_y + h

        first_idx = max(0, int(top_y // self.row_height) - 1)

        last_idx = min(len(self.rows), int(bottom_y // self.row_height) + 2)



        cols = self._col_positions(w)



        for idx in range(first_idx, last_idx):

            row = self.rows[idx]

            ry = idx * self.row_height

            bg = "#0D0E12" if idx % 2 == 0 else "#090A0D"

            self.canvas.create_rectangle(0, ry, w, ry + self.row_height, fill=bg, outline="#16181E")



            self.canvas.create_text(cols[0][1], ry + 15, text=row["artist"][:26], anchor="w", fill=TEXT_WHITE, font=(FONT_MAIN, 9))

            self.canvas.create_text(cols[1][1], ry + 15, text=row["title"][:36], anchor="w", fill="#E0E4EC", font=(FONT_MAIN, 9, "bold"))

            self.canvas.create_text(cols[2][1], ry + 15, text=row["fmt"], anchor="w", fill=TEXT_SILVER, font=(FONT_MAIN, 8, "bold"))



            lufs_color = "#FFA028" if (row["lufs_num"] is not None and row["lufs_num"] > self.target_lufs) else "#7CC6FF"

            self.canvas.create_text(cols[3][1], ry + 15, text=row["lufs_str"], anchor="w", fill=lufs_color, font=(FONT_MAIN, 9, "bold"))

            self.canvas.create_text(cols[4][1], ry + 15, text=row["gain_str"], anchor="w", fill="#FFE066", font=(FONT_MAIN, 9, "bold"))



            self._draw_horizontal_vumeter(cols[5][1], ry, cols[5][2], self.row_height, row["lufs_num"])



            st = row["status"]

            st_col = "#51CF66" if "✔" in st else ("#FFA028" if "⚠️" in st or "NORMALIZING" in st else TEXT_SILVER)

            self.canvas.create_text(cols[6][1], ry + 15, text=st, anchor="w", fill=st_col, font=(FONT_MAIN, 8, "bold"))





class GainlessApp:

    def __init__(self, root):

        self.root = root

        self.root.title("GAINLESS")

        self.root.geometry("1040x690")

        self.root.minsize(1000, 600)

        self.root.configure(bg=BG_CHASSIS)



        # Aplicamos el ícono gainless.ico a la ventana y barra de tareas

        ico_file = resource_path("gainless.ico")

        if os.path.exists(ico_file):

            try:

                self.root.iconbitmap(default=ico_file)

            except Exception:

                pass



        appdata = os.environ.get("APPDATA") or os.path.expanduser("~")

        self.db_dir = os.path.join(appdata, "WaveAlign_Custom_DB")

        os.makedirs(self.db_dir, exist_ok=True)

        self.db_path = os.path.join(self.db_dir, "processed_tracks_log.json")

        self.db_data = self._load_db()



        self.file_queue = []

        self.row_counter = 0

        self.is_running = False

        self.stop_requested = False

        self.msg_queue = queue.Queue()



        self._build_ui()

        self._refresh_screen_header()

        self.root.after(30, self._ui_and_animation_loop)

        self.root.after(360, self._blink_timer)



    # ---------------- DATABASE MANAGEMENT ----------------

    def _load_db(self):

        if os.path.exists(self.db_path):

            try:

                with open(self.db_path, "r", encoding="utf-8") as f:

                    data = json.load(f)

                    if isinstance(data, dict):

                        return data

            except Exception:

                pass

        return {}



    def _save_db(self):

        try:

            with open(self.db_path, "w", encoding="utf-8") as f:

                json.dump(self.db_data, f, indent=2, ensure_ascii=False)

        except Exception as e:

            print(f"Database save error: {e}")



    def _clean_for_tk(self, text):

        if not text:

            return ""

        cleaned = str(text).replace("\x00", "").replace("\r", " ").replace("\n", " ").strip()

        return "".join(ch for ch in cleaned if ord(ch) <= 0xFFFF)



    def _extract_track_identity(self, filepath):

        artist = ""

        title = ""

        try:

            audio = MutagenFile(filepath, easy=True)

            if audio and audio.tags:

                a_list = audio.tags.get("artist", [])

                t_list = audio.tags.get("title", [])

                if a_list:

                    artist = self._clean_for_tk(a_list[0])

                if t_list:

                    title = self._clean_for_tk(t_list[0])



            if not artist or not title:

                raw_audio = MutagenFile(filepath)

                if raw_audio and raw_audio.tags:

                    if not artist and "TPE1" in raw_audio.tags:

                        artist = self._clean_for_tk(raw_audio.tags["TPE1"])

                    if not title and "TIT2" in raw_audio.tags:

                        title = self._clean_for_tk(raw_audio.tags["TIT2"])

        except Exception:

            pass



        p = Path(filepath)

        filename = self._clean_for_tk(p.name)

        stem = self._clean_for_tk(p.stem)



        generic_names = {"", "unknown", "unknown artist", "desconocido", "varios", "various artists", "sin titulo", "untitled"}

        has_valid_artist = artist.lower() not in generic_names

        has_valid_title = title.lower() not in generic_names and not re.match(r"^track\s*\d+$", title.lower())



        if has_valid_artist and has_valid_title:

            key = f"tag::{artist.lower()} || {title.lower()}"

            display_artist = artist

            display_title = title

        else:

            key = f"file::{filename.lower()}"

            display_artist = artist if has_valid_artist else "No Tag (File)"

            display_title = title if has_valid_title else stem



        return key, display_artist, display_title, filename



    def _register_in_db(self, item, lufs_val, target_lufs, action_text):

        key = item["db_key"]

        self.db_data[key] = {

            "artist": item["artist"],

            "title": item["title"],

            "filename": item["filename"],

            "measured_lufs": round(lufs_val, 2),

            "target_lufs": round(target_lufs, 2),

            "action": action_text,

            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        }

        self._save_db()



    # ---------------- UI CONSTRUCTION ----------------

    def _build_ui(self):

        brand_bar = tk.Frame(self.root, bg="#050507", height=34)

        brand_bar.pack(fill=tk.X)



        logo_widget = HeaderGainlessLogo(brand_bar, size=26)

        logo_widget.pack(side=tk.LEFT, padx=(12, 6), pady=4)



        tk.Label(

            brand_bar, text="GAINLESS",

            fg="#FFFFFF", bg="#050507", font=(FONT_MAIN, 12, "bold")

        ).pack(side=tk.LEFT, pady=4)



        tk.Label(

            brand_bar, text="ZERO-GAIN AUDIO LOUDNESS NORMALIZER",

            fg=TEXT_DIM, bg="#050507", font=(FONT_MAIN, 8, "bold")

        ).pack(side=tk.RIGHT, padx=14, pady=4)



        deck_frame = tk.Frame(self.root, bg=BG_PANEL, highlightbackground=BORDER_SUBTLE, highlightthickness=1, padx=8, pady=6)

        deck_frame.pack(fill=tk.X, padx=8, pady=(2, 4))



        # 1. Source Selector Knob (STAND BY / FOLDER / TRACK)

        input_box = tk.Frame(deck_frame, bg=BG_PANEL, highlightbackground=BORDER_SUBTLE, highlightthickness=1, padx=2, pady=2)

        input_box.pack(side=tk.LEFT, padx=(0, 6))

        self.input_selector = InputFolderSelectorKnob(input_box, self.add_folder, self.add_files)

        self.input_selector.pack()



        # 2. Backlit Rubber Buttons Panel (TOOLS)

        buttons_spec = [

            ("LOAD\nFOLDER", self.add_folder),

            ("LOAD\nTRACK", self.add_files),

            ("CLEAN\nQUEUE", self.clear_queue),

            ("DATABASE", self.open_log_file),

            ("RESET\nDATABASE", self.reset_database),

            ("STOP", self.stop_processing),

        ]

        self.rubber_panel = BacklitRubberButtonsPanel(deck_frame, buttons_spec, width=326, height=148)

        self.rubber_panel.pack(side=tk.LEFT, padx=(0, 6))



        # 3. Potentiometers: TARGET LUFS & TOLERANCE

        knobs_box = tk.Frame(deck_frame, bg=BG_PANEL, highlightbackground=BORDER_SUBTLE, highlightthickness=1, padx=6, pady=2)

        knobs_box.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))



        self.target_knob = HardwareRotaryKnob(

            knobs_box, label_text="TARGET LUFS",

            min_val=-18.0, max_val=-6.0, init_val=-12.0, step=0.5,

            left_range_text="-18", right_range_text="-6", knob_style="eq", size=110,

            on_change=self._on_target_knob_change

        )

        self.target_knob.pack(side=tk.LEFT, padx=3)



        self.tol_knob = HardwareRotaryKnob(

            knobs_box, label_text="TOLERANCE",

            min_val=0.0, max_val=1.5, init_val=0.2, step=0.1,

            left_range_text="0.0", right_range_text="+1.5", knob_style="trim", size=110,

            on_change=lambda _v: None

        )

        self.tol_knob.pack(side=tk.LEFT, padx=3)



        # 4. Action Buttons: STEP 1 ANALYZE + NORMALIZE

        action_box = tk.Frame(deck_frame, bg=BG_PANEL, highlightbackground=BORDER_SUBTLE, highlightthickness=1, padx=8, pady=4)

        action_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)



        analyze_col = tk.Frame(action_box, bg=BG_PANEL)

        analyze_col.pack(side=tk.LEFT, expand=True, padx=(2, 6), pady=14)

        tk.Label(analyze_col, text="STEP 1", fg=TEXT_SILVER, bg=BG_PANEL, font=(FONT_MAIN, 8, "bold")).pack(pady=(0, 6))

        self.analyze_btn = BacklitOrangeAnalyzeButton(analyze_col, command=self.start_analysis)

        self.analyze_btn.pack()



        norm_col = tk.Frame(action_box, bg=BG_PANEL)

        norm_col.pack(side=tk.LEFT, expand=True, padx=2, pady=6)

        self.normalize_btn = BlueGradientNormalizeButton(norm_col, command=self.start_normalization)

        self.normalize_btn.pack()



        # Screen & High-Res Waveform

        screen_container = tk.Frame(self.root, bg=BG_CHASSIS, padx=8, pady=3)

        screen_container.pack(fill=tk.X)

        self.screen_wave = StatusScreenAndHighResWaveform(screen_container, height=132)

        self.screen_wave.pack(fill=tk.X)



        # Dark Track Table

        table_container = tk.Frame(self.root, bg=BG_CHASSIS, padx=8, pady=5)

        table_container.pack(fill=tk.BOTH, expand=True)

        self.track_table = DarkTrackTable(table_container)

        self.track_table.pack(fill=tk.BOTH, expand=True)



    def _on_target_knob_change(self, new_val):

        self.track_table.set_target_reference(new_val)

        if not self.is_running:

            self.screen_wave.update_display(lufs_readout=f"{new_val:.1f}")



    def _refresh_screen_header(self):

        self.screen_wave.update_display(

            lufs_readout=f"{self.target_knob.get():.1f}",

            db_count=len(self.db_data)

        )



    def _blink_timer(self):

        self.normalize_btn.toggle_blink_phase()

        self.root.after(360, self._blink_timer)



    # ---------------- FILE LOADING & DATABASE ----------------

    def add_folder(self):

        if self.is_running:

            return

        folder = filedialog.askdirectory(title="Select Root Music Folder")

        if not folder:

            return



        folder_name = Path(folder).name or folder

        self.input_selector.set_source("FOLDER", folder_name)



        added, skipped_db, duplicates_ui, other_files, errors = 0, 0, 0, 0, 0

        for root_dir, _, files in os.walk(folder):

            for f in sorted(files):

                if f.startswith("._") or f.startswith(".temp_"):

                    continue

                ext = os.path.splitext(f)[1].lower()

                if ext not in SUPPORTED_EXTS:

                    other_files += 1

                    continue

                full_path = os.path.join(root_dir, f)

                try:

                    res = self._enqueue_file(full_path)

                    if res == "added":

                        added += 1

                    elif res == "in_db":

                        skipped_db += 1

                    elif res == "duplicate":

                        duplicates_ui += 1

                except Exception:

                    errors += 1



        self.screen_wave.update_display(

            mode_title="FOLDER LOADED",

            track_text=f"'{folder_name}' -> Added: {added} | Skipped (in DB): {skipped_db} | Other files: {other_files}",

            progress=0.0

        )



    def add_files(self):

        if self.is_running:

            return

        files = filedialog.askopenfilenames(

            title="Select Audio Tracks",

            filetypes=[("Audio Files", "*.mp3 *.flac *.wav *.aiff *.aif *.m4a *.mp4 *.ogg *.opus *.aac *.wma")]

        )

        if not files:

            return



        self.input_selector.set_source("FILES", f"{len(files)} TRACKS")

        added, skipped_db, duplicates_ui, errors = 0, 0, 0, 0

        for f in files:

            try:

                res = self._enqueue_file(f)

                if res == "added":

                    added += 1

                elif res == "in_db":

                    skipped_db += 1

                elif res == "duplicate":

                    duplicates_ui += 1

            except Exception:

                errors += 1



        self.screen_wave.update_display(

            mode_title="TRACKS LOADED",

            track_text=f"Selected -> Added: {added} | Skipped (in DB): {skipped_db} | Duplicates: {duplicates_ui}",

            progress=0.0

        )



    def _enqueue_file(self, filepath):

        norm_path = os.path.normpath(filepath)

        if any(item["path"] == norm_path for item in self.file_queue):

            return "duplicate"



        db_key, artist, title, filename = self._extract_track_identity(norm_path)

        if db_key in self.db_data:

            return "in_db"



        p = Path(norm_path)

        ext_str = p.suffix.upper().replace(".", "")

        self.row_counter += 1

        row_id = f"row_{self.row_counter}"



        self.track_table.insert_row(row_id, artist, title, ext_str, "-", "-", "PENDING", lufs_num=None)

        self.file_queue.append({

            "id": row_id,

            "path": norm_path,

            "db_key": db_key,

            "artist": artist,

            "title": title,

            "filename": filename,

            "lufs": None,

            "gain_db": None,

            "analyzed": False,

            "done": False

        })

        return "added"



    def clear_queue(self):

        if self.is_running:

            messagebox.showwarning("Busy", "Stop the current process before cleaning the queue.")

            return

        self.track_table.clear()

        self.file_queue.clear()

        self.input_selector.set_source("IDLE", "STAND BY")

        self.screen_wave.update_display(

            mode_title="STAND BY",

            track_text="Queue cleaned. Select 'LOAD FOLDER' or 'LOAD TRACK' to begin.",

            progress=0.0

        )



    def reset_database(self):

        if self.is_running:

            messagebox.showwarning("Busy", "Stop the current process before resetting the database.")

            return

        count = len(self.db_data)

        if count == 0:

            messagebox.showinfo("Database", "The database is already empty.")

            return

        if messagebox.askyesno(

            "Reset Database",

            f"Are you sure you want to delete all {count} tracks from the permanent database?"

        ):

            self.db_data.clear()

            if os.path.exists(self.db_path):

                try:

                    os.remove(self.db_path)

                except OSError:

                    pass

            self._save_db()

            self._refresh_screen_header()

            self.screen_wave.update_display(mode_title="DB RESET", track_text="Permanent database cleared (0 tracks).")



    def open_log_file(self):

        if not os.path.exists(self.db_path):

            self._save_db()

        try:

            os.startfile(self.db_path)

        except Exception:

            os.startfile(self.db_dir)



    # ---------------- STEP 1 (ANALYZE) & STEP 2 (NORMALIZE) ----------------

    def start_analysis(self):

        if self.is_running or not self.file_queue:

            return

        if not shutil.which("ffmpeg"):

            messagebox.showerror("FFmpeg Not Found", "Could not find 'ffmpeg' on the system.")

            return



        target_lufs = self.target_knob.get()

        tolerance = self.tol_knob.get()



        self.is_running = True

        self.stop_requested = False

        self.analyze_btn.set_active(True)

        self.analyze_btn.set_enabled(False)

        self.normalize_btn.set_enabled(False)

        self.screen_wave.update_display(progress=0.0, ceiling=5.0)



        threading.Thread(

            target=self._worker_analyze_and_filter,

            args=(target_lufs, tolerance),

            daemon=True

        ).start()



    def start_normalization(self):

        if self.is_running or not self.file_queue:

            return

        if not shutil.which("ffmpeg"):

            messagebox.showerror("FFmpeg Not Found", "Could not find 'ffmpeg' on the system.")

            return



        target_lufs = self.target_knob.get()

        tolerance = self.tol_knob.get()



        self.is_running = True

        self.stop_requested = False

        self.analyze_btn.set_enabled(False)

        self.normalize_btn.set_enabled(False)

        self.normalize_btn.set_blinking(True)

        self.screen_wave.update_display(progress=0.0, ceiling=5.0)



        threading.Thread(

            target=self._worker_normalize,

            args=(target_lufs, tolerance),

            daemon=True

        ).start()



    def stop_processing(self):

        if self.is_running:

            self.stop_requested = True

            self.screen_wave.update_display(mode_title="STOPPING", track_text="Stopping after current track finishes...")



    def _worker_analyze_and_filter(self, target_lufs, tolerance):

        total = len(self.file_queue)

        kept_items = []

        discarded_count = 0

        out_of_range_count = 0



        for idx, item in enumerate(self.file_queue, start=1):

            if self.stop_requested:

                kept_items.append(item)

                continue



            filepath = item["path"]

            row_id = item["id"]

            start_pct = (idx - 1) / total * 100.0

            end_pct = idx / total * 100.0



            self.msg_queue.put(("update_row", row_id, None, None, "MEASURING...", None))

            self.msg_queue.put((

                "screen", "ANALYZING",

                f"[{idx}/{total}] Measuring LUFS: {item['artist']} - {item['title']}",

                f"{target_lufs:.1f}", start_pct, end_pct

            ))



            try:

                current_lufs = self._measure_lufs(filepath)

                if current_lufs is None:

                    self.msg_queue.put(("update_row", row_id, "ERR", "-", "READ ERROR", None))

                    kept_items.append(item)

                    continue



                item["lufs"] = current_lufs

                item["analyzed"] = True

                lufs_str = f"{current_lufs:.1f} dB"



                if current_lufs > (target_lufs + tolerance):

                    gain_db = target_lufs - current_lufs

                    item["gain_db"] = gain_db

                    out_of_range_count += 1

                    kept_items.append(item)

                    self.msg_queue.put((

                        "update_row", row_id, lufs_str, f"{gain_db:.2f} dB", "⚠️ OUT OF RANGE", current_lufs

                    ))

                    self.msg_queue.put((

                        "screen", "OUT OF RANGE",

                        f"[{idx}/{total}] Above target ({lufs_str}): {item['artist']} - {item['title']}",

                        f"{current_lufs:.1f}", end_pct, end_pct

                    ))

                else:

                    self._register_in_db(item, current_lufs, target_lufs, "In range (Untouched)")

                    discarded_count += 1

                    self.msg_queue.put(("remove_row", row_id))

                    self.msg_queue.put((

                        "screen", "IN RANGE",

                        f"[{idx}/{total}] In range ({lufs_str}, filtered out): {item['artist']} - {item['title']}",

                        f"{current_lufs:.1f}", end_pct, end_pct

                    ))



            except Exception as e:

                self.msg_queue.put(("update_row", row_id, "ERR", "-", f"ERR: {str(e)[:14]}", None))

                kept_items.append(item)



        self.file_queue = kept_items

        self.msg_queue.put(("analysis_finished", out_of_range_count, discarded_count))



    def _worker_normalize(self, target_lufs, tolerance):

        total = len(self.file_queue)

        normalized_count = 0



        for idx, item in enumerate(self.file_queue, start=1):

            if self.stop_requested:

                break

            if item["done"]:

                continue



            filepath = item["path"]

            row_id = item["id"]

            start_pct = (idx - 1) / total * 100.0

            end_pct = idx / total * 100.0



            try:

                if not item["analyzed"] or item["lufs"] is None:

                    self.msg_queue.put(("update_row", row_id, None, None, "MEASURING...", None))

                    self.msg_queue.put((

                        "screen", "MEASURING",

                        f"[{idx}/{total}] Evaluating: {item['artist']} - {item['title']}",

                        f"{target_lufs:.1f}", start_pct, end_pct

                    ))

                    current_lufs = self._measure_lufs(filepath)

                    if current_lufs is None:

                        self.msg_queue.put(("update_row", row_id, "ERR", "-", "READ ERROR", None))

                        continue

                    item["lufs"] = current_lufs

                    item["analyzed"] = True

                else:

                    current_lufs = item["lufs"]



                lufs_str = f"{current_lufs:.1f} dB"



                if current_lufs > (target_lufs + tolerance):

                    gain_db = target_lufs - current_lufs

                    gain_str = f"{gain_db:.2f} dB"

                    self.msg_queue.put(("update_row", row_id, lufs_str, gain_str, "⚡ NORMALIZING...", current_lufs))

                    self.msg_queue.put((

                        "screen", "NORMALIZING",

                        f"[{idx}/{total}] Applying {gain_str}: {item['artist']} - {item['title']}",

                        f"{current_lufs:.1f}", start_pct, end_pct

                    ))



                    self._apply_gain_preserving_tags(filepath, gain_db)

                    item["done"] = True

                    normalized_count += 1



                    self._register_in_db(

                        item, current_lufs, target_lufs, f"Normalized ({gain_str} -> {target_lufs:.1f} LUFS)"

                    )

                    self.msg_queue.put((

                        "update_row", row_id, f"{target_lufs:.1f} dB", gain_str, "✔ NORMALIZED", target_lufs

                    ))

                else:

                    item["done"] = True

                    self._register_in_db(item, current_lufs, target_lufs, "In range (Untouched)")

                    self.msg_queue.put(("update_row", row_id, lufs_str, "0.00 dB", "✔ IN RANGE", current_lufs))



            except Exception as e:

                self.msg_queue.put(("update_row", row_id, "ERR", "-", f"ERR: {str(e)[:14]}", None))



            self.msg_queue.put((

                "screen", "NORMALIZING",

                f"[{idx}/{total}] Completed: {item['artist']} - {item['title']}",

                f"{target_lufs:.1f}", end_pct, end_pct

            ))



        self.msg_queue.put(("normalization_finished", normalized_count))



    # ---------------- AUDIO ENGINE & TAG PRESERVATION ----------------

    def _measure_lufs(self, filepath):

        cmd = [

            "ffmpeg", "-nostats", "-i", filepath,

            "-filter_complex", "ebur128=peak=true",

            "-f", "null", "-"

        ]

        proc = subprocess.run(

            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,

            text=True, encoding="utf-8", errors="replace",

            creationflags=WIN_NO_WINDOW

        )

        matches = re.findall(r"I:\s*(-?\d+(?:\.\d+)?)\s*LUFS", proc.stderr)

        if not matches:

            return None

        val = float(matches[-1])

        if val <= -70.0:

            return None

        return val



    def _probe_audio_info(self, filepath):

        sample_rate = None

        bit_rate = "320k"

        if shutil.which("ffprobe"):

            cmd = [

                "ffprobe", "-v", "error", "-select_streams", "a:0",

                "-show_entries", "stream=sample_rate,bit_rate",

                "-of", "default=noprint_wrappers=1", filepath

            ]

            proc = subprocess.run(

                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,

                text=True, creationflags=WIN_NO_WINDOW

            )

            for line in proc.stdout.splitlines():

                if line.startswith("sample_rate="):

                    val = line.split("=")[1].strip()

                    if val.isdigit():

                        sample_rate = val

                elif line.startswith("bit_rate="):

                    val = line.split("=")[1].strip()

                    if val.isdigit() and int(val) > 0:

                        bit_rate = str(max(int(val), 192000))

        return sample_rate, bit_rate



    def _apply_gain_preserving_tags(self, filepath, gain_db):

        p = Path(filepath)

        ext = p.suffix.lower()

        temp_path = str(p.with_name(f".temp_align_{p.name}"))

        sample_rate, bit_rate = self._probe_audio_info(filepath)



        cmd = [

            "ffmpeg", "-y", "-i", filepath,

            "-map", "0:a:0",

            "-map_metadata", "0",

            "-af", f"volume={gain_db:.4f}dB"

        ]

        if sample_rate:

            cmd.extend(["-ar", sample_rate])



        if ext == ".mp3":

            cmd.extend(["-c:a", "libmp3lame", "-b:a", bit_rate, "-id3v2_version", "3", "-write_id3v1", "1"])

        elif ext == ".flac":

            cmd.extend(["-c:a", "flac"])

        elif ext in {".wav", ".aiff", ".aif"}:

            cmd.extend(["-write_id3v2", "1"])

        elif ext in {".m4a", ".mp4", ".aac"}:

            cmd.extend(["-c:a", "aac", "-b:a", bit_rate])



        cmd.append(temp_path)



        try:

            proc = subprocess.run(

                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,

                text=True, encoding="utf-8", errors="replace",

                creationflags=WIN_NO_WINDOW

            )

            if proc.returncode != 0 or not os.path.exists(temp_path):

                raise RuntimeError("FFmpeg Failed")



            self._clone_metadata_deep(filepath, temp_path, ext)

            os.replace(temp_path, filepath)

        finally:

            if os.path.exists(temp_path):

                try:

                    os.remove(temp_path)

                except OSError:

                    pass



    def _clone_metadata_deep(self, src_path, dst_path, ext):

        try:

            if ext == ".mp3":

                try:

                    orig_id3 = ID3(src_path)

                    orig_id3.save(dst_path, v2_version=3)

                except ID3NoHeaderError:

                    pass

            elif ext == ".flac":

                orig_flac = FLAC(src_path)

                dst_flac = FLAC(dst_path)

                if orig_flac.tags:

                    dst_flac.tags.clear()

                    for k, v in orig_flac.tags.items():

                        dst_flac.tags[k] = v

                dst_flac.clear_pictures()

                for pic in orig_flac.pictures:

                    dst_flac.add_picture(pic)

                dst_flac.save()

            elif ext == ".wav":

                orig_wav = WAVE(src_path)

                if orig_wav.tags:

                    orig_wav.tags.save(dst_path, v2_version=3)

            elif ext in {".aiff", ".aif"}:

                orig_aiff = AIFF(src_path)

                if orig_aiff.tags:

                    orig_aiff.tags.save(dst_path, v2_version=3)

            elif ext in {".m4a", ".mp4"}:

                orig_mp4 = MP4(src_path)

                dst_mp4 = MP4(dst_path)

                if orig_mp4.tags:

                    dst_mp4.tags = orig_mp4.tags

                    dst_mp4.save()

        except Exception as tag_err:

            print(f"Warning copying extra tags on {src_path}: {tag_err}")



    # ---------------- UI & ANIMATION LOOP ----------------

    def _ui_and_animation_loop(self):

        try:

            while True:

                msg = self.msg_queue.get_nowait()

                kind = msg[0]

                if kind == "update_row":

                    _, row_id, lufs_str, gain_str, status, lufs_num = msg

                    self.track_table.update_row(row_id, lufs_str, gain_str, status, lufs_num)

                elif kind == "remove_row":

                    _, row_id = msg

                    self.track_table.remove_row(row_id)

                elif kind == "screen":

                    _, mode_title, track_text, lufs_readout, start_pct, end_pct = msg

                    self.screen_wave.update_display(

                        mode_title=mode_title,

                        track_text=track_text,

                        lufs_readout=lufs_readout,

                        db_count=len(self.db_data),

                        progress=start_pct,

                        ceiling=end_pct

                    )

                elif kind == "analysis_finished":

                    _, out_count, disc_count = msg

                    self.is_running = False

                    self.analyze_btn.set_active(False)

                    self.analyze_btn.set_enabled(True)

                    self.normalize_btn.set_enabled(True)

                    resumen = (

                        f"Analysis complete: {disc_count} tracks in range (saved to DB). "

                        f"{out_count} tracks out of range ready to normalize."

                    )

                    self.screen_wave.update_display(

                        mode_title="READY",

                        track_text=resumen,

                        lufs_readout=f"{self.target_knob.get():.1f}",

                        db_count=len(self.db_data),

                        progress=100.0,

                        ceiling=100.0

                    )

                    messagebox.showinfo("Analysis Complete", resumen)

                elif kind == "normalization_finished":

                    _, norm_count = msg

                    self.is_running = False

                    self.normalize_btn.set_blinking(False)

                    self.analyze_btn.set_enabled(True)

                    self.normalize_btn.set_enabled(True)

                    resumen = f"Process complete: {norm_count} tracks normalized to {self.target_knob.get():.1f} LUFS and saved to DB."

                    self.screen_wave.update_display(

                        mode_title="COMPLETED",

                        track_text=resumen,

                        lufs_readout=f"{self.target_knob.get():.1f}",

                        db_count=len(self.db_data),

                        progress=100.0,

                        ceiling=100.0

                    )

                    messagebox.showinfo("Normalization Complete", resumen)

        except queue.Empty:

            pass



        self.screen_wave.step_smooth_animation(self.is_running)

        self.root.after(30, self._ui_and_animation_loop)





if __name__ == "__main__":

    set_windows_app_id()

    root = tk.Tk()

    app = GainlessApp(root)

    apply_dark_titlebar(root)

    root.eval('tk::PlaceWindow . center')

    root.deiconify()

    root.lift()

    root.focus_force()

    root.attributes('-topmost', True)

    root.after(500, lambda: root.attributes('-topmost', False))

    root.mainloop()
