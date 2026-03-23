from __future__ import annotations

import pandas as pd
import seaborn.objects as so
from seaborn import axes_style
import matplotlib.pyplot as plt

# -----------------------------
# Constants (module-level = shared by all functions in this file)
# -----------------------------
TECH_NAME_REPLACEMENT: dict[str, str] = {
    "T_LDV_C_DSL_EX": "DSL_EX",
    "T_LDV_C_DSL_N": "DSL",
    "T_LDV_C_GSL_EX": "GSL_EX",
    "T_LDV_C_GSL_N": "GSL",

    "T_LDV_C_CNG_N": "CNG",
    
    "T_LDV_C_BEV150_EX": "BEV150_EX",
    "T_LDV_C_BEV150_N": "BEV150",
    "T_LDV_C_BEV200_N": "BEV200",
    "T_LDV_C_BEV300_N": "BEV300",
    "T_LDV_C_BEV400_N": "BEV400",

    "T_LDV_C_GSL_HEV_EX": "GSL_HEV_EX",
    "T_LDV_C_GSL_HEV_N": "GSL_HEV",
    "T_LDV_C_GSL_PHEV35_EX": "GSL_PHEV35_EX",
    "T_LDV_C_GSL_PHEV35_N": "GSL_PHEV35",
    "T_LDV_C_GSL_PHEV50_N": "GSL_PHEV50",

    "T_LDV_C_FCEV400_N": "H2_FCEV400",
}

V_COLORS: dict[str, str] = {
    "BEV150": "#7795faff",
    "BEV150_EX": "#7796fa89",
    "BEV200": "#6486f8ff",
    "BEV300": "#3c67f4ff",
    "BEV400": "#1347f4ff",
    "CNG": "#888888",
    "DSL": "#712F22",
    "DSL_EX": "#712F2250",
    "FCEV400": "#ff02b3",
    "GSL_HEV": "#a01e1e",
    "GSL_HEV_EX": "#a01e1e8d",
    "GSL": "#891C1C7C",
    "GSL_EX": "#891C1C33",
    "GSL_PHEV35": "#FB9E3AC4",
    "GSL_PHEV50": "#ff8009",
}

THEME_DICT = {
    **axes_style("whitegrid"),
    "grid.linestyle": ":",
    "legend.frameon": False,
    "axes.spines.right": False,
    "axes.spines.top": False,

    # Font sizes
    "axes.titlesize": 16,     # plot title
    "axes.labelsize": 14,     # x / y labels
    "xtick.labelsize": 12,    # x tick labels
    "ytick.labelsize": 12,    # y tick labels
    "legend.fontsize": 12,    # legend text
    "legend.title_fontsize": 13,
}


# -----------------------------
# Helpers
# -----------------------------
def build_tech_palette(
    tech_values: pd.Series,
    replacement: dict[str, str] = TECH_NAME_REPLACEMENT,
    base_colors: dict[str, str] = V_COLORS,
    default_color: str = "#999999",
) -> dict[str, str]:
    """
    Returns a dict mapping *original tech codes* -> color hex.
    Falls back to default_color if a tech isn't covered.
    """
    palette: dict[str, str] = {}
    for tech in pd.unique(tech_values.dropna()):
        short = replacement.get(tech, tech)                 # map to friendly name if possible
        palette[tech] = base_colors.get(short, default_color)  # map to color if possible
    return palette


def replace_with_fallback(
    series: pd.Series,
    mapping: dict[str, str],
) -> pd.Series:
    """
    Replace values using mapping, falling back to original values if not found.
    """
    return series.map(mapping).fillna(series)


# -----------------------------
# Plot
# -----------------------------
def area_plot(
    df: pd.DataFrame,
    x: str,
    y: str,
    hue: str,
    *,
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    alpha: float = 0.7,
    theme: dict | None = None,
    palette: dict[str, str] | None = None,
):
        """
        Stacked area plot with seaborn.objects.

        Parameters
        ----------
        df : DataFrame
        x, y, hue : column names
        palette : optional mapping {hue_value -> color}. If not provided, uses TECH_NAME_REPLACEMENT + V_COLORS.
        """
        missing = [c for c in (x, y, hue) if c not in df.columns]
        if missing:
            raise KeyError(f"Missing columns in df: {missing}")

        theme = THEME_DICT if theme is None else theme
        df_plot = df.copy()

        # Replace y with friendly names
        hue_label = f"{hue}_label"
        df_plot[hue_label] = replace_with_fallback(
            df_plot[hue], TECH_NAME_REPLACEMENT
        )

        df = df_plot[[x,y,hue_label]].copy()
        df = df.groupby([x, hue_label], as_index=False)[y].sum()
        
        print(df)

        # Build colors based on replaced names
        palette = {
            tech: V_COLORS.get(tech, "#999999")
            for tech in df_plot[hue_label].unique()
        }
        
        

        fig = (
            so.Plot(df, x=x, y=y, color=hue_label)
            .add(so.Area(alpha=alpha), so.Agg(), so.Stack())
            .label(
                title=title,
                x=(xlabel if xlabel else x.capitalize()),
                y=(ylabel if ylabel else y.capitalize()),
                color = f'{hue.capitalize()}'
            )
            .scale(color=palette)
            .theme(theme)
            .layout(engine="tight")
            #.limit(x=(2025, 2050))
        )

        return fig

def main():
    vintages = [2025, 2030, 2050]
    technologies = ['T_LDV_C_DSL_EX', 'T_LDV_C_BEV150_EX']
    caps = []
    vints = []
    techs = [] 
    i = 10
    for v in vintages:
        for t in technologies:
            caps.append(i + 0.8)
            vints.append(v)
            techs.append(t)
            i += 2

    df = pd.DataFrame({"vintage": vints, "tech": techs, "capacity": caps})

    # print(df)

    fig = area_plot(df, x='vintage', y='capacity', hue='tech',)
    fig.show()


if __name__ == '__main__':
     main()
