"""
app.py  —  Streamlit Visualization Dashboard

Real-time visualization of the Artificial Curiosity Civilization simulation.

Run with:
    streamlit run app.py
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import json
import time
from typing import Dict, Any, List
from collections import defaultdict

from simulation.runner import Simulation, SimulationConfig
from engine.world import Biome


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Artificial Curiosity Civilization",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background: #1e1e2e;
        border-radius: 10px;
        padding: 12px 16px;
        border-left: 4px solid #7c3aed;
    }
    .stMetric label { font-size: 0.8rem !important; }
    div[data-testid="stExpander"] { border: 1px solid #333; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------

def init_session() -> None:
    """Initialise Streamlit session state."""
    if "sim" not in st.session_state:
        st.session_state.sim = None
    if "running" not in st.session_state:
        st.session_state.running = False
    if "auto_ticks" not in st.session_state:
        st.session_state.auto_ticks = 0
    if "history_df" not in st.session_state:
        st.session_state.history_df = pd.DataFrame()


def create_simulation(cfg: SimulationConfig) -> Simulation:
    """Create a fresh simulation and cache it."""
    sim = Simulation(cfg)
    st.session_state.sim = sim
    st.session_state.history_df = pd.DataFrame()
    return sim


# ---------------------------------------------------------------------------
# Colour maps
# ---------------------------------------------------------------------------

BIOME_COLOURS = {
    "OCEAN":      "#1a6b9a",
    "FOREST":     "#2d7a2d",
    "GRASSLAND":  "#8bc34a",
    "DESERT":     "#e8c56e",
    "MOUNTAIN":   "#9e9e9e",
    "TUNDRA":     "#b0d4e3",
    "WETLAND":    "#4caf50",
    "CAVE":       "#5d4037",
    "VOLCANO":    "#e53935",
    "PLAINS":     "#cddc39",
}


# ---------------------------------------------------------------------------
# World map
# ---------------------------------------------------------------------------

def render_world_map(sim: Simulation, show_agents: bool = True) -> go.Figure:
    """Build an interactive heatmap of the world with agent overlays."""
    W = sim.config.world_width
    H = sim.config.world_height

    # Build biome grid as numeric array for colour mapping
    biome_names = [b.name for b in Biome]
    biome_index = {b: i for i, b in enumerate(Biome)}

    z = np.zeros((H, W), dtype=int)
    hover_text = [[""] * W for _ in range(H)]

    for y in range(H):
        for x in range(W):
            cell = sim.world.grid[y][x]
            z[y][x] = biome_index.get(cell.biome, 0)
            res_str = ", ".join(f"{k.name}:{v:.0f}" for k, v in cell.resources.items() if v > 0)
            hover_text[y][x] = (
                f"({x},{y}) {cell.biome.name}<br>"
                f"Elevation: {cell.elevation:.2f}<br>"
                f"Temp: {cell.temperature:.1f}°<br>"
                f"Resources: {res_str or 'none'}"
            )

    # Discrete colour scale
    n_biomes = len(Biome)
    colorscale = []
    for i, biome in enumerate(Biome):
        frac_start = i / n_biomes
        frac_end = (i + 1) / n_biomes
        colour = BIOME_COLOURS.get(biome.name, "#888888")
        colorscale.append([frac_start, colour])
        colorscale.append([frac_end, colour])

    fig = go.Figure()
    fig.add_trace(go.Heatmap(
        z=z,
        text=hover_text,
        hoverinfo="text",
        colorscale=colorscale,
        showscale=False,
        zmin=0,
        zmax=n_biomes - 1,
    ))

    # Overlay agents
    if show_agents and sim.agents:
        ax = [a.position[0] for a in sim.agents.values()]
        ay = [a.position[1] for a in sim.agents.values()]
        labels = [
            f"{a.agent_id}<br>E:{a.energy:.0f} C:{a.curiosity_level:.2f}<br>KB:{len(a.knowledge_base)}"
            for a in sim.agents.values()
        ]
        # Colour agents by curiosity
        colours = [a.curiosity_level for a in sim.agents.values()]
        fig.add_trace(go.Scatter(
            x=ax, y=ay,
            mode="markers",
            marker=dict(
                size=9,
                color=colours,
                colorscale="Plasma",
                cmin=0, cmax=1,
                line=dict(width=1, color="white"),
                colorbar=dict(title="Curiosity", x=1.02, thickness=12),
            ),
            text=labels,
            hoverinfo="text",
            name="Agents",
        ))

    fig.update_layout(
        title=f"World Map  —  Tick {sim.tick}",
        xaxis=dict(showgrid=False, zeroline=False, title="X"),
        yaxis=dict(showgrid=False, zeroline=False, title="Y", autorange="reversed"),
        plot_bgcolor="#111111",
        paper_bgcolor="#1a1a2e",
        font=dict(color="white"),
        height=420,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    return fig


# ---------------------------------------------------------------------------
# Time-series charts
# ---------------------------------------------------------------------------

def render_timeseries(df: pd.DataFrame) -> go.Figure:
    """Multi-line chart of key metrics over time."""
    if df.empty:
        fig = go.Figure()
        fig.update_layout(title="No data yet", paper_bgcolor="#1a1a2e", font=dict(color="white"))
        return fig

    fig = go.Figure()
    metrics = {
        "num_agents":    ("Agents",     "#7c3aed"),
        "avg_curiosity": ("Curiosity",  "#f59e0b"),
        "avg_knowledge": ("Knowledge",  "#10b981"),
        "avg_energy":    ("Energy",     "#3b82f6"),
    }
    for col, (label, colour) in metrics.items():
        if col in df.columns:
            fig.add_trace(go.Scatter(
                x=df["tick"], y=df[col],
                name=label,
                line=dict(color=colour, width=2),
                mode="lines",
            ))
    fig.update_layout(
        title="Civilization Metrics Over Time",
        xaxis_title="Tick",
        paper_bgcolor="#1a1a2e",
        plot_bgcolor="#111111",
        font=dict(color="white"),
        legend=dict(bgcolor="#1a1a2e"),
        height=300,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    return fig


def render_milestones_chart(df: pd.DataFrame) -> go.Figure:
    """Bar + line chart for milestones and tool discovery."""
    if df.empty:
        fig = go.Figure()
        fig.update_layout(title="No data yet", paper_bgcolor="#1a1a2e", font=dict(color="white"))
        return fig

    fig = go.Figure()
    if "milestone_count" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["tick"], y=df["milestone_count"],
            name="Milestones",
            fill="tozeroy",
            line=dict(color="#f472b6", width=2),
        ))
    if "tools_crafted" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["tick"], y=df["tools_crafted"],
            name="Tools Crafted",
            line=dict(color="#fb923c", width=2, dash="dash"),
        ))
    fig.update_layout(
        title="Cultural Progress",
        xaxis_title="Tick",
        paper_bgcolor="#1a1a2e",
        plot_bgcolor="#111111",
        font=dict(color="white"),
        legend=dict(bgcolor="#1a1a2e"),
        height=280,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    return fig


# ---------------------------------------------------------------------------
# Agent table
# ---------------------------------------------------------------------------

def render_agent_table(sim: Simulation) -> pd.DataFrame:
    """Return a DataFrame of current agents for display."""
    rows = []
    for a in sim.agents.values():
        rows.append({
            "ID": a.agent_id,
            "X": a.position[0],
            "Y": a.position[1],
            "Energy": round(a.energy, 1),
            "Curiosity": round(a.curiosity_level, 3),
            "Knowledge": len(a.knowledge_base),
            "Tools": len(a.inventory),
            "Skills": len(a.skills),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Event log
# ---------------------------------------------------------------------------

def render_event_log(sim: Simulation, n: int = 20) -> str:
    """Return the most recent n events as a newline-separated string."""
    return "\n".join(sim.event_log[-n:][::-1])


# ---------------------------------------------------------------------------
# Main app layout
# ---------------------------------------------------------------------------

def main() -> None:
    init_session()

    st.title("🌍 Artificial Curiosity Civilization")
    st.caption("An artificial life simulation where agents evolve knowledge through curiosity.")

    # ── Sidebar ────────────────────────────────────────────────────────────
    with st.sidebar:
        st.header("⚙️ Configuration")

        seed = st.number_input("Random Seed", value=42, min_value=0, max_value=9999)
        w    = st.slider("World Width",  20, 80, 40, 5)
        h    = st.slider("World Height", 15, 60, 30, 5)
        init_agents = st.slider("Initial Agents", 4, 40, 12)
        max_agents  = st.slider("Max Agents",      10, 120, 80)

        st.divider()
        st.subheader("▶ Controls")
        col1, col2 = st.columns(2)
        with col1:
            start_btn = st.button("🚀 New Sim", use_container_width=True)
        with col2:
            step_btn  = st.button("⏭ Step ×10", use_container_width=True)

        run_ticks = st.slider("Auto-run ticks", 0, 500, 0, 10)
        auto_btn  = st.button("⚡ Run", use_container_width=True)

        st.divider()
        show_agents = st.checkbox("Show agents on map", value=True)
        show_table  = st.checkbox("Show agent table",   value=False)
        show_log    = st.checkbox("Show event log",     value=True)

        st.divider()
        export_btn = st.button("💾 Export JSON state")

    # ── Button actions ─────────────────────────────────────────────────────
    if start_btn:
        cfg = SimulationConfig(
            seed=int(seed),
            world_width=w, world_height=h,
            initial_agents=init_agents,
            max_agents=max_agents,
        )
        create_simulation(cfg)
        st.success("Simulation initialised!")

    sim = st.session_state.sim

    if sim is None:
        st.info("👈 Configure and click **🚀 New Sim** in the sidebar to start.")
        st.stop()

    if step_btn:
        for _ in range(10):
            sim.step()
        st.session_state.history_df = pd.DataFrame(sim.get_history_dataframe_data())

    if auto_btn and run_ticks > 0:
        with st.spinner(f"Running {run_ticks} ticks…"):
            sim.run(run_ticks)
        st.session_state.history_df = pd.DataFrame(sim.get_history_dataframe_data())
        st.success(f"Finished {run_ticks} ticks. Now at tick {sim.tick}.")

    if export_btn:
        state = sim.get_state()
        st.download_button(
            "⬇ Download JSON",
            data=json.dumps(state, indent=2),
            file_name=f"civ_state_tick{sim.tick}.json",
            mime="application/json",
        )

    # ── KPI Row ────────────────────────────────────────────────────────────
    state = sim.get_state()
    kpi_cols = st.columns(6)
    kpis = [
        ("🕐 Tick",        sim.tick),
        ("👥 Agents",      state["totals"].get("agents", len(sim.agents))),
        ("🔭 Discoveries", state["totals"]["discoveries"]),
        ("🔧 Tools",       state["totals"]["tools_crafted"]),
        ("🏛 Milestones",  state["culture"]["milestones"]),
        ("🤝 Societies",   state["culture"]["societies"]),
    ]
    for col, (label, val) in zip(kpi_cols, kpis):
        col.metric(label, val)

    # ── World map + time series ────────────────────────────────────────────
    map_col, chart_col = st.columns([3, 2])

    with map_col:
        st.plotly_chart(render_world_map(sim, show_agents=show_agents), use_container_width=True)

    with chart_col:
        df = st.session_state.history_df
        st.plotly_chart(render_timeseries(df), use_container_width=True)
        st.plotly_chart(render_milestones_chart(df), use_container_width=True)

    # ── Agent table ────────────────────────────────────────────────────────
    if show_table:
        with st.expander("📋 Agent Details", expanded=False):
            agent_df = render_agent_table(sim)
            if not agent_df.empty:
                st.dataframe(
                    agent_df.sort_values("Curiosity", ascending=False),
                    use_container_width=True,
                    height=300,
                )

    # ── Recent milestones ─────────────────────────────────────────────────
    milestone_names = state["culture"]["milestone_names"]
    if milestone_names:
        with st.expander("🏆 Recent Milestones", expanded=True):
            for m in milestone_names[::-1]:
                st.markdown(f"- **{m}**")

    # ── Event log ─────────────────────────────────────────────────────────
    if show_log:
        with st.expander("📜 Event Log", expanded=False):
            log_text = render_event_log(sim)
            st.text(log_text if log_text else "No events yet.")

    # ── Auto-refresh ──────────────────────────────────────────────────────
    with st.expander("🔄 Auto-Refresh", expanded=False):
        refresh_rate = st.slider("Refresh every N seconds", 0, 10, 0)
        if refresh_rate > 0:
            st.write(f"Auto-refreshing every {refresh_rate}s …")
            time.sleep(refresh_rate)
            st.rerun()


if __name__ == "__main__":
    main()
