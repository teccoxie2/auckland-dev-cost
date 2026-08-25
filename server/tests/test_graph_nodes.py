from app.graph import WORKFLOW


def test_workflow_has_planned_nodes():
    names = set(WORKFLOW.get_graph().nodes)
    for node in (
        "geocode",
        "land",
        "rules",
        "site_vision",
        "typology",
        "quantity",
        "building_rules",
        "cost",
        "explain",
        "pm_gate",
    ):
        assert node in names
    assert "options" not in names
