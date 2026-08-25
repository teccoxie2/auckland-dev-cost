from app.models import CostEstimate, SchemeOption, SiteSnapshot
from app.store import create_project, get_project, list_projects, reset_engine, session, update_project


def test_relational_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'projects.sqlite'}")
    reset_engine()
    record = create_project(
        "39 Nelson Street, Auckland Central",
        {
            "site": {
                "captured_at": "2026-08-24T00:00:00+00:00",
                "zone": {"zone_code": 60, "zone_name": "Mixed Housing Urban"},
                "parcel": {"found": True, "area_m2": 500},
            },
            "rules": {"permitted_dwellings": 3, "coverage": 0.5},
            "options": [
                {
                    "id": "compact_3bed2bath",
                    "template": {"kind": "standalone", "dwellings": 1, "gfa_m2": 110},
                    "verdict": {"status": "permitted"},
                    "totals": {
                        "confirmed_total_incl_gst": 12.0,
                        "missing_count": 2,
                        "pricebook_version": "2026-08-24",
                    },
                    "lines": [],
                }
            ],
        },
        "ready",
    )
    loaded = get_project(record["id"])
    assert loaded is not None
    assert loaded["address"] == "39 Nelson Street, Auckland Central"
    assert loaded["result"]["site"]["parcel"]["area_m2"] == 500
    listed = list_projects()
    assert listed[0]["id"] == record["id"]
    with session() as db:
        snaps = db.query(SiteSnapshot).filter_by(project_id=record["id"]).all()
        schemes = db.query(SchemeOption).filter_by(project_id=record["id"]).all()
        estimates = db.query(CostEstimate).filter_by(project_id=record["id"]).all()
        assert len(snaps) == 1
        assert snaps[0].area_m2 == 500
        assert snaps[0].zone_code == "60"
        assert len(schemes) == 1
        assert schemes[0].option_key == "compact_3bed2bath"
        assert len(estimates) == 1
        assert estimates[0].pricebook_version == "2026-08-24"
    updated = update_project(record["id"], {**loaded["result"], "explanation": "ok"}, "ready")
    assert updated is not None
    assert updated["result"]["explanation"] == "ok"
