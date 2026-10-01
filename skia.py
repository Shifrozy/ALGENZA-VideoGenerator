"""
Pure-Python Skia compatibility engine for Windows / environments where native skia-python crashes.
Faithfully emulates Skia 2D rendering primitives using Pillow (PIL) and NumPy.
"""

import os
import sys
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

kNormal_BlurStyle = 0
kPNG = "PNG"
kRGBA_8888_ColorType = 1

def Color(r, g, b, a=255):
    return (int(r) & 0xFF, int(g) & 0xFF, int(b) & 0xFF, int(a) & 0xFF)

class Point:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)

class Rect:
    def __init__(self, l, t, r, b):
        self.l = float(l)
        self.t = float(t)
        self.r = float(r)
        self.b = float(b)

    @staticmethod
    def MakeLTRB(l, t, r, b):
        return Rect(l, t, r, b)

    @staticmethod
    def MakeWH(w, h):
        return Rect(0, 0, w, h)

    @property
    def width(self):
        return self.r - self.l

    @property
    def height(self):
        return self.b - self.t

class RRect:
    def __init__(self, rect, rx, ry):
        self.rect = rect
        self.rx = float(rx)
        self.ry = float(ry)

    @staticmethod
    def MakeRectXY(rect, rx, ry):
        return RRect(rect, rx, ry)

class MaskFilter:
    def __init__(self, blur_style, sigma):
        self.style = blur_style
        self.sigma = float(sigma)

    @staticmethod
    def MakeBlur(style, sigma):
        return MaskFilter(style, sigma)

class DashPathEffect:
    def __init__(self, intervals, phase):
        self.intervals = intervals
        self.phase = phase

    @staticmethod
    def Make(intervals, phase=0):
        return DashPathEffect(intervals, phase)

class GradientShader:
    def __init__(self, center, radius, colors):
        self.center = (center.x if hasattr(center, 'x') else center[0],
                       center.y if hasattr(center, 'y') else center[1])
        self.radius = float(radius)
        self.colors = colors

    @staticmethod
    def MakeRadial(center, radius, colors):
        return GradientShader(center, radius, colors)

class Paint:
    kFill_Style = 0
    kStroke_Style = 1
    kStrokeAndFill_Style = 2
    kRound_Cap = 0
    kRound_Join = 0

    def __init__(self, AntiAlias=True, Color=(255, 255, 255, 255)):
        self.anti_alias = AntiAlias
        if isinstance(Color, (tuple, list)):
            self.color = (int(Color[0]), int(Color[1]), int(Color[2]), int(Color[3]) if len(Color) > 3 else 255)
        elif isinstance(Color, int):
            a = (Color >> 24) & 0xFF
            r = (Color >> 16) & 0xFF
            g = (Color >> 8) & 0xFF
            b = Color & 0xFF
            self.color = (r, g, b, a if a else 255)
        else:
            self.color = (255, 255, 255, 255)
        self.style = self.kFill_Style
        self.stroke_width = 1.0
        self.stroke_cap = self.kRound_Cap
        self.stroke_join = self.kRound_Join
        self.mask_filter = None
        self.path_effect = None
        self.shader = None

    def setStyle(self, style):
        self.style = style

    def setStrokeWidth(self, sw):
        self.stroke_width = float(sw)

    def setStrokeCap(self, cap):
        self.stroke_cap = cap

    def setStrokeJoin(self, join):
        self.stroke_join = join

    def setMaskFilter(self, mf):
        self.mask_filter = mf

    def setPathEffect(self, pe):
        self.path_effect = pe

    def setShader(self, s):
        self.shader = s

# Fonts fallback resolution for Windows
WIN_FONT_DIR = r"C:\Windows\Fonts"

class Typeface:
    def __init__(self, font_path=None, family_name=None):
        self.font_path = font_path
        self.family_name = family_name

    @staticmethod
    def MakeFromFile(path):
        if path and os.path.exists(path):
            return Typeface(path)
        # Windows system font fallbacks
        lower = os.path.basename(path).lower() if path else ""
        if "montserrat" in lower or "bold" in lower:
            candidates = ["segoeuib.ttf", "arialbd.ttf", "tahomabd.ttf"]
        elif "mono" in lower:
            candidates = ["consolab.ttf" if "bold" in lower else "consola.ttf", "cour.ttf"]
        else:
            candidates = ["segoeui.ttf", "arial.ttf", "tahoma.ttf"]

        for cand in candidates:
            fp = os.path.join(WIN_FONT_DIR, cand)
            if os.path.exists(fp):
                return Typeface(fp)
        return Typeface(None)

class Font:
    def __init__(self, typeface, size):
        self.typeface = typeface
        self.size = int(size)
        self._pil_font = None
        self._load_font()

    def _load_font(self):
        if self.typeface and self.typeface.font_path and os.path.exists(self.typeface.font_path):
            try:
                self._pil_font = ImageFont.truetype(self.typeface.font_path, self.size)
                return
            except Exception:
                pass
        # Fallback to Segoe UI or Arial on Windows
        for cand in ["segoeui.ttf", "arial.ttf", "tahoma.ttf"]:
            fp = os.path.join(WIN_FONT_DIR, cand)
            if os.path.exists(fp):
                try:
                    self._pil_font = ImageFont.truetype(fp, self.size)
                    return
                except Exception:
                    pass
        self._pil_font = ImageFont.load_default()

    def measureText(self, text):
        if not text:
            return 0.0
        try:
            return float(self._pil_font.getlength(text))
        except Exception:
            bbox = self._pil_font.getbbox(text)
            return float(bbox[2] - bbox[0])

class Path:
    def __init__(self):
        self.subpaths = []  # list of lists of (x, y)
        self.current_subpath = []

    def moveTo(self, x, y):
        if self.current_subpath:
            self.subpaths.append(self.current_subpath)
        self.current_subpath = [(float(x), float(y))]

    def lineTo(self, x, y):
        if not self.current_subpath:
            self.current_subpath = [(float(x), float(y))]
        else:
            self.current_subpath.append((float(x), float(y)))

    def close(self):
        if self.current_subpath and len(self.current_subpath) > 1:
            if self.current_subpath[0] != self.current_subpath[-1]:
                self.current_subpath.append(self.current_subpath[0])
            self.subpaths.append(self.current_subpath)
            self.current_subpath = []

    def addRRect(self, rrect):
        r = rrect.rect
        rx, ry = rrect.rx, rrect.ry
        # Approximate rounded rect path
        pts = []
        steps = 8
        # Top-right corner
        for a in np.linspace(3 * math.pi / 2, 2 * math.pi, steps):
            pts.append((r.r - rx + rx * math.cos(a), r.t + ry + ry * math.sin(a)))
        # Bottom-right corner
        for a in np.linspace(0, math.pi / 2, steps):
            pts.append((r.r - rx + rx * math.cos(a), r.b - ry + ry * math.sin(a)))
        # Bottom-left corner
        for a in np.linspace(math.pi / 2, math.pi, steps):
            pts.append((r.l + rx + rx * math.cos(a), r.b - ry + ry * math.sin(a)))
        # Top-left corner
        for a in np.linspace(math.pi, 3 * math.pi / 2, steps):
            pts.append((r.l + rx + rx * math.cos(a), r.t + ry + ry * math.sin(a)))
        pts.append(pts[0])
        if self.current_subpath:
            self.subpaths.append(self.current_subpath)
        self.current_subpath = pts
        self.close()

    def get_all_subpaths(self):
        res = list(self.subpaths)
        if self.current_subpath:
            res.append(self.current_subpath)
        return res

class PathMeasure:
    def __init__(self, path, force_closed=False):
        self.path = path
        self.subpaths = path.get_all_subpaths()
        # Compute lengths
        self.lengths = []
        self.total_length = 0.0
        for sp in self.subpaths:
            cur_l = 0.0
            for i in range(len(sp) - 1):
                p1, p2 = sp[i], sp[i+1]
                cur_l += math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            self.lengths.append(cur_l)
            self.total_length += cur_l

    def getLength(self):
        return self.total_length

    def getSegment(self, start_d, stop_d, dst_path, start_with_move_to=True):
        if not self.subpaths or stop_d <= start_d:
            return False
        accum = 0.0
        for sp in self.subpaths:
            for i in range(len(sp) - 1):
                p1, p2 = sp[i], sp[i+1]
                seg_l = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
                if accum + seg_l >= start_d and accum <= stop_d:
                    t1 = max(0.0, (start_d - accum) / max(seg_l, 1e-6))
                    t2 = min(1.0, (stop_d - accum) / max(seg_l, 1e-6))
                    pt_start = (p1[0] + (p2[0] - p1[0]) * t1, p1[1] + (p2[1] - p1[1]) * t1)
                    pt_end = (p1[0] + (p2[0] - p1[0]) * t2, p1[1] + (p2[1] - p1[1]) * t2)
                    if not dst_path.current_subpath:
                        dst_path.moveTo(pt_start[0], pt_start[1])
                    dst_path.lineTo(pt_end[0], pt_end[1])
                accum += seg_l
        return True

class ImageSnapshot:
    def __init__(self, pil_image):
        self.image = pil_image.copy()

    def toarray(self, colorType=None):
        return np.array(self.image)

    def save(self, filepath, format_hint=None):
        self.image.save(filepath)

class Canvas:
    def __init__(self, surface):
        self.surface = surface
        self.states = []
        self.tx = 0.0
        self.ty = 0.0
        self.sx = 1.0
        self.sy = 1.0
        self.alpha_factor = 1.0

    def _pt(self, x, y):
        return (x * self.sx + self.tx, y * self.sy + self.ty)

    def _col(self, paint):
        r, g, b, a = paint.color
        a_mod = int(round(a * self.alpha_factor))
        return (r, g, b, max(0, min(255, a_mod)))

    def clear(self, color):
        if isinstance(color, (tuple, list)):
            col = (int(color[0]), int(color[1]), int(color[2]), int(color[3]) if len(color) > 3 else 255)
        else:
            a = (color >> 24) & 0xFF
            r = (color >> 16) & 0xFF
            g = (color >> 8) & 0xFF
            b = color & 0xFF
            col = (r, g, b, a if a else 255)
        self.surface.image = Image.new("RGBA", self.surface.image.size, col)
        self.surface.draw = ImageDraw.Draw(self.surface.image, "RGBA")

    def translate(self, dx, dy):
        self.tx += dx * self.sx
        self.ty += dy * self.sy

    def scale(self, sx, sy):
        self.sx *= sx
        self.sy *= sy

    def saveLayerAlpha(self, bounds, alpha_int):
        # Push current canvas image and transformation state
        self.states.append((
            self.surface.image.copy(),
            self.tx, self.ty, self.sx, self.sy,
            self.alpha_factor,
            alpha_int / 255.0
        ))
        # Clear layer canvas for alpha blending
        self.surface.image = Image.new("RGBA", self.surface.image.size, (0, 0, 0, 0))
        self.surface.draw = ImageDraw.Draw(self.surface.image, "RGBA")

    def restore(self):
        if not self.states:
            return
        base_img, old_tx, old_ty, old_sx, old_sy, old_alpha, layer_alpha = self.states.pop()
        # Blend current surface layer onto base_img with layer_alpha
        cur_layer = self.surface.image
        if layer_alpha < 0.999:
            # Scale alpha channel
            arr = np.array(cur_layer)
            arr[:, :, 3] = (arr[:, :, 3].astype(np.float32) * layer_alpha).astype(np.uint8)
            cur_layer = Image.fromarray(arr, "RGBA")
        base_img.alpha_composite(cur_layer)
        self.surface.image = base_img
        self.surface.draw = ImageDraw.Draw(self.surface.image, "RGBA")
        self.tx, self.ty, self.sx, self.sy = old_tx, old_ty, old_sx, old_sy
        self.alpha_factor = old_alpha

    def drawImage(self, snapshot, x, y):
        img = snapshot.image if hasattr(snapshot, "image") else snapshot
        pt = self._pt(x, y)
        self.surface.image.alpha_composite(img, (int(round(pt[0])), int(round(pt[1]))))

    def drawLine(self, x1, y1, x2, y2, paint):
        pt1 = self._pt(x1, y1)
        pt2 = self._pt(x2, y2)
        sw = max(1, int(round(paint.stroke_width * ((self.sx + self.sy) / 2))))
        col = self._col(paint)
        if col[3] <= 0:
            return
        if paint.mask_filter:
            # Blurred line
            sigma = paint.mask_filter.sigma
            w, h = self.surface.image.size
            glow_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            gd = ImageDraw.Draw(glow_img, "RGBA")
            gd.line([pt1, pt2], fill=col, width=sw)
            glow_img = glow_img.filter(ImageFilter.GaussianBlur(sigma))
            self.surface.image.alpha_composite(glow_img)
        else:
            self.surface.draw.line([pt1, pt2], fill=col, width=sw)

    def drawCircle(self, cx, cy, r, paint):
        pt = self._pt(cx, cy)
        rx = r * self.sx
        ry = r * self.sy
        col = self._col(paint)
        if col[3] <= 0:
            return
        bbox = [pt[0] - rx, pt[1] - ry, pt[0] + rx, pt[1] + ry]
        if paint.mask_filter:
            sigma = paint.mask_filter.sigma
            w, h = self.surface.image.size
            glow_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            gd = ImageDraw.Draw(glow_img, "RGBA")
            if paint.style == Paint.kStroke_Style:
                sw = max(1, int(round(paint.stroke_width * ((self.sx + self.sy) / 2))))
                gd.ellipse(bbox, outline=col, width=sw)
            else:
                gd.ellipse(bbox, fill=col)
            glow_img = glow_img.filter(ImageFilter.GaussianBlur(sigma))
            self.surface.image.alpha_composite(glow_img)
        else:
            if paint.style == Paint.kStroke_Style:
                sw = max(1, int(round(paint.stroke_width * ((self.sx + self.sy) / 2))))
                self.surface.draw.ellipse(bbox, outline=col, width=sw)
            else:
                self.surface.draw.ellipse(bbox, fill=col)

    def drawOval(self, rect, paint):
        pt1 = self._pt(rect.l, rect.t)
        pt2 = self._pt(rect.r, rect.b)
        bbox = [pt1[0], pt1[1], pt2[0], pt2[1]]
        col = self._col(paint)
        if col[3] <= 0:
            return
        if paint.mask_filter:
            sigma = paint.mask_filter.sigma
            w, h = self.surface.image.size
            glow_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            gd = ImageDraw.Draw(glow_img, "RGBA")
            if paint.style == Paint.kStroke_Style:
                sw = max(1, int(round(paint.stroke_width * ((self.sx + self.sy) / 2))))
                gd.ellipse(bbox, outline=col, width=sw)
            else:
                gd.ellipse(bbox, fill=col)
            glow_img = glow_img.filter(ImageFilter.GaussianBlur(sigma))
            self.surface.image.alpha_composite(glow_img)
        else:
            if paint.style == Paint.kStroke_Style:
                sw = max(1, int(round(paint.stroke_width * ((self.sx + self.sy) / 2))))
                self.surface.draw.ellipse(bbox, outline=col, width=sw)
            else:
                self.surface.draw.ellipse(bbox, fill=col)

    def drawRect(self, rect, paint):
        pt1 = self._pt(rect.l, rect.t)
        pt2 = self._pt(rect.r, rect.b)
        bbox = [pt1[0], pt1[1], pt2[0], pt2[1]]
        col = self._col(paint)
        if paint.shader and isinstance(paint.shader, GradientShader):
            # Radial gradient shader emulation
            sh = paint.shader
            cx, cy = sh.center
            c_pt = self._pt(cx, cy)
            rad = sh.radius * ((self.sx + self.sy) / 2)
            w, h = self.surface.image.size
            # Draw gradient circle onto overlay
            overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            od = ImageDraw.Draw(overlay, "RGBA")
            c0 = sh.colors[0]
            if isinstance(c0, (tuple, list)):
                col0 = (int(c0[0]), int(c0[1]), int(c0[2]), int(c0[3] * self.alpha_factor))
            else:
                col0 = (c0 >> 16 & 0xFF, c0 >> 8 & 0xFF, c0 & 0xFF, int((c0 >> 24 & 0xFF) * self.alpha_factor))
            for step in range(24, 0, -1):
                cur_r = rad * (step / 24.0)
                cur_a = int(col0[3] * (1.0 - (step / 24.0)))
                od.ellipse([c_pt[0] - cur_r, c_pt[1] - cur_r, c_pt[0] + cur_r, c_pt[1] + cur_r],
                           fill=(col0[0], col0[1], col0[2], cur_a))
            self.surface.image.alpha_composite(overlay)
            return

        if col[3] <= 0:
            return
        if paint.mask_filter:
            sigma = paint.mask_filter.sigma
            w, h = self.surface.image.size
            glow_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            gd = ImageDraw.Draw(glow_img, "RGBA")
            if paint.style == Paint.kStroke_Style:
                sw = max(1, int(round(paint.stroke_width * ((self.sx + self.sy) / 2))))
                gd.rectangle(bbox, outline=col, width=sw)
            else:
                gd.rectangle(bbox, fill=col)
            glow_img = glow_img.filter(ImageFilter.GaussianBlur(sigma))
            self.surface.image.alpha_composite(glow_img)
        else:
            if paint.style == Paint.kStroke_Style:
                sw = max(1, int(round(paint.stroke_width * ((self.sx + self.sy) / 2))))
                self.surface.draw.rectangle(bbox, outline=col, width=sw)
            else:
                self.surface.draw.rectangle(bbox, fill=col)

    def drawRRect(self, rrect, paint):
        r = rrect.rect
        rx = rrect.rx * self.sx
        pt1 = self._pt(r.l, r.t)
        pt2 = self._pt(r.r, r.b)
        bbox = [pt1[0], pt1[1], pt2[0], pt2[1]]
        col = self._col(paint)
        if col[3] <= 0:
            return
        if paint.mask_filter:
            sigma = paint.mask_filter.sigma
            w, h = self.surface.image.size
            glow_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            gd = ImageDraw.Draw(glow_img, "RGBA")
            if paint.style == Paint.kStroke_Style:
                sw = max(1, int(round(paint.stroke_width * ((self.sx + self.sy) / 2))))
                gd.rounded_rectangle(bbox, radius=int(rx), outline=col, width=sw)
            else:
                gd.rounded_rectangle(bbox, radius=int(rx), fill=col)
            glow_img = glow_img.filter(ImageFilter.GaussianBlur(sigma))
            self.surface.image.alpha_composite(glow_img)
        else:
            if paint.style == Paint.kStroke_Style:
                sw = max(1, int(round(paint.stroke_width * ((self.sx + self.sy) / 2))))
                self.surface.draw.rounded_rectangle(bbox, radius=int(rx), outline=col, width=sw)
            else:
                self.surface.draw.rounded_rectangle(bbox, radius=int(rx), fill=col)

    def drawArc(self, rect, start_deg, sweep_deg, use_center, paint):
        pt1 = self._pt(rect.l, rect.t)
        pt2 = self._pt(rect.r, rect.b)
        bbox = [pt1[0], pt1[1], pt2[0], pt2[1]]
        col = self._col(paint)
        if col[3] <= 0:
            return
        sw = max(1, int(round(paint.stroke_width * ((self.sx + self.sy) / 2))))
        self.surface.draw.arc(bbox, start=start_deg, end=start_deg + sweep_deg, fill=col, width=sw)

    def drawPath(self, path, paint):
        subpaths = path.get_all_subpaths()
        if not subpaths:
            return
        col = self._col(paint)
        if col[3] <= 0:
            return
        sw = max(1, int(round(paint.stroke_width * ((self.sx + self.sy) / 2))))
        for sp in subpaths:
            if len(sp) < 2:
                continue
            pts = [self._pt(x, y) for (x, y) in sp]
            if paint.mask_filter:
                sigma = paint.mask_filter.sigma
                w, h = self.surface.image.size
                glow_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                gd = ImageDraw.Draw(glow_img, "RGBA")
                if paint.style == Paint.kStroke_Style:
                    gd.line(pts, fill=col, width=sw)
                else:
                    gd.polygon(pts, fill=col)
                glow_img = glow_img.filter(ImageFilter.GaussianBlur(sigma))
                self.surface.image.alpha_composite(glow_img)
            else:
                if paint.style == Paint.kStroke_Style:
                    self.surface.draw.line(pts, fill=col, width=sw)
                else:
                    self.surface.draw.polygon(pts, fill=col)

    def drawString(self, text, x, y, font, paint):
        if not text:
            return
        pt = self._pt(x, y)
        col = self._col(paint)
        if col[3] <= 0:
            return
        pil_font = font._pil_font
        # In Skia, y is baseline coordinate.
        # In Pillow, y is top coordinate. Adjust by font ascent (~0.8 * size).
        adjusted_y = pt[1] - font.size * 0.8
        if paint.mask_filter:
            sigma = paint.mask_filter.sigma
            w, h = self.surface.image.size
            glow_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            gd = ImageDraw.Draw(glow_img, "RGBA")
            gd.text((pt[0], adjusted_y), text, font=pil_font, fill=col)
            glow_img = glow_img.filter(ImageFilter.GaussianBlur(sigma))
            self.surface.image.alpha_composite(glow_img)
        else:
            self.surface.draw.text((pt[0], adjusted_y), text, font=pil_font, fill=col)

class Surface:
    def __init__(self, w, h):
        self.width = int(w)
        self.height = int(h)
        self.image = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 255))
        self.draw = ImageDraw.Draw(self.image, "RGBA")
        self._canvas = Canvas(self)

    def getCanvas(self):
        return self._canvas

    def makeImageSnapshot(self):
        return ImageSnapshot(self.image)
