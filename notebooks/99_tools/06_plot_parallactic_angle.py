#!/usr/bin/env python3
"""Plot parallactic angle as a function of hour angle for several latitudes.

The parallactic angle depends on latitude, declination, and hour angle:

    tan(q) = sin(H) / (tan(phi) * cos(delta) - sin(delta) * cos(H))

where:
    - q is the parallactic angle
    - H is the hour angle
    - phi is the observer latitude
    - delta is the target declination

By default this script uses delta = 0 deg, but both the declination and the
set of latitudes can be configured from the command line.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def parallactic_angle(hour_angle_rad: np.ndarray, latitude_rad: float, declination_rad: float) -> np.ndarray:
    """Return the parallactic angle in radians."""
    numerator = np.sin(hour_angle_rad)
    denominator = np.tan(latitude_rad) * np.cos(declination_rad) - np.sin(declination_rad) * np.cos(
        hour_angle_rad
    )
    return np.arctan2(numerator, denominator)


def parse_latitudes(value: str) -> list[float]:
    """parse latitude string to float

    Args:
        value (str): latitude string code

    Returns:
        list[float]: array of float corresponding to the latitudes
    """
    return [float(item) for item in value.split(",") if item.strip()]


def build_parser() -> argparse.ArgumentParser:
    """_summary_

    Returns:
        argparse.ArgumentParser: _description_
    """
    parser = argparse.ArgumentParser(
        description="Plot parallactic angle versus hour angle for several latitudes."
    )
    parser.add_argument(
        "--dec",
        type=float,
        default=0.0,
        help="Target declination in degrees (default: 0).",
    )
    parser.add_argument(
        "--latitudes",
        type=parse_latitudes,
        default=[-60, -45, -30, -15, 0, 15, 30, 45, 60],
        help="Comma-separated list of latitudes in degrees.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output image path. If omitted, the figure is shown interactively.",
    )
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="Do not open an interactive window after saving the figure.",
    )
    return parser


def main() -> int:
    """Main function to run the parallactic angle plotting script.

    Returns:
        int: Exit code.
    """
    args = build_parser().parse_args()

    declination_rad = np.deg2rad(args.dec)
    hour_angle_hours = np.linspace(-6.0, 6.0, 1200)
    hour_angle_rad = np.deg2rad(hour_angle_hours * 15.0)

    fig, ax = plt.subplots(figsize=(9, 5.5))

    for latitude_deg in args.latitudes:
        latitude_rad = np.deg2rad(latitude_deg)
        angle_rad = parallactic_angle(hour_angle_rad, latitude_rad, declination_rad)
        angle_deg = np.rad2deg(np.unwrap(angle_rad))
        ax.plot(hour_angle_hours, angle_deg, label=f"{latitude_deg:g}°")

    ax.set_xlabel("Angle horaire [h]")
    ax.set_ylabel("Angle parallactique [deg]")
    ax.set_title(f"Angle parallactique vs angle horaire (dec = {args.dec:g}°)")
    ax.set_xlim(-6, 6)
    ax.grid(True, alpha=0.3)
    ax.legend(title="Latitude", ncols=2, fontsize=9)
    fig.tight_layout()

    if args.output is not None:
        fig.savefig(args.output, dpi=200, bbox_inches="tight")
        print(f"Saved figure to {args.output}")

    if not args.no_show and args.output is None:
        plt.show()

    plt.close(fig)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
