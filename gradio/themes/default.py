from __future__ import annotations

from collections.abc import Iterable

from gradio.themes.base import Base
from gradio.themes.utils import colors, fonts, sizes


class Default(Base):
    def __init__(
        self,
        *,
        primary_hue: colors.Color | str = colors.orange,
        secondary_hue: colors.Color | str = colors.blue,
        neutral_hue: colors.Color | str = colors.zinc,
        spacing_size: sizes.Size | str = sizes.spacing_md,
        radius_size: sizes.Size | str = sizes.radius_md,
        text_size: sizes.Size | str = sizes.text_md,
        font: fonts.Font | str | Iterable[fonts.Font | str] = (
            fonts.GoogleFont("Source Sans Pro"),
            "ui-sans-serif",
            "system-ui",
            "sans-serif",
        ),
        font_mono: fonts.Font | str | Iterable[fonts.Font | str] = (
            fonts.LocalFont("IBM Plex Mono"),
            "ui-monospace",
            "Consolas",
            "monospace",
        ),
    ):
        super().__init__(
            primary_hue=primary_hue,
            secondary_hue=secondary_hue,
            neutral_hue=neutral_hue,
            spacing_size=spacing_size,
            radius_size=radius_size,
            text_size=text_size,
            font=font,
            font_mono=font_mono,
        )
        self.name = "default"
        super().set(
            # Colors
            input_background_fill_dark="*neutral_800",
            error_background_fill=colors.red.c50,
            error_background_fill_dark="*neutral_900",
            error_border_color=colors.red.c700,
            error_border_color_dark=colors.red.c500,
            error_icon_color=colors.red.c700,
            error_icon_color_dark=colors.red.c500,
            # Shadows — softer, more layered
            shadow_drop="0 1px 3px rgba(0,0,0,0.07), 0 1px 2px rgba(0,0,0,0.05)",
            shadow_drop_lg="0 4px 14px rgba(0,0,0,0.1), 0 2px 6px rgba(0,0,0,0.06)",
            shadow_inset="0 1px 2px rgba(0,0,0,0.04) inset",
            shadow_spread="4px",
            shadow_spread_dark="2px",
            # Input focus glow
            input_shadow_focus="0 0 0 *shadow_spread *secondary_50, *shadow_inset",
            input_shadow_focus_dark="0 0 0 *shadow_spread *neutral_700, *shadow_inset",
            # Button borders
            button_border_width="1px",
            input_border_width="1px",
            input_background_fill="white",
            # Smoother, more satisfying transitions
            button_transition="all 0.2s cubic-bezier(0.4, 0, 0.2, 1)",
            button_transform_hover="translateY(-1px)",
            button_transform_active="translateY(0px)",
            # Gradients
            stat_background_fill="linear-gradient(to right, *primary_400, *primary_200)",
            stat_background_fill_dark="linear-gradient(to right, *primary_400, *primary_600)",
            checkbox_label_background_fill="*background_fill_primary",
            checkbox_label_background_fill_dark="*neutral_800",
            checkbox_label_background_fill_hover="*background_fill_secondary",
            checkbox_label_background_fill_hover_dark="*checkbox_label_background_fill",
            # Primary Button — subtle gradient + glow shadow
            button_primary_background_fill="linear-gradient(135deg, *primary_500, *primary_400)",
            button_primary_background_fill_dark="linear-gradient(135deg, *primary_600, *primary_500)",
            button_primary_background_fill_hover="linear-gradient(135deg, *primary_600, *primary_500)",
            button_primary_background_fill_hover_dark="linear-gradient(135deg, *primary_700, *primary_600)",
            button_primary_border_color="*primary_600",
            button_primary_border_color_dark="*primary_700",
            button_primary_border_color_hover="*primary_700",
            button_primary_border_color_hover_dark="*primary_800",
            button_primary_text_color="white",
            button_primary_text_color_dark="white",
            button_primary_shadow="0 2px 8px rgba(0,0,0,0.15)",
            button_primary_shadow_hover="0 4px 12px rgba(0,0,0,0.2)",
            # Secondary Button
            button_secondary_background_fill="*neutral_200",
            button_secondary_background_fill_dark="*neutral_600",
            button_secondary_background_fill_hover="*neutral_300",
            button_secondary_background_fill_hover_dark="*neutral_700",
            button_secondary_border_color="*neutral_300",
            button_secondary_border_color_dark="*neutral_500",
            button_secondary_border_color_hover="*neutral_400",
            button_secondary_border_color_hover_dark="*neutral_400",
            button_secondary_text_color="black",
            button_secondary_text_color_dark="white",
            # Cancel Button
            button_cancel_background_fill=colors.red.c500,
            button_cancel_background_fill_dark=colors.red.c700,
            button_cancel_background_fill_hover=colors.red.c600,
            button_cancel_background_fill_hover_dark=colors.red.c800,
            button_cancel_border_color=colors.red.c600,
            button_cancel_border_color_dark=colors.red.c800,
            button_cancel_border_color_hover=colors.red.c700,
            button_cancel_border_color_hover_dark=colors.red.c900,
            button_cancel_text_color="white",
            button_cancel_text_color_dark="white",
            button_cancel_text_color_hover="white",
            button_cancel_text_color_hover_dark="white",
            # Other
            border_color_accent_subdued="*primary_200",
            # Block shadow — softer, more modern
            block_shadow="0 1px 3px rgba(0,0,0,0.06)",
            block_shadow_dark="0 1px 3px rgba(0,0,0,0.3)",
        )
