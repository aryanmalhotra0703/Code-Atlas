from datetime import datetime, timedelta, timezone

from app.investigate.ranking import recency_score, blast_radius_score, composite_score_breakdown


def test_recency_score_is_high_for_today():
    assert recency_score(datetime.now(timezone.utc)) > 0.95


def test_recency_score_decays_for_old_dates():
    old_date = datetime.now(timezone.utc) - timedelta(days=365)
    assert 0 < recency_score(old_date) < 0.3


def test_recency_score_is_zero_for_missing_date():
    assert recency_score(None) == 0.0


def test_blast_radius_score_is_zero_for_no_dependents():
    assert blast_radius_score(0) == 0.0


def test_blast_radius_score_increases_with_more_dependents():
    assert blast_radius_score(5) < blast_radius_score(54)


def test_blast_radius_score_caps_near_one():
    assert blast_radius_score(1000) <= 1.0


def test_composite_score_rewards_high_similarity_recent_central_result():
    recent = datetime.now(timezone.utc)
    high = composite_score_breakdown(similarity=0.9, date=recent, total_blast_radius=50)
    low = composite_score_breakdown(similarity=0.3, date=recent - timedelta(days=400), total_blast_radius=0)
    assert high["total"] > low["total"]