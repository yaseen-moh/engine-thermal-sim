# Engine Thermal Regulation Simulator

A lumped-capacitance thermal network simulator for modeling heat flow
through an engine's cooling path -- built in the same spirit as the
thermal regulation work done with **NPSS** (Numerical Propulsion System
Simulation) during an aerospace engineering internship, reimplemented here
as an open, dependency-light tool since NPSS itself is licensed
institutional/industry software.

## What it models

Engines are represented as a network of **thermal nodes** (e.g. combustion
chamber wall, coolant jacket, ambient air), each with its own thermal
mass (`mass x specific heat`), connected by **conductive/convective
links** with a defined thermal conductance (W/K). A time-varying heat
source can be applied to any node (e.g. combustion heat generation), and
nodes can also be coupled to a fixed-temperature ambient reservoir (e.g. a
coolant loop rejecting heat to outside air through a radiator).

The system of coupled ODEs (one per node) is integrated with
`scipy.integrate.solve_ivp`, and every node can be given a
`max_safe_temp_k` -- if the simulation ever exceeds that limit, it's
flagged as an overheat alert with the exact time it happened.

## Demo scenarios

**1. Normal operation** -- chamber wall heats up during a 20-second burn,
coolant loop actively rejects heat to ambient air the whole time. Peak
temperatures stay under both safety limits.

**2. Coolant pump / radiator failure** -- identical heat generation, but
the coolant loop's ambient heat-rejection path is cut to zero. With
nowhere for heat to go, the coolant temperature runs past its 370 K safe
limit around the 48-second mark -- exactly the kind of failure mode this
sort of model is meant to catch before it happens in hardware.

```bash
pip install -r requirements.txt

python thermal_sim.py       # prints peak temps + overheat alerts for both scenarios
python plot_thermal.py      # saves thermal_profiles.png comparing both scenarios
python -m pytest tests/ -v  # sanity tests (no false alerts, real failure IS caught, etc.)
```

## Design notes

- Uses a simple **1/R = conductance** formulation rather than modeling
  conduction/convection/radiation as physically separate mechanisms --
  conductance values are meant to be tuned to match empirical or
  finite-element results rather than derived purely analytically.
- Overheat detection is a straightforward `max(temperature) > limit` check,
  reported with the first timestep it happened rather than just a boolean,
  since knowing *when* in the burn the failure mode kicks in is the
  actionable part.

## Extending this

- Add radiative heat transfer terms (important at very high chamber wall
  temperatures where radiation dominates over conduction).
- Model coolant flow rate explicitly (mass flow x specific heat) instead
  of a fixed conductance, so pump RPM changes propagate through properly.
- Add a control loop (e.g. bang-bang or PID coolant valve) that reacts to
  temperature readings in real time, rather than a fixed on/off failure.
