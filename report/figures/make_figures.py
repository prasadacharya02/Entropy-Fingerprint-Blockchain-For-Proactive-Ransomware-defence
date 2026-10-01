#!/usr/bin/env python3
"""Regenerate every figure used in the ENTROPY project report.

Figures are drawn at their final print size (about 6.6 in wide, the text
column of an A4 page with 0.85 in margins) so that the lettering stays
legible when the document is printed.  Everything is deterministic:

    python report/figures/make_figures.py
"""

from __future__ import annotations

import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

HERE = Path(__file__).resolve().parent
DPI = 300

NAVY = "#16324F"
TEAL = "#2E86AB"
AMBER = "#B8860B"
RED = "#B03A2E"
GREEN = "#2E7D5B"
GREY = "#7F8C8D"
LIGHT = "#EDF2F7"
PURPLE = "#6C5B7B"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 7.5,
        "axes.edgecolor": "#4A5568",
        "axes.labelcolor": NAVY,
        "axes.titlesize": 8.5,
        "axes.titleweight": "bold",
        "axes.titlecolor": NAVY,
        "axes.labelsize": 7.5,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "xtick.color": "#2D3748",
        "ytick.color": "#2D3748",
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
        "savefig.bbox": "tight",
        "savefig.dpi": DPI,
    }
)


def save(fig, name: str) -> None:
    path = HERE / name
    fig.savefig(path)
    plt.close(fig)
    print(f"wrote {path.name}")


def box(ax, x, y, w, h, text, *, fc=LIGHT, ec=NAVY, tc=NAVY, size=7.2,
        weight="normal", lw=1.0):
    ax.add_patch(
        FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.006,rounding_size=0.02",
            linewidth=lw, edgecolor=ec, facecolor=fc, zorder=2,
        )
    )
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=size, color=tc, weight=weight, zorder=3,
            linespacing=1.35, multialignment="center")


def arrow(ax, p1, p2, *, color=NAVY, lw=1.0, ls="-", rad=0.0):
    ax.add_patch(
        FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=8,
                        color=color, linewidth=lw, linestyle=ls, zorder=1,
                        connectionstyle=f"arc3,rad={rad}")
    )


def canvas(w=6.6, h=3.0):
    """A blank drawing canvas on a 0-100 grid; *h* sets the printed height."""
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    return fig, ax


# ── 2.1 entropy envelopes and one document over time ──────────
def fig_entropy_profile() -> None:
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(6.6, 2.5), gridspec_kw={"width_ratios": [1.4, 1]}
    )
    formats = [("text (.txt)", 3.0, 5.5, GREY), ("code / csv", 4.0, 6.0, GREY),
               ("docx / xlsx", 6.0, 7.5, TEAL), ("pdf", 6.5, 7.8, TEAL),
               ("jpeg / png", 7.0, 7.8, TEAL), ("mp4 video", 7.0, 7.9, TEAL),
               ("zip archive", 7.5, 8.0, TEAL)]
    y = np.arange(len(formats))[::-1]
    for yi, (label, lo, hi, colour) in zip(y, formats):
        ax1.barh(yi, hi - lo, left=lo, height=0.5, color=colour, alpha=0.9,
                 edgecolor="white", linewidth=0.7)
        ax1.text(lo - 0.1, yi, f"{lo:.1f}", ha="right", va="center",
                 fontsize=6.2, color="#4A5568")
        ax1.text(hi + 0.1, yi, f"{hi:.1f}", ha="left", va="center",
                 fontsize=6.2, color="#4A5568")
    ax1.axvline(8.0, color=RED, linewidth=1.3, linestyle="--")
    ax1.text(7.9, 0.05, "ciphertext ceiling 8.0", ha="right", va="bottom",
             fontsize=6.4, color=RED, weight="bold")
    ax1.set_yticks(y)
    ax1.set_yticklabels([f[0] for f in formats], fontsize=6.8)
    ax1.set_xlim(2.3, 8.7)
    ax1.set_xticks([3, 4, 5, 6, 7, 8])
    ax1.set_xlabel("Shannon entropy (bits per byte)", fontsize=7)
    ax1.set_title("Per-format entropy envelopes", pad=4)
    ax1.grid(axis="x", alpha=0.2, linestyle=":")

    stages = ["before", "50 %\nencrypted", "fully\nencrypted"]
    values = [4.1, 6.2, 7.94]
    bars = ax2.bar(stages, values, color=[GREEN, AMBER, RED], width=0.55)
    for rect, value in zip(bars, values):
        ax2.text(rect.get_x() + rect.get_width() / 2, value + 0.15,
                 f"{value:.2f}", ha="center", fontsize=7.4, weight="bold",
                 color=NAVY)
    ax2.axhline(6.8, color=NAVY, linestyle="--", linewidth=1.1)
    ax2.text(-0.42, 6.95, "threshold 6.8", fontsize=6.2, color=NAVY)
    ax2.axhline(6.1, color=PURPLE, linestyle=":", linewidth=1.1)
    ax2.text(-0.42, 5.05, "delta limit 4.1 + 2.0", fontsize=6.2, color=PURPLE)
    ax2.set_ylim(0, 9.1)
    ax2.set_yticks([0, 2, 4, 6, 8])
    ax2.set_ylabel("bits/byte", fontsize=7)
    ax2.set_title("One document over time", pad=4)
    ax2.grid(axis="y", alpha=0.2, linestyle=":")

    fig.tight_layout(pad=0.6)
    save(fig, "fig01_entropy_profile.png")


# ── 3.1 deployment topology ───────────────────────────────────
def fig_topology() -> None:
    fig, ax = canvas(h=3.4)
    box(ax, 2, 62, 26, 30,
        "ATTACKER CONSOLE :8001\n\n10 ransomware families\nspeed / seed control",
        fc="#FDF0EE", ec=RED, tc=RED, weight="bold")
    box(ax, 2, 8, 26, 30,
        "VICTIM PC :5001\n\nneutral file explorer\n+ PIN evidence vault",
        fc=LIGHT, ec=TEAL, tc=NAVY, weight="bold")
    box(ax, 36, 34, 28, 44,
        "VICTIM ESTATE\nuser_files/\n\n18 controlled files\nDocuments · Downloads\nDesktop · Pictures",
        fc="white", ec=NAVY, weight="bold", size=7.4)
    box(ax, 72, 62, 26, 30,
        "SOC DASHBOARD :5000\n\nlive feed · entropy graph\nalerts · ledger · reports",
        fc="#EAF4EF", ec=GREEN, tc=GREEN, weight="bold")
    box(ax, 72, 8, 26, 30,
        "ENTROPY SHIELD\n\nmonitor · analyse · decide\ncontain · restore · audit",
        fc="#EAF2F8", ec=TEAL, weight="bold")
    box(ax, 36, 2, 28, 12, "ephemeral attacker process",
        fc="#FDF0EE", ec=RED, tc=RED, size=6.8, weight="bold")

    arrow(ax, (28, 77), (36, 68), color=RED, lw=1.2)
    ax.text(29, 81, "encrypt", fontsize=6.6, color=RED, weight="bold")
    arrow(ax, (64, 74), (72, 72), color=GREEN, lw=1.2)
    ax.text(60, 80, "socket push 0.4 s", fontsize=6.6, color=GREEN,
            weight="bold")
    arrow(ax, (72, 24), (64, 30), color=TEAL, lw=1.2)
    ax.text(66, 16, "detect / contain /\nrestore", fontsize=6.6, color=TEAL,
            weight="bold")
    arrow(ax, (36, 44), (28, 30), color=TEAL, lw=1.1, ls="--")
    ax.text(24, 44, "clean backup", fontsize=6.4, color=TEAL, ha="right")
    arrow(ax, (50, 34), (50, 14), color=RED, lw=1.0, ls=":")
    save(fig, "fig02_topology.png")


# ── 3.2 runtime pipeline ──────────────────────────────────────
def fig_pipeline() -> None:
    fig, ax = canvas(h=3.5)
    stages = [
        (84, "1 · MONITOR", TEAL, "watchdog poll 0.2 s · create / modify / delete / rename · 1 s dedup"),
        (70, "2 · ANALYSE", NAVY, "Shannon + section entropy · delta vs own history · 0–100 score"),
        (56, "3 · CORROBORATE", PURPLE, "ransom note · store tamper · federated fingerprint lookup"),
        (42, "4 · DECIDE", AMBER, "hard-signal short-circuit · rules | RF | DQN · campaign 2 files / 15 s"),
        (28, "5 · RESPOND", RED, "verified-PID kill · quarantine + SHA3-256 · campaign sweep"),
        (14, "6 · RECOVER & AUDIT", GREEN, "strict-clean restore + rename-back · report · ledger · exchange"),
    ]
    for y, title, colour, body in stages:
        box(ax, 2, y, 62, 11, "", fc="white", ec=colour, lw=1.1)
        ax.text(4, y + 7.4, title, fontsize=7.2, color=colour, weight="bold",
                va="center")
        ax.text(4, y + 3.3, body, fontsize=6.4, color="#2D3748", va="center")
        if y > 14:
            arrow(ax, (33, y - 0.6), (33, y - 2.9), color=GREY, lw=1.1)

    right = [
        (84, "victim_server/user_files\n18-file controlled estate", LIGHT, NAVY, NAVY),
        (70, "backup_storage/\nversioned clean copies", "#EAF4EF", GREEN, GREEN),
        (56, "quarantine_storage/\nevidence + metadata", "#FDF0EE", RED, RED),
        (42, "reports/ + entropy.db\nevents and outcomes", LIGHT, NAVY, NAVY),
        (28, "Ganache ThreatLogger\nor labelled local ledger", "#F3EEF7", PURPLE, PURPLE),
        (14, "fingerprint exchange\ncross-node threat memory", "#F3EEF7", PURPLE, PURPLE),
    ]
    for y, body, fc, ec, tc in right:
        box(ax, 70, y, 28, 11, body, fc=fc, ec=ec, tc=tc, size=6.6,
            weight="bold")
    arrow(ax, (64.5, 89.5), (70, 89.5), color=NAVY, lw=1.1)
    for y in (70, 56, 42, 28, 14):
        arrow(ax, (64.5, y + 5.5), (70, y + 5.5), color=GREY, lw=0.8, ls=":")
    save(fig, "fig03_pipeline.png")


# ── 4.1 decision flow ─────────────────────────────────────────
def fig_decision_flow() -> None:
    fig, ax = canvas(h=3.6)
    box(ax, 34, 89, 32, 9, "file event analysed", fc=NAVY, ec=NAVY, tc="white",
        size=7.4, weight="bold")
    box(ax, 27, 74, 46, 10, "hard-confirmation signal?\nransom note · store tamper · known fingerprint",
        fc="#FDF0EE", ec=RED, tc=RED, size=6.6)
    box(ax, 30, 60, 40, 10, "per-event score 0–100\nrules · RF · DQN", fc="#EAF2F8",
        ec=TEAL, size=7.0)
    box(ax, 30, 46, 40, 10, "campaign tracker\n≥2 files qualifying in 15 s", fc="#FEF6E7",
        ec=AMBER, tc="#7A5200", size=7.0)

    box(ax, 2, 30, 22, 9, "score < 40\nIGNORE", fc="white", ec=GREY, tc="#4A5568",
        size=7.0)
    box(ax, 28, 30, 24, 9, "40 ≤ score < 70\nALERT + log", fc="#EAF2F8", ec=TEAL,
        size=7.0)
    box(ax, 56, 30, 42, 9, "score ≥ 70 or campaign confirmed\nTERMINATE + QUARANTINE + RESTORE",
        fc="#FDF0EE", ec=RED, tc=RED, size=6.8, weight="bold")

    box(ax, 5, 12, 44, 11, "respond()\nkill PID → quarantine → restore clean copy",
        fc="#F7FAFC", ec=RED, size=6.4)
    box(ax, 53, 12, 44, 11, "aftermath\nsweep → post-kill verification → report",
        fc="#F7FAFC", ec=GREEN, size=6.4)

    arrow(ax, (50, 89), (50, 84.6), lw=1.2)
    ax.text(51, 86.4, "yes", fontsize=6.6, color=RED, weight="bold")
    arrow(ax, (73, 79), (94, 79), color=RED, lw=1.1)
    arrow(ax, (94, 79), (94, 34.5), color=RED, lw=1.1)
    arrow(ax, (94, 34.5), (98.4, 34.5), color=RED, lw=1.1)
    arrow(ax, (50, 74), (50, 70.4), lw=1.2)
    ax.text(51, 71.8, "no", fontsize=6.6)
    arrow(ax, (50, 60), (50, 56.4), lw=1.2)
    arrow(ax, (50, 46), (50, 39.4), lw=1.1)
    arrow(ax, (30, 51), (18, 39.4), color=AMBER, lw=1.0, ls=":")
    arrow(ax, (40, 51), (38, 39.4), color=GREY, lw=0.9, ls="--")
    arrow(ax, (70, 51), (76, 39.4), color=AMBER, lw=1.0, ls=":")
    arrow(ax, (76, 30), (80, 23.4), color=RED, lw=1.1)
    arrow(ax, (24, 30), (20, 23.4), color=RED, lw=1.0)
    arrow(ax, (92, 30), (92, 23.4), color=GREEN, lw=1.0, ls=":")
    save(fig, "fig04_decision_flow.png")


# ── 4.2 containment trace and estate damage ───────────────────
def fig_campaign_timeline() -> None:
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(6.6, 2.6), gridspec_kw={"width_ratios": [1.5, 1]}
    )
    events = [
        ("0.0 s", "file 1 touched", GREY),
        ("0.9 s", "file 1 (xlsx) H → 7.88 · ALERT", AMBER),
        ("1.8 s", "file 2 renamed .WNCRY · H 7.81", AMBER),
        ("2.4 s", "campaign confirmed (2 files / 15 s)", RED),
        ("2.7 s", "attacker PID terminated (rc 42)", RED),
        ("3.4 s", "sweep: quarantine + restore", GREEN),
        ("4.1 s", "post-kill repair of mid-write file", GREEN),
    ]
    ax1.set_xlim(0, 10)
    ax1.set_ylim(0, 10)
    ax1.axis("off")
    ax1.plot([1.4, 1.4], [0.6, 9.2], color="#CBD5E0", lw=1.4, zorder=1)
    for index, (stamp, label, colour) in enumerate(events):
        y = 9.2 - index * 1.32
        ax1.plot([1.4], [y], marker="o", markersize=5.5, color=colour,
                 zorder=3)
        ax1.text(0.3, y, stamp, ha="right", va="center", fontsize=6.8,
                 color=colour, weight="bold")
        ax1.text(1.9, y, label, ha="left", va="center", fontsize=6.5,
                 color="#2D3748")
    ax1.set_title("Live WannaCry containment trace", pad=3)

    files = ["file 1\n(xlsx)", "file 2\n(.WNCRY)", "file 3\n(mid-write)",
             "files 4–18\n(unreached)"]
    before = [4.6, 4.9, 5.1, 4.8]
    after = [7.88, 7.81, 7.79, 4.8]
    x = np.arange(len(files))
    ax2.bar(x - 0.19, before, width=0.36, color=GREEN, label="before")
    ax2.bar(x + 0.19, after, width=0.36, color=RED, label="after")
    ax2.axhline(6.8, color=NAVY, linestyle="--", linewidth=1.0)
    ax2.text(-0.42, 7.0, "6.8", fontsize=6.2, color=NAVY)
    ax2.set_xticks(x)
    ax2.set_xticklabels(files, fontsize=6.2)
    ax2.set_ylim(0, 9.4)
    ax2.set_yticks([0, 2, 4, 6, 8])
    ax2.set_ylabel("bits/byte", fontsize=6.8)
    ax2.legend(fontsize=6.2, frameon=False, loc="upper right")
    ax2.set_title("Estate damage at kill time", pad=3)
    ax2.grid(axis="y", alpha=0.2, linestyle=":")
    fig.tight_layout(pad=0.5)
    save(fig, "fig05_campaign_timeline.png")


# ── 4.3 backup versioning and the strict clean rule ───────────
def fig_restore_states() -> None:
    fig, ax = canvas(h=2.0)
    box(ax, 2, 46, 20, 34, "v1 baseline\nH = 4.6\nclean ✔", fc="#EAF4EF",
        ec=GREEN, tc=GREEN, weight="bold")
    box(ax, 27, 46, 20, 34, "v2 event-time\nH = 4.7\nclean ✔", fc="#EAF4EF",
        ec=GREEN, tc=GREEN, weight="bold")
    box(ax, 52, 46, 22, 34, "ciphertext\nH = 7.88\nrejected ✘", fc="#FDF0EE",
        ec=RED, tc=RED, weight="bold")
    box(ax, 79, 46, 19, 34, "restore\nuses v2", fc="#EAF2F8", ec=TEAL,
        weight="bold")
    arrow(ax, (22, 63), (27, 63), color=GREEN, lw=1.1)
    ax.text(24.5, 68, "capture", fontsize=6.2, color=GREEN, ha="center",
            weight="bold")
    arrow(ax, (47, 63), (52, 63), color=RED, lw=1.1)
    ax.text(49.5, 68, "modified", fontsize=6.2, color=RED, ha="center",
            weight="bold")
    arrow(ax, (74, 63), (79, 63), color=TEAL, lw=1.1)
    ax.text(76.5, 68, "select", fontsize=6.2, color=TEAL, ha="center",
            weight="bold")
    arrow(ax, (88, 46), (88, 30), color=TEAL, lw=1.1)
    box(ax, 60, 8, 38, 22,
        "restore: verify SHA-256 of the blob,\noverwrite ciphertext, rename back",
        fc="white", ec=TEAL, size=6.6)
    ax.text(2, 33,
            "A version is clean only if its entropy is inside the format envelope with no "
            "margin and is not ≥ 2.0 bits\nabove the previous clean version — so encrypted "
            "content can never become the source of a restore.",
            fontsize=6.4, color="#4A5568", va="top", linespacing=1.45)
    save(fig, "fig06_restore_states.png")


# ── 4.4 audit and federated sharing ───────────────────────────
def fig_blockchain_flow() -> None:
    fig, ax = canvas(h=3.0)
    box(ax, 2, 78, 22, 18, "confirmed incident\n(files quarantined)",
        fc="#FDF0EE", ec=RED, tc=RED, size=6.8, weight="bold")
    box(ax, 28, 78, 22, 18, "dual hash\nSHA3-256 + SHA-256", fc=LIGHT, ec=NAVY,
        size=6.8, weight="bold")
    box(ax, 54, 78, 20, 18, "forensic report\nreports/*.json", fc=LIGHT, ec=NAVY,
        size=6.8, weight="bold")
    box(ax, 78, 78, 20, 18, "event store\nentropy.db", fc=LIGHT, ec=NAVY,
        size=6.8, weight="bold")

    box(ax, 16, 40, 32, 20,
        "ThreatLogger contract (Ganache)\nlogThreat() onlyOwner\nThreatLogged(id, fp, type, ts)",
        fc="#F3EEF7", ec=PURPLE, tc=PURPLE, size=6.4, weight="bold")
    box(ax, 52, 40, 32, 20,
        "local SQLite ledger (fallback)\nnot a blockchain — labelled\nmode = ganache | fallback | none",
        fc="#F7FAFC", ec=GREY, tc="#4A5568", size=6.4, weight="bold")

    box(ax, 16, 8, 32, 20, "fingerprint exchange\nsightings + independent sources",
        fc="#EAF2F8", ec=TEAL, tc=TEAL, size=6.6, weight="bold")
    box(ax, 52, 8, 32, 20,
        "other nodes\n1 sighting → +25 corroboration\n2 sources → auto-confirm",
        fc="#EAF4EF", ec=GREEN, tc=GREEN, size=6.4, weight="bold")

    arrow(ax, (24, 78), (28, 78), color=NAVY, lw=1.0)
    arrow(ax, (50, 78), (54, 78), color=NAVY, lw=1.0)
    arrow(ax, (74, 78), (78, 78), color=NAVY, lw=1.0)
    arrow(ax, (14, 77), (26, 61), color=PURPLE, lw=1.1)
    arrow(ax, (34, 77), (60, 61), color=GREY, lw=1.0, ls="--")
    arrow(ax, (60, 77), (52, 61), color=GREY, lw=1.0, ls="--")
    arrow(ax, (30, 39), (30, 29), color=TEAL, lw=1.1)
    arrow(ax, (48, 18), (52, 18), color=GREEN, lw=1.1)
    ax.text(50, 24, "publish", fontsize=6.2, color=GREEN, ha="center",
            weight="bold")
    save(fig, "fig07_audit_flow.png")


# ── 7.1 detection results ─────────────────────────────────────
def fig_detection_results() -> None:
    scenarios = ["burst", "slow", "poly", "baseline", "unknown", "note", "tamper",
                 "blindspot"]
    rules = [100, 100, 100, 100, 100, 100, 100, 0]
    rf = [100, 100, 100, 100, 100, 100, 100, 100]

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(6.6, 2.6), gridspec_kw={"width_ratios": [1.55, 1]}
    )
    x = np.arange(len(scenarios))
    ax1.bar(x - 0.2, rules, width=0.4, color=TEAL, label="rules (default)")
    ax1.bar(x + 0.2, rf, width=0.4, color=PURPLE, label="random forest (opt-in)")
    ax1.set_xticks(x)
    ax1.set_xticklabels(scenarios, rotation=35, ha="right", fontsize=6.2)
    ax1.set_ylim(0, 122)
    ax1.set_yticks([0, 25, 50, 75, 100])
    ax1.set_ylabel("runs detected (%)", fontsize=6.8)
    ax1.legend(fontsize=6.2, frameon=False, loc="lower left")
    ax1.set_title("Detection per scenario (6 runs each)", pad=4)
    ax1.grid(axis="y", alpha=0.2, linestyle=":")
    ax1.axhline(87.5, color=RED, linestyle="--", linewidth=0.9)
    ax1.text(7.45, 90, "rules 87.5 %", fontsize=6.2, color=RED, ha="right")

    metrics = ["attack\ndetection", "false\npositives", "false\nquarantines"]
    rules_pct = [87.5, 14.3, 0.0]
    rf_pct = [100.0, 42.9, 28.6]
    x2 = np.arange(len(metrics))
    ax2.bar(x2 - 0.2, rules_pct, width=0.4, color=TEAL, label="rules")
    ax2.bar(x2 + 0.2, rf_pct, width=0.4, color=PURPLE, label="RF")
    for xi, (r, f) in enumerate(zip(rules_pct, rf_pct)):
        ax2.text(xi - 0.2, r + 2.5, f"{r:.0f}", ha="center", fontsize=6.2,
                 color=TEAL, weight="bold")
        ax2.text(xi + 0.2, f + 2.5, f"{f:.0f}", ha="center", fontsize=6.2,
                 color=PURPLE, weight="bold")
    ax2.set_xticks(x2)
    ax2.set_xticklabels(metrics, fontsize=6.4)
    ax2.set_ylim(0, 122)
    ax2.set_yticks([0, 25, 50, 75, 100])
    ax2.set_ylabel("percent", fontsize=6.8)
    ax2.set_title("Headline trade-off", pad=4)
    ax2.grid(axis="y", alpha=0.2, linestyle=":")
    fig.tight_layout(pad=0.5)
    save(fig, "fig08_detection_results.png")


# ── 7.2 legitimate workloads ──────────────────────────────────
def fig_workloads() -> None:
    workloads = ["document\nediting", "archive\ncreation", "photo\nimport",
                 "video\nwrite", "git\nburst", "csv\nexport", "db\ndump"]
    fig, ax = plt.subplots(figsize=(6.6, 2.3))
    x = np.arange(len(workloads))
    w = 0.2
    ax.bar(x - 1.5 * w, [0, 0, 0, 0, 3, 0, 0], width=w, color=AMBER,
           label="rules — alerts")
    ax.bar(x - 0.5 * w, [0] * 7, width=w, color=RED,
           label="rules — false quarantines")
    ax.bar(x + 0.5 * w, [0, 0, 3, 3, 0, 0, 3], width=w, color=TEAL,
           label="RF — alerts")
    ax.bar(x + 1.5 * w, [0, 0, 3, 3, 0, 0, 0], width=w, color=PURPLE,
           label="RF — false quarantines")
    ax.set_xticks(x)
    ax.set_xticklabels(workloads, fontsize=6.4)
    ax.set_ylim(0, 4.0)
    ax.set_yticks([0, 1, 2, 3])
    ax.set_ylabel("runs out of 3", fontsize=6.8)
    ax.legend(fontsize=6.2, frameon=False, ncol=2, loc="upper center")
    ax.set_title("Legitimate workloads with no startup baseline", pad=5,
                 fontsize=8)
    ax.grid(axis="y", alpha=0.2, linestyle=":")
    fig.tight_layout(pad=0.4)
    save(fig, "fig09_workloads.png")


# ── 7.3 recovery drill ────────────────────────────────────────
def fig_recovery() -> None:
    scenarios = ["burst", "slow", "poly", "baseline", "unknown", "blindspot",
                 "note", "tamper"]
    with_base = {"recovered": [8, 8, 8, 4, 5, 0, 0, 0],
                 "contained": [0, 0, 0, 0, 0, 0, 0, 2],
                 "lost": [0, 0, 0, 0, 0, 4, 1, 1]}
    no_base = {"recovered": [0, 0, 0, 4, 0, 0, 0, 0],
               "contained": [0, 0, 0, 0, 0, 0, 0, 2],
               "lost": [8, 8, 8, 0, 5, 4, 1, 1]}
    colours = {"recovered": GREEN, "contained": AMBER, "lost": RED}
    labels = {"recovered": "recovered byte-for-byte",
              "contained": "contained, not restored", "lost": "lost"}

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.6, 2.6), sharey=True)
    x = np.arange(len(scenarios))
    for ax, data, title in (
        (ax1, with_base, "with startup baseline"),
        (ax2, no_base, "no baseline (worst case)"),
    ):
        bottom = np.zeros(len(scenarios))
        for key in ("recovered", "contained", "lost"):
            values = np.array(data[key], dtype=float)
            ax.bar(x, values, bottom=bottom, width=0.62, color=colours[key],
                   label=labels[key], edgecolor="white", linewidth=0.5)
            bottom += values
        ax.set_xticks(x)
        ax.set_xticklabels(scenarios, rotation=38, ha="right", fontsize=6.2)
        ax.set_title(title, fontsize=7.2, pad=4)
        ax.grid(axis="y", alpha=0.2, linestyle=":")
        ax.set_ylim(0, 8.9)
    ax1.set_ylabel("files in the estate", fontsize=6.8)
    handles, names = ax1.get_legend_handles_labels()
    fig.legend(handles, names, fontsize=6.2, frameon=False, ncol=3,
               loc="lower center", bbox_to_anchor=(0.5, -0.10))
    fig.suptitle("Recovery drill: 111 of 246 attacked files recovered (45.1 %)",
                 fontsize=8, color=NAVY, weight="bold", y=1.02)
    fig.tight_layout(pad=0.5)
    save(fig, "fig10_recovery.png")


# ── 7.4 latency ───────────────────────────────────────────────
def fig_latency() -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.6, 2.3))
    x = np.arange(2)
    ax1.bar(x - 0.2, [42, 6], width=0.4, color=TEAL, label="rules")
    ax1.bar(x + 0.2, [48, 0], width=0.4, color=PURPLE, label="RF")
    for xi, value in ((0, 42), (1, 6)):
        ax1.text(xi - 0.2, value + 1, str(value), ha="center", fontsize=6.4,
                 color=TEAL, weight="bold")
    ax1.text(0.2, 49, "48", ha="center", fontsize=6.4, color=PURPLE,
             weight="bold")
    ax1.set_xticks(x)
    ax1.set_xticklabels(["1 op", "2 ops"], fontsize=6.8)
    ax1.set_ylim(0, 58)
    ax1.set_ylabel("attacked runs detected", fontsize=6.8)
    ax1.set_xlabel("file operations to detection", fontsize=6.8)
    ax1.set_title("Detection latency (48 runs)", pad=4, fontsize=7.6)
    ax1.legend(fontsize=6.2, frameon=False)
    ax1.grid(axis="y", alpha=0.2, linestyle=":")

    names = ["watchdog poll", "dashboard push", "live kill",
             "restore one file"]
    values = [200, 400, 2700, 22]
    y = np.arange(len(names))[::-1]
    ax2.barh(y, values, color=[TEAL, GREEN, RED, GREEN], height=0.5, log=True)
    for yi, value in zip(y, values):
        ax2.text(value * 1.2, yi, f"{value} ms", va="center", fontsize=6.4,
                 color="#2D3748")
    ax2.set_yticks(y)
    ax2.set_yticklabels(names, fontsize=6.6)
    ax2.set_xlim(10, 20000)
    ax2.set_xlabel("milliseconds (log scale)", fontsize=6.8)
    ax2.set_title("Measured timing envelope", pad=4, fontsize=7.6)
    ax2.grid(axis="x", alpha=0.2, linestyle=":")
    fig.tight_layout(pad=0.5)
    save(fig, "fig11_latency.png")


# ── 3.2 five layers of defence ────────────────────────────────
def fig_defence_layers() -> None:
    fig, ax = canvas(h=2.4)
    layers = [
        ("DETECT", "entropy · format range · delta · rate · extension change", TEAL),
        ("CORROBORATE", "campaign tracker · ransom note · tamper · exchange", PURPLE),
        ("CONTAIN", "verified-PID kill · quarantine with SHA3-256 evidence", RED),
        ("RECOVER", "versioned clean backups · strict rule · rename-back", GREEN),
        ("AUDIT", "dual-hash report · ledger anchor · federated sharing", AMBER),
    ]
    y = 84
    for name, body, colour in layers:
        box(ax, 2, y - 1, 22, 15, name, fc=colour, ec=colour, tc="white",
            size=7.4, weight="bold")
        box(ax, 27, y - 1, 71, 15, body, fc="white", ec=colour, size=6.8)
        y -= 18
    save(fig, "fig12_defence_layers.png")


def main() -> None:
    for fn in (fig_entropy_profile, fig_defence_layers, fig_topology,
               fig_pipeline, fig_decision_flow, fig_campaign_timeline,
               fig_restore_states, fig_blockchain_flow, fig_detection_results,
               fig_workloads, fig_recovery, fig_latency):
        fn()
    print(f"\nAll figures written to {HERE} at {DPI} dpi.")


if __name__ == "__main__":
    os.makedirs(HERE, exist_ok=True)
    main()
