"""
Задание «Вывести время с тенью»

  t - показать/скрыть часы, Esc - выход
"""
import argparse
import colorsys
import datetime
import math
import os
import sys
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 640, 480

# Шрифт НЕ как на занятии. Берём первый найденный (Windows -> Colab/Linux).
FONT_CANDIDATES = [
    "C:/Windows/Fonts/segoeprb.ttf",   # Segoe Print Bold (рукописный)
    "C:/Windows/Fonts/georgiab.ttf",   # Georgia Bold
    "C:/Windows/Fonts/comicbd.ttf",    # Comic Sans Bold
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
]


def load_font(size, custom=None):
    for p in ([custom] if custom else []) + FONT_CANDIDATES:
        if p and os.path.exists(p):
            return ImageFont.truetype(p, size), p
    return ImageFont.load_default(size), "default"


def hsv(h, s=1.0, v=1.0, a=255):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return int(r * 255), int(g * 255), int(b * 255), a


def add_clock(frame_bgr, now, t, font_big, font_small, pos=(24, 18)):
    """Рисует время и дату с тенью и меняющимися цветами."""
    base = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)).convert("RGBA")
    time_txt = now.strftime("%H:%M:%S")
    date_txt = now.strftime("%d.%m.%Y")
    x, y = pos
    y2 = y + font_big.size + 6

    # 1) Тень: рисуем чёрный текст на прозрачном слое со смещением и размываем
    shadow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    off = 6
    sd.text((x + off, y + off), time_txt, font=font_big, fill=(0, 0, 0, 220))
    sd.text((x + off // 2, y2 + off // 2), date_txt, font=font_small, fill=(0, 0, 0, 220))
    shadow = shadow.filter(ImageFilter.GaussianBlur(4))
    base = Image.alpha_composite(base, shadow)

    # 2) Цвета: оттенок плавно меняется во времени (полный круг за 12 секунд)
    hue = (t / 12.0) % 1.0
    main_col = hsv(hue, 0.85, 1.0)
    outline = hsv(hue + 0.5, 0.9, 0.45)          # тёмная обводка противоположного цвета
    date_col = hsv(hue + 0.5, 0.55, 1.0)         # дата - дополнительный цвет

    # 3) Основной текст поверх тени
    d = ImageDraw.Draw(base)
    d.text((x, y), time_txt, font=font_big, fill=main_col, stroke_width=2, stroke_fill=outline)
    d.text((x, y2), date_txt, font=font_small, fill=date_col, stroke_width=1, stroke_fill=outline)

    return cv2.cvtColor(np.asarray(base.convert("RGB")), cv2.COLOR_RGB2BGR)


def synthetic_frame(t):
    yy, xx = np.mgrid[0:H, 0:W]
    f = np.zeros((H, W, 3), np.uint8)
    f[..., 0] = (140 + 90 * np.sin(xx / 120 + t * 0.6)).astype(np.uint8)
    f[..., 1] = (120 + 70 * np.sin(yy / 90 - t * 0.4)).astype(np.uint8)
    f[..., 2] = (100 + 60 * np.sin((xx + yy) / 180 + t * 0.8)).astype(np.uint8)
    cv2.circle(f, (int(W / 2 + 180 * math.sin(t)), int(H / 2 + 100 * math.cos(t * 0.7))),
               40, (235, 235, 235), -1)
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--camera", default="0")
    ap.add_argument("--source", default=None, help="видеофайл вместо камеры")
    ap.add_argument("--font", default=None, help="путь к .ttf (по умолчанию - автоподбор)")
    ap.add_argument("--demo", action="store_true", help="без окна, запись в demo_clock.mp4")
    ap.add_argument("--save", default=None)
    ap.add_argument("--seconds", type=float, default=14)
    args = ap.parse_args()

    font_big, used = load_font(64, args.font)
    font_small, _ = load_font(28, args.font)
    print("Шрифт:", used)

    cap = None
    if not (args.demo and args.source is None):
        src = args.source if args.source is not None else args.camera
        if isinstance(src, str) and src.isdigit():
            src = int(src)
        cap = cv2.VideoCapture(src, cv2.CAP_DSHOW) if (isinstance(src, int) and sys.platform.startswith("win")) \
            else cv2.VideoCapture(src)
        if not cap.isOpened():
            sys.exit("Не удалось открыть видео. Попробуйте --camera 1, --source файл.mp4 или --demo.")

    fps = 20 if args.demo else 30
    out_path = args.save or ("demo_clock.mp4" if args.demo else None)
    writer = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (W, H)) if out_path else None

    is_clock = True
    start_dt = datetime.datetime.now()
    t_start = time.time()
    i = 0
    while True:
        t = i / fps if args.demo else time.time() - t_start
        if args.demo and t >= args.seconds:
            break

        if cap is None:
            image = synthetic_frame(t)
        else:
            ok, image = cap.read()
            if not ok:
                break
            image = cv2.resize(image, (W, H))

        # в демо «время» идёт от момента запуска по кадрам, чтобы секунды тикали в записи
        now = start_dt + datetime.timedelta(seconds=t) if args.demo else datetime.datetime.now()

        if is_clock:
            image = add_clock(image, now, t, font_big, font_small)

        if writer is not None:
            writer.write(image)
        if not args.demo:
            cv2.imshow("Clock with shadow", image)
            k = cv2.waitKey(1) & 0xFF
            if k == 27:
                break
            if k == ord("t"):
                is_clock = not is_clock
        i += 1

    if cap is not None:
        cap.release()
    if writer is not None:
        writer.release()
        print("Видео сохранено:", out_path)
    if not args.demo:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()