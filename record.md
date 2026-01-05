# 实验记录

## 尝试 1 - 初始状态
- 参数: `edge_diffusion=3, stroke_variation=0.28, feather_amount=0.18, lighting_strength=0.25`
- 问题: 白边，墨迹浮在纸面上

## 尝试 2 - RGBA 输出
- 修改 `generate_ink_layer` 输出 BGRA 格式，alpha 通道 = ink_amount
- 修改 `preview_ink_on_frame` 使用 alpha 通道混合
- 结果: 白边消失，但墨迹仍"浮"

## 尝试 3 - 纸张纹理混合
- 用纸张颜色作为基底，墨迹通过线性混合与纸张结合
- `ink_strength = ink_amount * 0.92` 保留部分纸张纹理
- 结果: 纸张纹理透过墨迹显示，效果更自然

## 最终参数
- `edge_diffusion=5` - 边缘扩散
- `stroke_variation=0.35` - 笔画变化
- `feather_amount=0.25` - 羽化
- `lighting_strength=0.4` - 光照适应
