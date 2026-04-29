#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

from abc import ABC, abstractmethod


class FigureRenderer(ABC):

    @abstractmethod
    def add_hline(
        self, y: float, color: str, style: str = "--", linewidth: float = 1.0
    ) -> None: ...

    @abstractmethod
    def add_vline(
        self, x: float, color: str, style: str = "--", linewidth: float = 1.0
    ) -> None: ...

    @abstractmethod
    def add_hrect(self, y0: float, y1: float, color: str) -> None: ...

    @abstractmethod
    def add_vrect(self, x0: float, x1: float, color: str) -> None: ...

    @abstractmethod
    def add_curve(
        self, x: list[float], y: list[float], color: str, style: str = "-", name: str = ""
    ) -> None: ...

    @abstractmethod
    def add_scatter(self, x: float, y: float, color: str, name: str = "") -> None: ...

    @abstractmethod
    def add_annotation(
        self,
        text: str,
        x: float,
        y: float,
        color: str,
        offset_y: float = 0.0,
        paper_coords: bool = False,
    ) -> None: ...


class MatplotlibRenderer(FigureRenderer):

    _STYLE_MAP = {
        "--": "--",
        "-": "-",
        ":": ":",
        "dash": "--",
        "dot": ":",
        "solid": "-",
        "dashdot": "-.",
    }

    def add_hline(self, y: float, color: str, style: str = "--", linewidth: float = 1.0) -> None:
        import matplotlib.pyplot as plt

        plt.axhline(
            y=y, color=color, linestyle=self._STYLE_MAP.get(style, style), linewidth=linewidth
        )

    def add_vline(self, x: float, color: str, style: str = "--", linewidth: float = 1.0) -> None:
        import matplotlib.pyplot as plt

        plt.axvline(
            x=x, color=color, linestyle=self._STYLE_MAP.get(style, style), linewidth=linewidth
        )

    def add_hrect(self, y0: float, y1: float, color: str) -> None:
        import matplotlib.pyplot as plt

        plt.axhspan(ymin=y0, ymax=y1, color=color, linestyle="-", linewidth=0.2)

    def add_vrect(self, x0: float, x1: float, color: str) -> None:
        import matplotlib.pyplot as plt

        plt.axvspan(xmin=x0, xmax=x1, color=color, linestyle="-", linewidth=0.2)

    def add_curve(
        self, x: list[float], y: list[float], color: str, style: str = "-", name: str = ""
    ) -> None:
        import matplotlib.pyplot as plt

        plt.plot(x, y, color=color, linestyle=self._STYLE_MAP.get(style, style))

    def add_scatter(self, x: float, y: float, color: str, name: str = "") -> None:
        import matplotlib.pyplot as plt

        plt.scatter(x, y, color=color)

    def add_annotation(
        self,
        text: str,
        x: float,
        y: float,
        color: str,
        offset_y: float = 0.0,
        paper_coords: bool = False,
    ) -> None:
        import matplotlib.pyplot as plt

        if paper_coords:
            plt.annotate(
                text,
                xy=(1, 0),
                xytext=(-60, 5),
                xycoords="axes fraction",
                textcoords="offset points",
                color=color,
                fontsize="small",
            )
        else:
            plt.annotate(
                text,
                xy=(x, y),
                xytext=(2.5, offset_y),
                textcoords="offset points",
                color=color,
                fontsize="small",
            )


class PlotlyRenderer(FigureRenderer):

    _STYLE_MAP = {
        "--": "dash",
        "-": "solid",
        ":": "dot",
        "dash": "dash",
        "dot": "dot",
        "solid": "solid",
        "dashdot": "dashdot",
    }

    def __init__(self, fig) -> None:
        self._fig = fig

    def add_hline(self, y: float, color: str, style: str = "--", linewidth: float = 1.0) -> None:
        self._fig.add_hline(
            y=y,
            line_color=color,
            line_dash=self._STYLE_MAP.get(style, style),
            line_width=linewidth,
        )

    def add_vline(self, x: float, color: str, style: str = "--", linewidth: float = 1.0) -> None:
        self._fig.add_vline(
            x=x,
            line_color=color,
            line_dash=self._STYLE_MAP.get(style, style),
            line_width=linewidth,
            opacity=0.8,
        )

    def add_hrect(self, y0: float, y1: float, color: str) -> None:
        self._fig.add_hrect(y0=y0, y1=y1, line_width=0, fillcolor=color, opacity=0.5)

    def add_vrect(self, x0: float, x1: float, color: str) -> None:
        self._fig.add_vrect(x0=x0, x1=x1, line_width=0, fillcolor=color, opacity=0.5)

    def add_curve(
        self, x: list[float], y: list[float], color: str, style: str = "-", name: str = ""
    ) -> None:
        import plotly.graph_objects as go

        self._fig.add_traces(
            go.Scatter(
                x=x,
                y=y,
                mode="lines",
                name=name,
                line_color=color,
                line_dash=self._STYLE_MAP.get(style, style),
            )
        )

    def add_scatter(self, x: float, y: float, color: str, name: str = "") -> None:
        import plotly.graph_objects as go

        self._fig.add_traces(go.Scatter(x=[x], y=[y], line_color=color, name=name))

    def add_annotation(
        self,
        text: str,
        x: float,
        y: float,
        color: str,
        offset_y: float = 0.0,
        paper_coords: bool = False,
    ) -> None:
        if paper_coords:
            self._fig.add_annotation(
                text=text,
                xref="paper",
                yref="paper",
                x=1,
                y=0,
                showarrow=False,
                font=dict(family="sans serif", size=14, color=color),
                align="left",
            )
        else:
            self._fig.add_annotation(
                text=text,
                x=x,
                y=y,
                xshift=25,
                yshift=offset_y,
                showarrow=False,
                font=dict(family="sans serif", size=14, color=color),
            )
