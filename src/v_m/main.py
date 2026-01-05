from src.v_m.config import DEFAULT_FONT_FILE, EFFECT_FRAME, EFFECTED_TEXT, GEN_TEXT, ORIGINAL_FRAME, PAPER
from v_m.effect import generate_ink_layer, preview_ink_on_frame
from v_m.text import composite_text_to_image


def main():
    composite_text_to_image(
        text_items=[{"x": 674, "y": 450, "text": "张大哥"}, {"x": 632, "y": 455, "text": "2025年12月31日"}],
        out=GEN_TEXT,
        width=1280,
        height=720,
        font=DEFAULT_FONT_FILE,
        size=92,
        scale=0.28,
    )
    generate_ink_layer(
        paper_path=str(PAPER),
        text_path=str(GEN_TEXT),
        output_path=str(EFFECTED_TEXT),
        ink_color="#000000",
        edge_diffusion=5,
        stroke_variation=0.35,
        feather_amount=0.25,
        adapt_lighting=True,
        lighting_strength=0.4,
    )
    preview_ink_on_frame(
        frame_path=str(ORIGINAL_FRAME),
        ink_path=str(EFFECTED_TEXT),
        output_path=str(EFFECT_FRAME),
    )
    print("Hello from v_m main!")
