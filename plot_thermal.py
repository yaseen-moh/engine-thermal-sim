"""Plots node temperatures over time for both demo scenarios, side by side."""
import matplotlib.pyplot as plt
from thermal_sim import demo_network

fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)

for ax, profile, title in zip(
    axes, ["steady_burn", "coolant_pump_failure"],
    ["Normal Operation", "Coolant Pump Failure"]
):
    net = demo_network(profile)
    result = net.simulate(t_end_s=120)
    ax.plot(result["t"], result["chamber_wall"], label="Chamber wall")
    ax.plot(result["t"], result["coolant"], label="Coolant")
    ax.axhline(net.nodes["coolant"].max_safe_temp_k, color="red",
               linestyle="--", linewidth=1, label="Coolant safe limit")
    ax.set_title(title)
    ax.set_xlabel("time (s)")
    ax.legend(fontsize=8)

axes[0].set_ylabel("Temperature (K)")
plt.tight_layout()
plt.savefig("thermal_profiles.png", dpi=150)
print("Saved thermal_profiles.png")
