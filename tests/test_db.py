import pytest

import db


@pytest.mark.parametrize(
    "dnorm, games, expected",
    [
        (2.0, 500, "Favored"),
        (1.99, 500, "Even"),
        (-2.0, 500, "Unfavored"),
        (5.0, 199, "low sample"),
        (5.0, None, "Favored"),
    ],
)
def test_label_thresholds(dnorm, games, expected):
    assert db.label(dnorm, games) == expected


@pytest.mark.parametrize(
    "raw, expected", [("Favoured", "Favored"), ("Even / skill", "Even"), ("unfavored", "Unfavored")]
)
def test_norm_label(raw, expected):
    assert db.norm_label(raw) == expected


def test_combined_averages_both_directions(conn):
    comb = db.combined(db.lola_rows(conn, "top"))
    a = comb[("Aatrox", "Darius")]
    assert a["dnorm"] == pytest.approx(-3.2)
    assert a["wr"] == pytest.approx(45.5)  # 46 and 100 - 55
    assert a["games"] == 880
    assert a["source"] == "both"
    assert comb[("Aatrox", "Garen")]["source"] == "direct"


def champ(conn, name):
    return next(c for c in db.champions(conn, "top") if c["name"] == name)


def test_champion_defaults_and_hand_edits(conn):
    assert champ(conn, "Aatrox")["when"] == "You need a frontline with damage and sustain"  # role_data default
    db.set_hand_champion(conn, "top", "Aatrox", {"pick_when": "Hand text", "good_into": "my note"})
    a = champ(conn, "Aatrox")
    assert a["when"] == "Hand text"
    assert a["good"] == "Garen; my note"  # data-derived names first (Garen +2.5), then the hand note
    assert a["arch"] == "Diver"  # untouched fields keep the default


def test_resetting_every_field_removes_the_hand_row(conn):
    db.set_hand_champion(conn, "top", "Aatrox", {"pick_when": "x"})
    db.set_hand_champion(conn, "top", "Aatrox", {"pick_when": ""})
    assert conn.execute("SELECT count(*) FROM hand_champion").fetchone()[0] == 0


def test_unknown_champion_falls_back_to_flex_without_leading_semicolon(conn):
    z = champ(conn, "Zaahen")
    assert z["arch"] == "Flex"
    assert not z["good"].startswith(";")


def test_set_hand_champion_rejects_unknown_fields(conn):
    with pytest.raises(ValueError):
        db.set_hand_champion(conn, "top", "Aatrox", {"hack": "x"})


def rows(conn):
    return {(r["champ"], r["opp"]): r for r in db.matchups(conn, "top")}


def test_matchup_rows_and_labels(conn):
    m = rows(conn)
    assert m[("Aatrox", "Darius")]["label"] == "Unfavored"
    assert m[("Aatrox", "Darius")]["result"] == "Unfavored"
    assert m[("Aatrox", "Garen")]["label"] == "low sample"
    assert ("Aatrox", "Zaahen") not in m  # 50 games, no hand data


def test_hand_tip_keeps_a_thin_row(conn):
    db.set_hand_matchup(conn, "top", "Aatrox", "Zaahen", tip="Hand tip")
    r = rows(conn)[("Aatrox", "Zaahen")]
    assert r["tip"] == "Hand tip"
    assert r["games"] == 50


def test_hand_label_without_data_is_kept(conn):
    db.set_hand_matchup(conn, "top", "Garen", "Kled", result="Favored")
    r = rows(conn)[("Garen", "Kled")]
    assert (r["label"], r["result"], r["wr"]) == ("no data", "Favored", None)


def test_hand_label_disagreeing_with_data_is_a_mismatch(conn):
    db.set_hand_matchup(conn, "top", "Garen", "Darius", result="Favored")
    r = rows(conn)[("Garen", "Darius")]
    assert (r["result"], r["label"], r["mismatch"]) == ("Favored", "Even", "yes")


def test_low_sample_is_never_a_mismatch(conn):
    db.set_hand_matchup(conn, "top", "Aatrox", "Garen", result="Unfavored")
    assert rows(conn)[("Aatrox", "Garen")]["mismatch"] is None


def test_clearing_label_and_tip_deletes_the_row(conn):
    db.set_hand_matchup(conn, "top", "Garen", "Darius", result="Favored", tip="t")
    db.set_hand_matchup(conn, "top", "Garen", "Darius", result="", tip="")
    assert conn.execute("SELECT count(*) FROM hand_matchup").fetchone()[0] == 0


def test_reddit_tips_from_both_subreddits(conn):
    r = rows(conn)[("Aatrox", "Darius")]
    assert r["reddit_tips"] == "Aatrox mains on Darius | [Darius mains] Darius mains on Aatrox"
    assert r["reddit_mentions"] == 5
    assert r["reddit_newest"] == "2026-01-02"


def test_writes_bump_the_stamp(conn):
    before = db.stamp(conn)
    db.set_hand_matchup(conn, "top", "Garen", "Darius", tip="t")
    assert db.stamp(conn) == before + 1


def test_backup_is_a_full_copy(conn, tmp_path):
    db.set_hand_matchup(conn, "top", "Garen", "Darius", tip="kept")
    dest = tmp_path / "backups" / "copy.db"
    db.backup(dest)
    copy = db.connect(dest)
    assert copy.execute("SELECT tip FROM hand_matchup").fetchone()[0] == "kept"
    copy.close()
