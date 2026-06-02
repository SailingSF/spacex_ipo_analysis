#!/usr/bin/env python3
"""One-shot layout fixes for notebook plot cells (legends, margins, annotations)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PATCHES: list[tuple[str, str, list[tuple[str, str]]]] = [
    # --- AI ---
    ("notebooks/ai.ipynb", "sec1_code", [
        ('axL.legend(handles=[b_sol, b_adv, EST_PATCH], loc="upper left", fontsize=8.5)',
         'charts.legend_outside(axL, handles=[b_sol, b_adv, EST_PATCH], fontsize=8.5)'),
        ('axR.annotate(f"{p*100:.0f}%", (i, p*100), textcoords="offset points", xytext=(0, 8),',
         'charts.annotate_clear(axR, f"{p*100:.0f}%", (i, p*100), textcoords="offset points", xytext=(0, 12),'),
        ('charts.save(fig, "ai_revenue_mix"); plt.show()',
         'charts.pad_ylim(axL); charts.pad_ylim(axR); fig.subplots_adjust(right=0.82); charts.finish(fig); charts.save(fig, "ai_revenue_mix", layout=False); plt.show()'),
    ]),
    ("notebooks/ai.ipynb", "sec2_code", [
        ('axL.legend(loc="upper left", fontsize=8.2)',
         'charts.legend_outside(axL, fontsize=8.2)'),
        ('charts.save(fig, "ai_cost_stack"); plt.show()',
         'charts.pad_ylim(axL); charts.pad_ylim(axR); fig.subplots_adjust(right=0.82); charts.finish(fig); charts.save(fig, "ai_cost_stack", layout=False); plt.show()'),
    ]),
    ("notebooks/ai.ipynb", "sec3_code", [
        ('ax.text(0.98, 0.95, f"FY2025 total operating cost: ${total_cost:,.0f}M\\n"\n'
         '        f"D&A alone = {R.da[p]/total_cost:.0%} of it",\n'
         '        transform=ax.transAxes, ha="right", va="top", fontsize=9.5,\n'
         '        bbox=dict(boxstyle="round", fc="white", ec="#ccc"))',
         'ax.text(0.02, 0.96, f"FY2025 total operating cost: ${total_cost:,.0f}M\\n"\n'
         '        f"D&A alone = {R.da[p]/total_cost:.0%} of it",\n'
         '        transform=ax.transAxes, ha="left", va="top", fontsize=9.5,\n'
         '        bbox=dict(boxstyle="round", fc="white", ec="#ccc"))'),
        ('charts.save(fig, "ai_cost_nature"); plt.show()',
         'charts.pad_ylim(ax); charts.finish(fig); charts.save(fig, "ai_cost_nature", layout=False); plt.show()'),
    ]),
    ("notebooks/ai.ipynb", "sec4_code", [
        ('axL.legend(h1 + h2 + [EST_PATCH], l1 + l2 + ["FY2026E (run-rate est.)"], loc="upper left", fontsize=8.2)',
         'charts.legend_outside(axL, handles=h1 + h2 + [EST_PATCH], labels=l1 + l2 + ["FY2026E (run-rate est.)"], fontsize=8.2)'),
        ('axR.legend(loc="upper right", fontsize=9)',
         'charts.legend_outside(axR, loc="lower left", fontsize=9)'),
        ('charts.save(fig, "ai_capex_buildout"); plt.show()',
         'charts.pad_ylim(axL); charts.pad_ylim(axR); fig.subplots_adjust(right=0.76); charts.finish(fig); charts.save(fig, "ai_capex_buildout", layout=False); plt.show()'),
    ]),
    ("notebooks/ai.ipynb", "gpu_count", [
        ('ax.axhline(blended/1e3, color="#444", ls="--", lw=1.3)\n'
         'ax.text(1.45, blended/1e3, f"  blended ≈ {blended/1e3:,.0f}k GPUs", va="center", fontsize=9.5, color="#444")',
         'ax.axhline(blended/1e3, color="#444", ls="--", lw=1.3,\n'
         '           label=f"blended ≈ {blended/1e3:,.0f}k GPUs")'),
        ('charts.save(fig, "ai_gpu_count"); plt.show()',
         'charts.pad_ylim(ax); charts.legend_outside(ax, fontsize=9); charts.finish(fig); charts.save(fig, "ai_gpu_count", layout=False); plt.show()'),
    ]),
    ("notebooks/ai.ipynb", "gpu_dep", [
        ('axR.axhline(R.revenue["FY2025"], color="black", lw=1.6, ls="--")\n'
         'axR.text(-0.42, R.revenue["FY2025"] + 120, f"FY2025 segment revenue \\\\${R.revenue[\'FY2025\']:,.0f}M",\n'
         '         va="bottom", ha="left", fontsize=9, fontweight="bold")',
         'axR.axhline(R.revenue["FY2025"], color="black", lw=1.6, ls="--",\n'
         '           label=f"FY2025 segment revenue ${R.revenue[\'FY2025\']:,.0f}M")'),
        ('axR.text(0.97, 0.96,',
         'charts.legend_outside(axR, fontsize=8.5)\n'
         'axR.text(0.97, 0.72,'),
        ('charts.save(fig, "ai_gpu_depreciation"); plt.show()',
         'charts.pad_ylim(axR); fig.subplots_adjust(right=0.78); charts.finish(fig); charts.save(fig, "ai_gpu_depreciation", layout=False); plt.show()'),
    ]),
    ("notebooks/ai.ipynb", "gpu_tread", [
        ('ax.axhline(GPU_RENTAL_USD_HR, color="#333", ls="--", lw=1.5)\n'
         'ax.text(41, GPU_RENTAL_USD_HR + 0.06, f"~${GPU_RENTAL_USD_HR}/GPU-hr blended market rent (2025-26, and falling)",\n'
         '        fontsize=9, fontweight="bold", color="#333")\n'
         'ax.text(41, GPU_RENTAL_USD_HR_BAND[1] - 0.25, "market rental band\\n$1.5–$4.0/hr", fontsize=8.5, color=GREY)',
         'ax.axhline(GPU_RENTAL_USD_HR, color="#333", ls="--", lw=1.5,\n'
         '           label=f"~${GPU_RENTAL_USD_HR}/GPU-hr blended market rent (2025-26)")\n'
         'ax.axhspan(*GPU_RENTAL_USD_HR_BAND, color=GREY, alpha=0.12, label="market rental band $1.5–$4.0/hr")'),
        ('ax.axhspan(*GPU_RENTAL_USD_HR_BAND, color=GREY, alpha=0.12)\n',
         ''),
        ('ax.annotate(f"base case: ${be0:.2f}/hr to break even\\n(5-yr life, {u0:.0%} utilization)",\n'
         '            (u0 * 100, be0), textcoords="offset points", xytext=(10, 14), fontsize=9)',
         'charts.annotate_clear(ax, f"base case: ${be0:.2f}/hr to break even\\n(5-yr life, {u0:.0%} utilization)",\n'
         '            (u0 * 100, be0), textcoords="offset points", xytext=(12, 18), fontsize=9)'),
        ('ax.legend(loc="upper right", fontsize=9)\n'
         'charts.save(fig, "ai_gpu_treadmill"); plt.show()',
         'charts.legend_outside(ax, loc="upper left", fontsize=9)\n'
         'charts.finish(fig); charts.save(fig, "ai_gpu_treadmill", layout=False); plt.show()'),
    ]),
    ("notebooks/ai.ipynb", "gpu_revneed", [
        ('ax.axhline(sol, color=NAVY, lw=2.0, ls="--")\n'
         'ax.text(2.46, sol + 80, f"compute revenue today (AI Solutions & Infra)  \\\\${sol:,.0f}M",\n'
         '        va="bottom", ha="right", fontsize=9, color=NAVY, fontweight="bold")\n'
         'ax.axhline(tot, color="black", lw=1.4, ls=":")\n'
         'ax.text(2.46, tot + 80, f"ALL AI revenue incl. ads  \\\\${tot:,.0f}M", va="bottom", ha="right", fontsize=9)',
         'ax.axhline(sol, color=NAVY, lw=2.0, ls="--", label=f"compute revenue today ${sol:,.0f}M")\n'
         'ax.axhline(tot, color="black", lw=1.4, ls=":", label=f"ALL AI revenue (incl. ads) ${tot:,.0f}M")'),
        ('charts.save(fig, "ai_fleet_revenue_need"); plt.show()',
         'charts.pad_ylim(ax); charts.legend_outside(ax, fontsize=9); charts.finish(fig); charts.save(fig, "ai_fleet_revenue_need", layout=False); plt.show()'),
    ]),
    ("notebooks/ai.ipynb", "sec5_code", [
        ('axL.text(gx + 0.05, (op[i] + eb[i]) / 2,\n'
         '         f"+\\\\${eb[i]-op[i]:,.0f}M \\"added back\\":\\nD&A \\\\${R.da[\'FY2025\']:,.0f}M (chips consumed)\\nSBC \\\\${R.sbc[\'FY2025\']:,.0f}M (engineer pay)\\n→ both are REAL costs",\n'
         '         va="center", ha="left", fontsize=8.0, color=ORANGE)',
         'axL.text(gx + 0.05, (op[i] + eb[i]) / 2,\n'
         '         f"+\\\\${eb[i]-op[i]:,.0f}M \\"added back\\":\\nD&A \\\\${R.da[\'FY2025\']:,.0f}M (chips consumed)\\nSBC \\\\${R.sbc[\'FY2025\']:,.0f}M (engineer pay)\\n→ both are REAL costs",\n'
         '         va="center", ha="left", fontsize=8.0, color=ORANGE,\n'
         '         bbox=dict(boxstyle="round,pad=0.35", facecolor="white", alpha=0.9, edgecolor="none"))'),
        ('axL.legend(loc="lower left", fontsize=8.2)',
         'charts.legend_outside(axL, loc="upper left", fontsize=8.2)'),
        ('    ax2.annotate(f"{p*100:.0f}%", (i, p*100), textcoords="offset points", xytext=(0, 9),',
         '    charts.annotate_clear(ax2, f"{p*100:.0f}%", (i, p*100), textcoords="offset points", xytext=(0, 11),'),
        ('charts.save(fig, "ai_adjusted_ebitda"); plt.show()',
         'fig.subplots_adjust(right=0.78); charts.finish(fig); charts.save(fig, "ai_adjusted_ebitda", layout=False); plt.show()'),
    ]),
    # --- Connectivity ---
    ("notebooks/connectivity.ipynb", "sec77_chart", [
        ('lines1, lab1 = ax.get_legend_handles_labels()\n'
         'lines2, lab2 = ax2.get_legend_handles_labels()\n'
         'ax.legend(lines1 + lines2, lab1 + lab2, fontsize=7, loc="upper right")',
         'charts.legend_merged(ax, ax2, fontsize=7, bbox_to_anchor=(1.0, 1.0))'),
        ('ax.set_ylabel("Subscribers (M)"); ax.set_title("More subs — ceiling expands with lower ARPU")\n'
         'ax.legend(fontsize=8)',
         'ax.set_ylabel("Subscribers (M)"); ax.set_title("More subs — ceiling expands with lower ARPU")\n'
         'charts.legend_outside(ax, fontsize=8, loc="upper left")'),
        ('ax.set_ylabel("Revenue ($B)"); ax.set_title("Revenue: volume nearly offsets ARPU drag")\n'
         'ax.legend()',
         'ax.set_ylabel("Revenue ($B)"); ax.set_title("Revenue: volume nearly offsets ARPU drag")\n'
         'charts.legend_outside(ax, loc="upper left")'),
        ('ax.set_title("Margin rises as cost-per-bit falls")\n'
         'ax.legend(fontsize=8)',
         'ax.set_title("Margin rises as cost-per-bit falls")\n'
         'charts.legend_outside(ax, fontsize=8, loc="lower right")'),
        ('fig.suptitle("§7.7 Affordability–cost flywheel vs §7.5 base", y=1.01)\n'
         'fig.tight_layout()\n'
         'charts.save(fig, "connectivity_flywheel"); plt.show()',
         'fig.suptitle("§7.7 Affordability–cost flywheel vs §7.5 base", y=1.02)\n'
         'fig.tight_layout(rect=[0, 0, 1, 0.96])\n'
         'charts.save(fig, "connectivity_flywheel", layout=False); plt.show()'),
    ]),
    ("notebooks/connectivity.ipynb", "fcf8_chart", [
        ('ax1.annotate(f"FY2025 actual ${FCF25/1000:.1f}B", (2025, FCF25/1000),',
         'charts.annotate_clear(ax1, f"FY2025 actual ${FCF25/1000:.1f}B", (2025, FCF25/1000),'),
        ('charts.save(fig, "connectivity_forward_fcf"); plt.show()',
         'charts.finish(fig); charts.save(fig, "connectivity_forward_fcf", layout=False); plt.show()'),
    ]),
    ("notebooks/connectivity.ipynb", "940decca", [
        ('ax.legend(loc="upper right")',
         'charts.legend_outside(ax, loc="upper left")'),
        ('charts.save(fig, "connectivity_realistic_ceiling"); plt.show()',
         'charts.pad_ylim(ax); charts.finish(fig); charts.save(fig, "connectivity_realistic_ceiling", layout=False); plt.show()'),
    ]),
    ("notebooks/connectivity.ipynb", "infra76_cadence", [
        ('ax.legend(fontsize=8, loc="upper left")',
         'charts.legend_outside(ax, fontsize=8, loc="upper left")'),
    ]),
    # --- Valuation ---
    ("notebooks/valuation.ipynb", "field_code", [
        ('ax.annotate(f"all 3 methods\\noverlap\\n~${zlo:.0f}-{zhi:.0f}B", ((zlo+zhi)/2, 0.5),\n'
         '            ha="center", va="center", fontsize=8.5, color="#8a6d3b", fontweight="bold")',
         'charts.annotate_clear(ax, f"all 3 methods overlap ~${zlo:.0f}-{zhi:.0f}B", ((zlo+zhi)/2, 0.5),\n'
         '            ha="center", va="center", fontsize=8.5, color="#8a6d3b", fontweight="bold")'),
        ('ax.annotate(f"private mark ~${pm:.0f}B\\n(Dec-2024 tender)", (pm-7, 0.55), color="#444",\n'
         '            fontsize=8.5, ha="right", va="center")\n'
         'ax.annotate("→ speculative 2026\\nchatter ~$0.8-1.75T", (pm+6, 0.55), color="#aaa",\n'
         '            fontsize=7.5, ha="left", va="center")',
         ''),
        ('ax.legend(handles=leg, fontsize=8.5, loc="lower right")\n'
         'fig.tight_layout()\n'
         'charts.save(fig, "valuation_field"); plt.show()',
         'ax.legend(handles=leg + [Line2D([0],[0], color="#444", ls="--", label=f"private mark ~${pm:.0f}B (Dec-2024)")],\n'
         '          fontsize=8.5, loc="upper left", bbox_to_anchor=(0, -0.22), ncol=2, frameon=False)\n'
         'fig.subplots_adjust(bottom=0.22)\n'
         'charts.save(fig, "valuation_field"); plt.show()'),
    ]),
    ("notebooks/valuation.ipynb", "ro_code", [
        ('ax.legend(fontsize=9, title="if it works, AI is worth:")',
         'charts.legend_outside(ax, fontsize=9, title="if it works, AI is worth:")'),
        ('charts.save(fig, "val_ai_option"); plt.show()',
         'charts.finish(fig); charts.save(fig, "val_ai_option", layout=False); plt.show()'),
    ]),
    # --- DCF ---
    ("notebooks/dcf.ipynb", "542849ad42d1", [
        ('axL.annotate("a 2030 dollar ≈ 57¢ at 12%", (2030, 1 / 1.12 ** 5), textcoords="offset points",',
         'charts.annotate_clear(axL, "a 2030 dollar ≈ 57¢ at 12%", (2030, 1 / 1.12 ** 5), textcoords="offset points",'),
        ('axL.legend(fontsize=9)',
         'charts.legend_outside(axL, fontsize=9)'),
        ('axR.legend(fontsize=9)',
         'charts.legend_outside(axR, fontsize=9)'),
    ]),
    # --- Debt ---
    ("notebooks/debt.ipynb", "5bbdc657fc95", [
        ('ax.axvline(3.75, color=RED, lw=1.6); ax.text(3.78, 1, "3.75x limit", va="center", color=RED, fontsize=9)\n'
         'ax.axvline(4.25, color=RED, lw=1.0, ls="--"); ax.text(4.28, 1, "4.25x (post-acq.)", va="center", color=RED, fontsize=8)\n'
         'ax.text(cov_ratio/2, 1, f"{cov_ratio:.2f}x", va="center", ha="center", color="white", fontweight="bold")',
         'ax.axvline(3.75, color=RED, lw=1.6, label="3.75x limit")\n'
         'ax.axvline(4.25, color=RED, lw=1.0, ls="--", label="4.25x (post-acq.)")\n'
         'ax.text(cov_ratio/2, 1, f"{cov_ratio:.2f}x", va="center", ha="center", color="white", fontweight="bold",\n'
         '        bbox=dict(boxstyle="round,pad=0.25", facecolor=RED, alpha=0.85, edgecolor="none"))'),
        ('ax.legend(loc="lower right", fontsize=9)',
         'charts.legend_outside(ax, loc="upper left", fontsize=9)'),
    ]),
    # --- Integrated ---
    ("notebooks/integrated.ipynb", "e3786c8ecae9", [
        ('axL.annotate(f"Bull stops self-funding\\nat ~{zc:.0f}% reserved", (zc+1.2, 6.5), fontsize=8.5, color="#1c6b60")',
         'charts.annotate_clear(axL, f"Bull stops self-funding\\nat ~{zc:.0f}% reserved", (zc+1.2, 6.5), fontsize=8.5, color="#1c6b60")'),
        ('axL.legend(fontsize=9, title="scenario")',
         'charts.legend_outside(axL, fontsize=9, title="scenario")'),
        ('axR.annotate("bet PAYS\\n(belief > break-even)", (1400, 18), fontsize=9, color="#1c6b60", ha="center")\n'
         'axR.annotate("value-destroying\\n(belief < break-even)", (820, 2.0), fontsize=9, color="#9b2d22", ha="center")',
         'charts.annotate_clear(axR, "bet PAYS (belief > break-even)", (1400, 22), fontsize=9, color="#1c6b60", ha="center")\n'
         'charts.annotate_clear(axR, "value-destroying (belief < break-even)", (820, 3.5), fontsize=9, color="#9b2d22", ha="center")'),
        ('    axR.annotate(lbl, (v, price/v*100), textcoords="offset points", xytext=(7,6), fontsize=8.5)',
         '    charts.annotate_clear(axR, lbl, (v, price/v*100), textcoords="offset points", xytext=(8, 8), fontsize=8.5)'),
    ]),
    ("notebooks/integrated.ipynb", "a556b9661eed", [
        ('axR.annotate("$20B bridge takeout (every scenario)", (2.42, 21), ha="right", fontsize=8.5, color="#444")',
         'charts.annotate_clear(axR, "$20B bridge takeout (every scenario)", (2.35, 21), ha="right", fontsize=8.5, color="#444")'),
        ('axL.legend(fontsize=9)',
         'charts.legend_outside(axL, fontsize=9)'),
    ]),
    ("notebooks/integrated.ipynb", "2d36f499dac6", [
        ('ax.annotate("~$2/hr: today\'s H100-class market", (41, 2.04), fontsize=8.5, color="#1b3a6b")',
         'charts.annotate_clear(ax, "~$2/hr: today\'s H100-class market", (41, 2.08), fontsize=8.5, color="#1b3a6b")'),
        ('    ax.annotate(f"{s} 2030", (u,p), textcoords="offset points", xytext=(7,5), fontsize=9, fontweight="bold")',
         '    charts.annotate_clear(ax, f"{s} 2030", (u,p), textcoords="offset points", xytext=(8, 8), fontsize=9, fontweight="bold")'),
        ('ax.legend(handles=[Line2D([0],[0], color="k", lw=2.6, label="break-even, 4.5-yr chip life"),',
         'charts.legend_outside(ax, handles=[Line2D([0],[0], color="k", lw=2.6, label="break-even, 4.5-yr chip life"),'),
    ]),
    # --- Space ---
    ("notebooks/space.ipynb", "sec6_chart", [
        ('ax.legend(loc="upper left", fontsize=9)\n'
         'ax.text(0.015, 0.60, "Open circle = first year of commercial Starship payloads;\\nR&D glides to maintenance as costs capi',
         'charts.legend_outside(ax, loc="upper left", fontsize=9)\n'
         'ax.text(0.02, 0.02, "Open circle = first year of commercial Starship payloads;\\nR&D glides to maintenance as costs capi'),
        ('charts.save(fig, "space_starship_scenarios"); plt.show()',
         'charts.finish(fig); charts.save(fig, "space_starship_scenarios", layout=False); plt.show()'),
    ]),
]


def apply_patches() -> None:
    for nb_path, cell_id, replacements in PATCHES:
        path = ROOT / nb_path
        nb = json.loads(path.read_text())
        for i, c in enumerate(nb["cells"]):
            if c.get("id") != cell_id or c["cell_type"] != "code":
                continue
            src = "".join(c["source"])
            new = src
            for old, new_s in replacements:
                if old not in new:
                    if new_s in new:
                        continue  # already patched
                    raise KeyError(f"{nb_path} [{cell_id}]: missing fragment:\n{old[:120]}...")
                new = new.replace(old, new_s, 1)
            if new != src:
                c["source"] = new.splitlines(keepends=True)
                path.write_text(json.dumps(nb, indent=1, ensure_ascii=False))
                print(f"patched {nb_path} [{cell_id}]")
            break
        else:
            raise KeyError(f"cell {cell_id} not found in {nb_path}")


if __name__ == "__main__":
    apply_patches()
