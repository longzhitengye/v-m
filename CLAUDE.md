# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

生成毛笔书法效果的程序。流程：

1. **`composite_text_to_image`** - 使用 `handright` 生成基础手写文字
2. **`generate_ink_layer`** - 分析纸张材质 (`PAPER`) 的纹理和光照，将基础文字处理成有墨迹效果的文字（**这是最终需要的输出**）
3. **`preview_ink_on_frame`** - 预览检查，把处理后的文字叠加到背景图上，看效果是否自然

## Development Commands

```bash
# Run all linters/formatters
pre-commit run --all-files

# Individual tools
ruff check src/          # Lint
ruff format src/         # Format
pyright src/             # Type check

# Run the main entry point
poetry run dev
```

## Code Style

- Line length: 120
- Python: 3.12+
- Double quotes, black-compatible isort
