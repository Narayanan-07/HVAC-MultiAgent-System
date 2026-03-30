import pytest
import json
from backend.agents.tools.optimization_tools import (
    optimize_setpoints,
    recommend_chiller_sequencing,
    plan_load_shifting,
    score_maintenance_priority,
    compile_final_recommendations
)

def test_optimize_setpoints():
    scorecard = json.dumps({"avg_ikwtr": 0.85})
    # .func()
    res = json.loads(optimize_setpoints.func(scorecard, 32.0))
    assert len(res) > 0
    assert res[0]["priority"] == 1

def test_recommend_chiller_sequencing():
    # .func()
    res = json.loads(recommend_chiller_sequencing.func(60.0, 3))
    assert res["recommended_active_chillers"] == 2
    assert "rationale" in res

def test_plan_load_shifting():
    peaks = json.dumps([{"peak_start": "14:00:00"}])
    # Single arg, so .run()
    res = json.loads(plan_load_shifting.run(peaks))
    assert len(res) == 1
    assert "pre_cool_start" in res[0]

def test_score_maintenance_priority():
    report = json.dumps({"anomaly_count": 5, "pct_time_above_benchmark": 20.0})
    # .func()
    res = json.loads(score_maintenance_priority.func(report, 10.0))
    assert "priority_level" in res
    assert res["priority_score"] > 50

def test_compile_final_recommendations():
    spts = json.dumps([{"action": "test action 1", "priority": 2, "category": "Setpoints"}])
    seqs = json.dumps([{"recommended_active_chillers": 2, "category": "Sequencing"}])
    load = json.dumps([{"pre_cool_action": "test cool", "category": "Load Shifting"}])
    maint = json.dumps([{"recommended_maintenance_action": "test maint", "priority_level": "HIGH", "category": "Maintenance", "priority_score": 80}])

    res = json.loads(compile_final_recommendations.func(spts, seqs, load, maint))
    assert "recommendations" in res
    assert len(res["recommendations"]) >= 1
    assert res["total_recommendations"] <= 10