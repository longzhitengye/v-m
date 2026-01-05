from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def hex_to_bgr(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    return (b, g, r)


def _odd(k: int) -> int:
    return k if (k % 2 == 1) else (k + 1)


def _kernel_from_size(h: int, w: int, frac: float, min_k: int, max_k: int) -> int:
    k = int(max(3, round(min(h, w) * frac)))
    k = max(min_k, min(max_k, k))
    return _odd(k)


def _pctl(x: np.ndarray, q: float) -> float:
    # 关键：np.asarray + float(...)，避免 Pylance 对 percentile 的误报
    return float(np.percentile(np.asarray(x, dtype=np.float32), q))


def analyze_paper_texture_and_lighting(paper_bgr: np.ndarray, out_hw: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    if paper_bgr.ndim == 3:
        gray = cv2.cvtColor(paper_bgr, cv2.COLOR_BGR2GRAY)
    else:
        gray = paper_bgr

    gray_f = gray.astype(np.float32) / 255.0
    ph, pw = gray_f.shape[:2]

    k_light = _kernel_from_size(ph, pw, frac=0.10, min_k=31, max_k=151)
    lighting = cv2.GaussianBlur(gray_f, (k_light, k_light), 0).astype(np.float32)

    high = (gray_f - lighting).astype(np.float32)

    tex = np.abs(high).astype(np.float32)
    p1 = _pctl(tex, 5.0)
    p95 = _pctl(tex, 95.0)
    tex = (tex - p1) / (p95 - p1 + 1e-6)
    tex = np.clip(tex, 0.0, 1.0)
    tex = np.power(tex, 0.8).astype(np.float32)

    l_p1 = _pctl(lighting, 1.0)
    l_p99 = _pctl(lighting, 99.0)
    lighting_n = (lighting - l_p1) / (l_p99 - l_p1 + 1e-6)
    lighting_n = np.clip(lighting_n, 0.0, 1.0).astype(np.float32)

    out_h, out_w = out_hw
    tex_rs = cv2.resize(tex, (out_w, out_h), interpolation=cv2.INTER_LINEAR).astype(np.float32)
    light_rs = cv2.resize(lighting_n, (out_w, out_h), interpolation=cv2.INTER_LINEAR).astype(np.float32)
    return tex_rs, light_rs


def generate_perlin_like_noise(shape: tuple[int, int], scale: int = 80) -> np.ndarray:
    h, w = shape
    sh, sw = max(1, h // scale), max(1, w // scale)
    n = np.random.randn(sh + 1, sw + 1).astype(np.float32)
    n = cv2.resize(n, (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32)
    n = (n - float(n.mean())) / (float(n.std()) + 1e-6)
    n = np.clip(n, -2.0, 2.0) / 2.0
    return n.astype(np.float32)


def extract_text_mask_from_white_bg(text_bgr: np.ndarray, *, invert: bool = True) -> np.ndarray:
    if text_bgr.ndim == 3:
        gray = cv2.cvtColor(text_bgr, cv2.COLOR_BGR2GRAY)
    else:
        gray = text_bgr

    blur = cv2.GaussianBlur(gray, (3, 3), 0)

    if invert:
        _, m = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    else:
        _, m = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    m = cv2.medianBlur(m, 3)
    return m.astype(np.uint8)


def texture_modulated_diffusion(mask_u8: np.ndarray, texture01: np.ndarray, iterations: int = 3) -> np.ndarray:
    result = mask_u8.astype(np.float32) / 255.0
    diffusion_strength = (0.45 + texture01 * 0.55).astype(np.float32)

    for _ in range(iterations):
        angle = float(np.random.uniform(0.0, 180.0))

        size = 5
        kernel = np.zeros((size, size), dtype=np.float32)
        cv2.ellipse(
            kernel,
            (size // 2, size // 2),
            (size // 2, max(1, size // 3)),
            angle,
            0,
            360,
            1,
            -1,
        )
        kernel = kernel / (float(kernel.sum()) + 1e-6)

        diffused = cv2.filter2D(result, -1, kernel).astype(np.float32)

        edge_weight = (1.0 - np.power(result, 2.0)).astype(np.float32)
        delta = (diffused - result) * edge_weight

        result = result + delta * 0.28 * diffusion_strength
        result = np.clip(result, 0.0, 1.0).astype(np.float32)

    return result


def add_stroke_variation(mask_u8: np.ndarray, texture01: np.ndarray, strength: float = 0.28) -> np.ndarray:
    if int(mask_u8.max()) < 1:
        return mask_u8

    mask_bin = ((mask_u8 > 127).astype(np.uint8) * 255).astype(np.uint8)
    dist = cv2.distanceTransform(mask_bin, cv2.DIST_L2, 5).astype(np.float32)
    dist_norm = dist / (float(dist.max()) + 1e-6)

    h, w = mask_u8.shape
    noise = generate_perlin_like_noise((h, w), scale=60)

    edge_zone = (1.0 - dist_norm).astype(np.float32)
    texture_factor = (0.75 + texture01 * 0.7).astype(np.float32)

    var = (1.0 + noise * strength * edge_zone * texture_factor).astype(np.float32)
    var = np.clip(var, 0.55, 1.55).astype(np.float32)

    mf = (mask_u8.astype(np.float32) / 255.0) * var
    mf = np.clip(mf, 0.0, 1.0).astype(np.float32)
    return (mf * 255.0).astype(np.uint8)


def create_ink_amount_mask(
    text_mask_u8: np.ndarray,
    texture01: np.ndarray,
    *,
    edge_diffusion: int = 3,
    stroke_variation: float = 0.28,
    feather_amount: float = 0.18,
) -> np.ndarray:
    mask_var = add_stroke_variation(text_mask_u8, texture01, strength=stroke_variation)
    ink01 = texture_modulated_diffusion(mask_var, texture01, iterations=edge_diffusion)

    if feather_amount > 0:
        h, w = text_mask_u8.shape
        n = np.random.randn(h, w).astype(np.float32)
        n = cv2.GaussianBlur(n, (3, 3), 0).astype(np.float32)

        mask_bin = ((text_mask_u8 > 127).astype(np.uint8) * 255).astype(np.uint8)
        dist = cv2.distanceTransform(mask_bin, cv2.DIST_L2, 5).astype(np.float32)
        dist_norm = dist / (float(dist.max()) + 1e-6)
        edge_zone = np.exp(-dist_norm * 4.0).astype(np.float32)

        feather_mod = (n * (0.65 + texture01 * 0.7)).astype(np.float32)
        ink01 = ink01 + feather_mod * feather_amount * edge_zone * ink01
        ink01 = np.clip(ink01, 0.0, 1.0).astype(np.float32)

    ink01 = np.power(ink01, 0.85).astype(np.float32)
    return ink01


def generate_ink_layer(
    *,
    paper_path: str,
    text_path: str,
    output_path: str,
    ink_color: str | tuple[int, int, int] = "#2b1a12",
    edge_diffusion: int = 3,
    stroke_variation: float = 0.28,
    feather_amount: float = 0.18,
    adapt_lighting: bool = True,
    lighting_strength: float = 0.25,
) -> np.ndarray:
    paper = cv2.imread(paper_path, cv2.IMREAD_COLOR)
    text_img = cv2.imread(text_path, cv2.IMREAD_COLOR)
    assert paper is not None, f"无法读取纸张: {paper_path}"
    assert text_img is not None, f"无法读取文字: {text_path}"

    ink_bgr = hex_to_bgr(ink_color) if isinstance(ink_color, str) else ink_color

    h, w = text_img.shape[:2]

    texture01, lighting01 = analyze_paper_texture_and_lighting(paper, (h, w))
    text_mask = extract_text_mask_from_white_bg(text_img, invert=True)

    ink_amount01 = create_ink_amount_mask(
        text_mask,
        texture01,
        edge_diffusion=edge_diffusion,
        stroke_variation=stroke_variation,
        feather_amount=feather_amount,
    )

    if adapt_lighting:
        lf = (1.0 - (1.0 - lighting01) * lighting_strength).astype(np.float32)
        ink_amount01 = np.clip(ink_amount01 * lf, 0.0, 1.0).astype(np.float32)

    # 获取纸张对应区域
    paper_resized = cv2.resize(paper, (w, h), interpolation=cv2.INTER_LINEAR)

    # === 乘法混合 (multiply blend) ===
    # 墨水是让纸张变暗，而不是覆盖纸张
    # 将墨色归一化到 [0,1]
    ink_norm = np.array(ink_bgr, dtype=np.float32) / 255.0

    # 基础墨量：纹理深处墨更多
    base_ink = ink_amount01 * (0.7 + texture01 * 0.3)

    # 添加干笔效果 - 笔画内不均匀
    dry_brush = generate_perlin_like_noise((h, w), scale=40)
    base_ink = base_ink * (0.85 + dry_brush * 0.3)
    base_ink = np.clip(base_ink, 0.0, 1.0)

    # 乘法混合: result = paper * (1 - ink * (1 - ink_color))
    # 墨色越深，纸张被压暗越多
    paper_f = paper_resized.astype(np.float32) / 255.0

    # 计算每个通道的暗化系数
    darken = 1.0 - base_ink[:, :, None] * (1.0 - ink_norm)

    # 应用乘法混合
    out_f = paper_f * darken
    out = np.clip(out_f * 255.0, 0.0, 255.0).astype(np.uint8)

    # alpha 用原始 ink_amount
    alpha = (ink_amount01 * 255).astype(np.uint8)
    bgra = np.dstack((out, alpha)).astype(np.uint8)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(output_path, bgra)
    return bgra


def preview_ink_on_frame(*, frame_path: str, ink_path: str, output_path: str) -> np.ndarray:
    frame = cv2.imread(frame_path, cv2.IMREAD_COLOR)
    ink = cv2.imread(ink_path, cv2.IMREAD_UNCHANGED)  # 读取 BGRA
    assert frame is not None, f"无法读取 frame: {frame_path}"
    assert ink is not None, f"无法读取 ink: {ink_path}"

    # 如果 ink 是 BGRA，使用 alpha 通道
    if ink.shape[2] == 4:
        alpha = ink[:, :, 3:4].astype(np.float32) / 255.0
        ink_bgr = ink[:, :, :3]

        # alpha 混合: out = frame * (1-alpha) + ink * alpha
        frame_f = frame.astype(np.float32)
        ink_f = ink_bgr.astype(np.float32)
        out_f = frame_f * (1.0 - alpha) + ink_f * alpha
        out = np.clip(out_f, 0, 255).astype(np.uint8)
    else:
        # 兼容旧版 RGB
        ink_gray = cv2.cvtColor(ink, cv2.COLOR_BGR2GRAY).astype(np.float32)
        alpha = (255.0 - ink_gray) / 255.0
        alpha = np.clip(alpha, 0.0, 1.0)

        frame_f = frame.astype(np.float32)
        ink_f = ink.astype(np.float32)
        out_f = frame_f * (1.0 - alpha[:, :, None]) + ink_f * alpha[:, :, None]
        out = np.clip(out_f, 0, 255).astype(np.uint8)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(output_path, out)
    return out

