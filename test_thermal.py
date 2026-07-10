import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from thermal_sim import demo_network


def test_normal_operation_stays_within_limits():
    net = demo_network("steady_burn")
    result = net.simulate(t_end_s=60)
    assert len(result["overheat_alerts"]) == 0


def test_pump_failure_triggers_alert():
    net = demo_network("coolant_pump_failure")
    result = net.simulate(t_end_s=120)
    assert len(result["overheat_alerts"]) > 0
    assert result["overheat_alerts"][0]["node"] == "coolant"


def test_energy_flows_from_hot_to_cold():
    # chamber wall (heated) should always end up hotter than coolant
    net = demo_network("steady_burn")
    result = net.simulate(t_end_s=60)
    assert result["chamber_wall"][-1] >= result["coolant"][-1]


if __name__ == "__main__":
    test_normal_operation_stays_within_limits()
    test_pump_failure_triggers_alert()
    test_energy_flows_from_hot_to_cold()
    print("All tests passed.")
