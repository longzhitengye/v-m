# 实验记录

## 尝试 1 - 初始状态
- 参数: `edge_diffusion=3, stroke_variation=0.28, feather_amount=0.18, lighting_strength=0.25`
- 问题: 白边，墨迹浮在纸面上

## 尝试 2 - RGBA 输出
- 修改 `generate_ink_layer` 输出 BGRA 格式，alpha 通道 = ink_amount
- 修改 `preview_ink_on_frame` 使用 alpha 通道混合
- 结果: 白边消失，但墨迹仍"浮"

## 尝试 3 - 纸张纹理线性混合
- 用纸张颜色作为基底，墨迹通过线性混合与纸张结合
- `ink_strength = ink_amount * 0.92` 保留部分纸张纹理
- 结果: 纸张纹理透过墨迹显示，效果更自然

## 尝试 4 - 乘法混合 (multiply blend) + 干笔效果
- 墨水通过乘法混合让纸张变暗，而非覆盖纸张
- `darken = 1 - ink * (1 - ink_color)` 类似 Photoshop 正片叠底
- 添加干笔效果：笔画内不均匀，纹理深处墨更多
- 墨色改用 `#1a1a1a` 深灰而非纯黑

## 最终参数
- `ink_color="#1a1a1a"` - 深灰色墨
- `edge_diffusion=6` - 边缘扩散
- `stroke_variation=0.4` - 笔画变化
- `feather_amount=0.3` - 羽化
- `lighting_strength=0.5` - 光照适应
