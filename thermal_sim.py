"""
Engine Thermal Regulation Simulator
------------------------------------
A lumped-capacitance thermal network model of an engine's heat path, in
the spirit of the kind of thermal regulation modeling done with NPSS
(Numerical Propulsion System Simulation) -- simplified here into an
open, dependency-light form since NPSS itself is licensed software not
available outside an institutional/industry setting.

Models heat flow through a chain of thermal nodes (e.g. combustion
chamber wall -> coolant jacket -> ambient), each with its own thermal
mass, connected by conductive/convective resistances, with a
time-varying heat generation profile at the source node. Integrates the
resulting system of ODEs and flags overheating risk against a
configurable safety threshold.

Author: Yaseen Mohamed
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from scipy.integrate import solve_ivp


@dataclass
class ThermalNode:
    name: str
    mass_kg: float
    specific_heat_j_per_kgK: float
    initial_temp_k: float
    max_safe_temp_k: float = 1e9  # effectively "no limit" unless set

    @property
    def thermal_capacitance(self) -> float:
        return self.mass_kg * self.specific_heat_j_per_kgK


@dataclass
class ThermalLink:
    """A conductive/convective coupling between two nodes."""
    node_a: str
    node_b: str
    conductance_w_per_K: float  # 1 / thermal resistance


@dataclass
class HeatSource:
    """Time-varying heat generation applied to a specific node, in Watts."""
    node: str
    profile_fn: callable  # profile_fn(t) -> watts


class ThermalNetwork:
    def __init__(self, nodes: list[ThermalNode], links: list[ThermalLink],
                 sources: list[HeatSource] = None,
                 ambient_temp_k: float = 293.15,
                 ambient_conductance_w_per_K: dict[str, float] = None):
        """
        ambient_conductance_w_per_K: optional dict mapping node name -> W/K
        coupling that node has directly to a fixed-temperature ambient
        reservoir (e.g. a coolant node losing heat to outside air).
        """
        self.nodes = {n.name: n for n in nodes}
        self.node_order = [n.name for n in nodes]
        self.links = links
        self.sources = sources or []
        self.ambient_temp_k = ambient_temp_k
        self.ambient_conductance = ambient_conductance_w_per_K or {}

    def _rhs(self, t, temps):
        temp_map = dict(zip(self.node_order, temps))
        dTdt = {name: 0.0 for name in self.node_order}

        # heat generation
        for src in self.sources:
            q = src.profile_fn(t)
            dTdt[src.node] += q / self.nodes[src.node].thermal_capacitance

        # conductive links between nodes
        for link in self.links:
            dT = temp_map[link.node_b] - temp_map[link.node_a]
            q = link.conductance_w_per_K * dT  # heat flowing a -> b if dT>0
            dTdt[link.node_a] += q / self.nodes[link.node_a].thermal_capacitance
            dTdt[link.node_b] -= q / self.nodes[link.node_b].thermal_capacitance

        # loss to fixed ambient reservoir
        for name, k in self.ambient_conductance.items():
            q = k * (self.ambient_temp_k - temp_map[name])
            dTdt[name] += q / self.nodes[name].thermal_capacitance

        return [dTdt[name] for name in self.node_order]

    def simulate(self, t_end_s: float, max_step: float = 0.5) -> dict:
        t0 = [self.nodes[name].initial_temp_k for name in self.node_order]
        sol = solve_ivp(self._rhs, [0, t_end_s], t0, max_step=max_step, dense_output=True)

        result = {"t": sol.t}
        for i, name in enumerate(self.node_order):
            result[name] = sol.y[i]

        # overheating diagnostics
        alerts = []
        for name in self.node_order:
            max_temp = result[name].max()
            limit = self.nodes[name].max_safe_temp_k
            if max_temp > limit:
                over_idx = np.argmax(result[name] > limit)
                alerts.append({
                    "node": name,
                    "max_temp_k": max_temp,
                    "limit_k": limit,
                    "first_exceeded_at_s": sol.t[over_idx],
                })
        result["overheat_alerts"] = alerts
        return result


def demo_network(profile: str = "steady_burn") -> ThermalNetwork:
    """
    Chamber wall (heated by combustion) -> coolant jacket -> ambient air.
    """
    chamber = ThermalNode("chamber_wall", mass_kg=0.8, specific_heat_j_per_kgK=460,
                           initial_temp_k=293.15, max_safe_temp_k=1200.0)
    coolant = ThermalNode("coolant", mass_kg=1.5, specific_heat_j_per_kgK=4180,
                           initial_temp_k=293.15, max_safe_temp_k=370.0)

    link = ThermalLink("chamber_wall", "coolant", conductance_w_per_K=25.0)

    if profile == "steady_burn":
        def heat_fn(t):
            return 15000.0 if t < 20.0 else 0.0
    elif profile == "coolant_pump_failure":
        # combustion heat stays on for the whole burn, and the coolant loop
        # loses its heat-rejection path partway through (pump/radiator
        # failure) -- so heat has nowhere to go and temperatures run away.
        def heat_fn(t):
            return 15000.0 if t < 60.0 else 0.0
    else:
        raise ValueError(f"unknown profile {profile}")

    source = HeatSource("chamber_wall", heat_fn)

    if profile == "coolant_pump_failure":
        ambient_cond = {"coolant": 0.0}  # no heat rejection -- pump is down
    else:
        ambient_cond = {"coolant": 40.0}

    return ThermalNetwork([chamber, coolant], [link], [source],
                           ambient_temp_k=293.15,
                           ambient_conductance_w_per_K=ambient_cond)


if __name__ == "__main__":
    print("=== Scenario 1: Normal operation (coolant loop active) ===")
    net = demo_network("steady_burn")
    result = net.simulate(t_end_s=60)
    print(f"Peak chamber wall temp: {result['chamber_wall'].max():.1f} K "
          f"(limit {net.nodes['chamber_wall'].max_safe_temp_k} K)")
    print(f"Peak coolant temp: {result['coolant'].max():.1f} K "
          f"(limit {net.nodes['coolant'].max_safe_temp_k} K)")
    print(f"Overheat alerts: {result['overheat_alerts']}")

    print("\n=== Scenario 2: Coolant pump failure ===")
    net2 = demo_network("coolant_pump_failure")
    result2 = net2.simulate(t_end_s=120)
    print(f"Peak chamber wall temp: {result2['chamber_wall'].max():.1f} K "
          f"(limit {net2.nodes['chamber_wall'].max_safe_temp_k} K)")
    print(f"Peak coolant temp: {result2['coolant'].max():.1f} K "
          f"(limit {net2.nodes['coolant'].max_safe_temp_k} K)")
    print(f"Overheat alerts: {result2['overheat_alerts']}")
