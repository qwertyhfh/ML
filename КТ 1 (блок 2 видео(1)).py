"""
Задание «Сделать свой видео-продакшн»
  c  - показать свою подпись (плавно появляется и исчезает)
  l  - включить/выключить свой логотип (УСЛОЖНЁННЫЙ ВАРИАНТ: логотип анимирован -
       «переворачивается» как монета и покачивается)
  b  - чёрно-белый режим (из лекции), Esc - выход
"""
import argparse
import math
import os
import sys
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ============================ НАСТРОЙКИ (свои данные) ============================
MY_NAME = "Artyom"                     # <- ваше имя (только тут, в кавычках)
MY_SIGNATURE = f"Автор: {MY_NAME}"     # <- НЕ МЕНЯТЬ
MY_SUBTITLE = "Video Production · Python + OpenCV"
LOGO_LETTER = MY_NAME[0]               # <- НЕ МЕНЯТЬ
LOGO_COLOR = (30, 144, 255)            # цвет логотипа (R, G, B)
# ==================================================================================

W, H = 640, 480
FPS_LIVE = 30

FONT_CANDIDATES = [
    "C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def load_font(size):
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size)


# ---------------------------- картинки: подпись и логотип ----------------------------
def make_caption():
    """Плашка 640x80 с подписью (если нет my_caption.png)."""
    if os.path.exists("my_caption.png"):
        return Image.open("my_caption.png").convert("RGBA").resize((W, 80))
    img = Image.new("RGBA", (W, 80), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 80], fill=(10, 10, 20, 170))
    d.rectangle([0, 0, 8, 80], fill=LOGO_COLOR + (255,))
    d.text((28, 12), MY_SIGNATURE, font=load_font(30), fill=(255, 255, 255, 255))
    d.text((28, 50), MY_SUBTITLE, font=load_font(18), fill=(200, 210, 230, 255))
    return img


def make_logo(size=96):
    """Круглый логотип с буквой (если нет my_logo.png)."""
    if os.path.exists("my_logo.png"):
        return Image.open("my_logo.png").convert("RGBA").resize((size, size))
    s = size * 4  # рисуем в 4x и уменьшаем - гладкие края
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, s - 4, s - 4], fill=LOGO_COLOR + (255,))
    d.ellipse([s * 0.08, s * 0.08, s * 0.92, s * 0.92], outline=(255, 255, 255, 255), width=int(s * 0.04))
    f = load_font(int(s * 0.55))
    box = d.textbbox((0, 0), LOGO_LETTER, font=f)
    d.text(((s - (box[2] - box[0])) / 2 - box[0], (s - (box[3] - box[1])) / 2 - box[1]),
           LOGO_LETTER, font=f, fill=(255, 255, 255, 255))
    return img.resize((size, size), Image.LANCZOS)


def animate_logo(base, t):
    """Анимация логотипа: «монетка» (сжатие по ширине) + пульсация размера."""
    phase = t * 2 * math.pi / 2.5                      # один оборот за 2.5 с
    squeeze = max(abs(math.cos(phase)), 0.06)          # ширина 6%..100%
    pulse = 1.0 + 0.06 * math.sin(phase * 2)           # лёгкая пульсация
    w = max(int(base.width * squeeze * pulse), 2)
    h = int(base.height * pulse)
    img = base.resize((w, h), Image.LANCZOS)
    canvas = Image.new("RGBA", base.size, (0, 0, 0, 0))
    canvas.paste(img, ((base.width - w) // 2, (base.height - h) // 2))
    return canvas


def overlay(frame, rgba_img, x, y, opacity=1.0):
    """Накладывает RGBA-картинку на BGR-кадр с учётом прозрачности."""
    rgba = np.asarray(rgba_img, dtype=np.uint8)
    h, w = rgba.shape[:2]
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, frame.shape[1]), min(y + h, frame.shape[0])
    if x0 >= x1 or y0 >= y1 or opacity <= 0:
        return frame
    patch = rgba[y0 - y:y1 - y, x0 - x:x1 - x]
    a = patch[..., 3:4].astype(np.float32) / 255.0 * min(opacity, 1.0)
    bgr = patch[..., :3][..., ::-1].astype(np.float32)
    roi = frame[y0:y1, x0:x1].astype(np.float32)
    frame[y0:y1, x0:x1] = (roi * (1 - a) + bgr * a).astype(np.uint8)
    return frame


# ---------------------------- источник кадров ----------------------------
def synthetic_frame(t):
    """Фон для демо без камеры: плавный градиент + бегущий круг."""
    yy, xx = np.mgrid[0:H, 0:W]
    f = np.zeros((H, W, 3), np.uint8)
    f[..., 0] = (127 + 100 * np.sin(xx / 140 + t * 0.7)).astype(np.uint8)
    f[..., 1] = (110 + 80 * np.sin(yy / 110 - t * 0.5)).astype(np.uint8)
    f[..., 2] = (90 + 60 * np.sin((xx + yy) / 200 + t * 0.9)).astype(np.uint8)
    cx = int(W / 2 + 200 * math.sin(t * 1.1))
    cy = int(H / 2 + 120 * math.cos(t * 0.8))
    cv2.circle(f, (cx, cy), 45, (240, 240, 240), -1)
    cv2.putText(f, "demo video", (W // 2 - 80, H // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    return f


def open_source(args):
    if args.source is None and args.demo:
        return None  # синтетический фон
    src = args.source if args.source is not None else args.camera
    if isinstance(src, str) and src.isdigit():
        src = int(src)
    if isinstance(src, int) and sys.platform.startswith("win"):
        cap = cv2.VideoCapture(src, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        sys.exit("Не удалось открыть источник видео. Попробуйте --camera 1, --source файл.mp4 "
                 "или --demo (без камеры).")
    return cap


# ---------------------------- состояние эффектов ----------------------------
CAP_FADE_IN, CAP_HOLD, CAP_FADE_OUT = 1.0, 2.5, 1.0   # секунды


def caption_opacity(dt):
    """Плавное появление -> показ -> плавное исчезновение. None, если подпись закончилась."""
    if dt < 0:
        return None
    if dt < CAP_FADE_IN:
        return dt / CAP_FADE_IN
    if dt < CAP_FADE_IN + CAP_HOLD:
        return 1.0
    end = CAP_FADE_IN + CAP_HOLD + CAP_FADE_OUT
    if dt < end:
        return 1.0 - (dt - CAP_FADE_IN - CAP_HOLD) / CAP_FADE_OUT
    return None


def main():
    ap = argparse.ArgumentParser(description="Видео-продакшн: подпись (c) и логотип (l)")
    ap.add_argument("--camera", default="0", help="номер камеры (по умолчанию 0)")
    ap.add_argument("--source", default=None, help="путь к видеофайлу вместо камеры")
    ap.add_argument("--demo", action="store_true", help="без окна: сценарий нажатий + запись в файл")
    ap.add_argument("--save", default=None, help="записать результат в этот mp4")
    ap.add_argument("--seconds", type=float, default=16, help="длина демо, сек")
    args = ap.parse_args()

    cap = open_source(args)
    caption = make_caption()
    logo = make_logo()

    fps = FPS_LIVE
    if cap is not None and args.demo:
        fps = cap.get(cv2.CAP_PROP_FPS) or 25
    if args.demo:
        fps = min(fps, 30)
    out_path = args.save or ("demo_production.mp4" if args.demo else None)
    writer = None
    if out_path:
        writer = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (W, H))

    # сценарий нажатий для демо: (секунда, клавиша)
    script = [(1.5, "c"), (7.0, "l"), (9.5, "c"), (13.5, "l")] if args.demo else []

    is_logo, is_mono = False, False
    cap_t0, logo_t0 = None, None
    last_key, last_key_t = "", -10
    frame_idx = 0
    t_start = time.time()

    while True:
        t = frame_idx / fps if args.demo else time.time() - t_start

        # --- кадр ---
        if cap is None:
            image = synthetic_frame(t)
        else:
            ok, image = cap.read()
            if not ok:
                break
            image = cv2.resize(image, (W, H))
        if args.demo and t >= args.seconds:
            break

        # --- клавиши ---
        key = None
        if args.demo:
            while script and script[0][0] <= t:
                key = script.pop(0)[1]
        else:
            k = cv2.waitKey(max(1, int(1000 / fps))) & 0xFF
            if k == 27:
                break
            if k != 255:
                key = chr(k).lower()

        if key == "c":
            cap_t0 = t
        elif key == "l":
            is_logo = not is_logo
            logo_t0 = t
        elif key == "b":
            is_mono = not is_mono
        if key:
            last_key, last_key_t = key, t

        # --- эффекты ---
        if is_mono:
            image = cv2.cvtColor(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)

        if is_logo:
            fade = min((t - logo_t0) / 0.5, 1.0)                     # плавное появление логотипа
            bob = int(4 * math.sin(t * 3))                           # покачивание вверх-вниз
            image = overlay(image, animate_logo(logo, t), W - logo.width - 20, 15 + bob, fade)

        if cap_t0 is not None:
            op = caption_opacity(t - cap_t0)
            if op is None:
                cap_t0 = None
            else:
                image = overlay(image, caption, 0, H - 80, op)

        # --- подсказка и индикатор нажатой клавиши (чтобы было видно на записи экрана) ---
        cv2.putText(image, "[c] caption  [l] logo  [b] b/w  [Esc] exit", (10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        if t - last_key_t < 1.2:
            cv2.putText(image, f"key pressed: {last_key.upper()}", (10, H - 95),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2, cv2.LINE_AA)

        if writer is not None:
            writer.write(image)
        if not args.demo:
            cv2.imshow("TV show", image)
        frame_idx += 1

    if cap is not None:
        cap.release()
    if writer is not None:
        writer.release()
        print("Видео сохранено:", out_path)
    if not args.demo:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()