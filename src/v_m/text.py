from pathlib import Path
from typing import Any

from handright import Template, handwrite
from PIL import Image, ImageFont, ImageOps


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """将十六进制颜色转换为 RGB 元组

    Args:
        hex_color: 十六进制颜色字符串，如 "#ffffff" 或 "#fff"

    Returns:
        RGB 元组，如 (255, 255, 255)
    """
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _crop_to_ink(img_1bit: Image.Image, pad: int = 14) -> Image.Image:
    inv = ImageOps.invert(img_1bit.convert("L"))
    bbox = inv.getbbox()
    if not bbox:
        return img_1bit
    x0, y0, x1, y1 = bbox
    x0 = max(0, x0 - pad)
    y0 = max(0, y0 - pad)
    x1 = min(img_1bit.width, x1 + pad)
    y1 = min(img_1bit.height, y1 + pad)
    return img_1bit.crop((x0, y0, x1, y1))


def gen_text(
    text: str,
    out: str | Path,
    font: str | Path,
    size: int = 100,
    pad: int = 14,
    gap: int = 18,
    direction: str = "垂直",
    text_color: str | None = None,
) -> bool:
    """
    生成手写文字图片（透明背景）

    Args:
        text: 要生成的文字
        font: 字体文件路径
        size: 字体大小
        out: 输出文件路径
        pad: 单字裁剪留白像素
        gap: 字间距像素
        direction: 文字方向, "水平" 或 "垂直"
        text_color: 文字颜色十六进制，如 "#ff0000" 为红色，默认 "#000000" 黑色

    Returns:
        bool: 成功返回True,失败返回False
    """
    try:
        font_path = Path(font)
        output_path = Path(out)

        # 检查字体文件是否存在
        if not font_path.exists():
            print(f"错误: 字体文件未找到: {font_path}")
            return False

        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 设置默认文字颜色
        if text_color is None:
            text_color = "#000000"  # 黑色
        rgb_color = _hex_to_rgb(text_color)

        template = Template(
            background=Image.new(mode="1", size=(200, 200), color=1),
            font=ImageFont.truetype(str(font_path), size=size),
        )

        character_images = []
        for ch in text:
            imgs = list(handwrite(ch, template))
            if not imgs:
                continue
            # 裁剪并转换为 RGBA 模式，应用颜色
            cropped = _crop_to_ink(imgs[0], pad=pad)
            # 创建 RGBA 图像，透明背景
            img_rgba = Image.new("RGBA", cropped.size, (0, 0, 0, 0))
            # 将黑白图像作为蒙版，应用文字颜色
            # handright 生成的是白底黑字，需要反转蒙版
            mask = ImageOps.invert(cropped.convert("L"))
            # 阈值处理消除灰度边缘的小白点
            mask = mask.point(lambda x: 255 if x > 128 else 0)
            # 创建文字颜色的图层
            text_layer = Image.new("RGBA", cropped.size, (*rgb_color, 255))
            # 使用蒙版合成文字
            img_rgba.paste(text_layer, (0, 0), mask)
            character_images.append(img_rgba)

        if not character_images:
            print("错误: 没有生成任何字符图片")
            return False

        if direction == "垂直":
            # 竖排文字
            col_width = max(img.width for img in character_images)
            total_height = sum(img.height for img in character_images) + gap * (len(character_images) - 1)

            vertical_image = Image.new("RGBA", (col_width, total_height), (0, 0, 0, 0))

            y = 0
            for img in character_images:
                x = (col_width - img.width) // 2
                vertical_image.paste(img, (x, y), img)
                y += img.height + gap

            vertical_image.save(output_path)
            print(f"竖排文字图片已生成：{output_path}")
        else:
            # 水平文字
            max_height = max(img.height for img in character_images)
            total_width = sum(img.width for img in character_images) + gap * (len(character_images) - 1)

            horizontal_image = Image.new("RGBA", (total_width, max_height), (0, 0, 0, 0))

            x = 0
            for img in character_images:
                y = (max_height - img.height) // 2
                horizontal_image.paste(img, (x, y), img)
                x += img.width + gap

            horizontal_image.save(output_path)
            print(f"水平文字图片已生成：{output_path}")

        return True

    except Exception as e:
        print(f"生成竖排文字时出错: {e}")
        return False


def composite_text_to_image(
    text_items: list[dict[str, Any]],
    out: str | Path,
    width: int,
    height: int,
    font: str | Path,
    size: int = 100,
    pad: int = 4,
    gap: int = 4,
    direction: str = "垂直",
    background_color: str | None = None,
    text_color: str | None = None,
    scale: float = 1.0,
) -> bool:
    """
    合成多个文字到一张底图上

    Args:
        text_items: 文字项列表, 每项包含 x, y, text 字段, 例如 [{x: 10, y: 20, text: "你好"}]
        out: 输出文件路径
        width: 底图宽度
        height: 底图高度
        font: 字体文件路径
        size: 字体大小
        pad: 单字裁剪留白像素
        gap: 字间距像素
        direction: 文字方向, "水平" 或 "垂直"
        background_color: 背景颜色十六进制，默认 "#ffffff" 白色
        text_color: 文字颜色十六进制，默认 "#000000" 黑色
        scale: 文字缩放比例 (默认 1.0)

    Returns:
        bool: 成功返回True, 失败返回False
    """
    try:
        font_path = Path(font)
        output_path = Path(out)

        # 检查字体文件是否存在
        if not font_path.exists():
            print(f"错误: 字体文件未找到: {font_path}")
            return False

        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 设置默认颜色
        if text_color is None:
            text_color = "#000000"  # 黑色
        if background_color is None:
            background_color = "#ffffff"  # 白色

        bg_rgb = _hex_to_rgb(background_color)
        # 创建底图
        base_image = Image.new("RGBA", (width, height), (*bg_rgb, 255))

        # 为每个文字项生成图片并合成到底图上
        for item in text_items:
            x = item.get("x", 0)
            y = item.get("y", 0)
            text = item.get("text", "")

            if not text:
                continue

            # 临时文件路径用于保存单个文字图片
            temp_path = output_path.parent / f"temp_{id(item)}.png"

            # 生成单个文字图片（透明背景）
            success = gen_text(
                text=text,
                out=temp_path,
                font=font_path,
                size=size,
                pad=pad,
                gap=gap,
                direction=direction,
                text_color=text_color,
            )

            if not success:
                print(f"警告: 生成文字 '{text}' 失败, 跳过")
                continue

            # 加载生成的文字图片
            text_img = Image.open(temp_path).convert("RGBA")

            # 应用缩放
            if scale != 1.0:
                new_width = int(text_img.width * scale)
                new_height = int(text_img.height * scale)
                text_img = text_img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # 合成到底图上，使用 alpha 通道
            base_image.paste(text_img, (x, y), text_img)

            # 删除临时文件
            temp_path.unlink()

        # 保存最终合成图片
        base_image.save(output_path)
        print(f"合成文字图片已生成：{output_path}")
        return True

    except Exception as e:
        print(f"合成文字时出错: {e}")
        return False
