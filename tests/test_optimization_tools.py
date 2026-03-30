import pytest
import json
from backend.agents.tools.optimization_tools import (
    optimize_setpoints, recommend_chiller_sequencing,
    plan_load_shifting, score_maintenance_priority,
    compile_final_recommendations
)

def test_setpoint_optimization_high_ikwtr():
    scorecard = json.dumps({"avg_ikwtr": 0.82, "efficiency_grade": "F", "ambient_temp_c": 28.0})
    result = json.loads(optimize_setpoints.run(scorecard))
    assert len(result) > 0
    actions = [r['action'] for r in result]
    assert any('setpoint' in a.lower() or 'inspect' in a.lower() for a in actions)

def test_chiller_sequencing_low_load():
    result = json.loads(recommend_chiller_sequencing.run("30.0, 3"))
    assert result['recommended_active_chillers'] == 1

def test_chiller_sequencing_high_load():
    result = json.loads(recommend_chiller_sequencing.run("95.0, 3"))
    assert result['recommended_active_chillers'] == 3

def test_maintenance_score_in_range():
    anomaly_report = json.dumps({"anomaly_count": 15, "pct_time_above_benchmark": 40, "degradation_score": 65.0})
    result = json.loads(score_maintenance_priority.run(anomaly_report))
    assert 0 <= result['priority_score'] <= 100
    assert result['priority_level'] in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']

def test_rationale_not_empty():
    scorecard = json.dumps({"avg_ikwtr": 0.75, "efficiency_grade": "D", "ambient_temp_c": 32.0})
    result = json.loads(optimize_setpoints.run(scorecard))
    for rec in result:
        assert len(rec.get('rationale', '')) > 20, "Rationale too short"

def test_compile_max_10_recommendations():
    dummy = json.dumps([{"action": f"Action {i}", "rationale": "test",
                         "priority": i, "category": "test",
                         "expected_impact": "low", "priority_score": i*10}
                        for i in range(1, 15)])
    result = json.loads(compile_final_recommendations.run(dummy))
    assert result['total_recommendations'] <= 10