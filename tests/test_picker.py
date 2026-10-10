import pytest

import db
import picker
import role_data


def test_lane_opponent_counts_fully_others_a_third(conn):
    champs, mu, _ = picker.load_full("top")
    s_main, _ = picker.score("aatrox", ["darius"], "darius", [], None, None, champs, mu)
    s_side, _ = picker.score("aatrox", ["darius"], "garen", [], None, None, champs, mu)
    assert s_main == pytest.approx(-3.0)  # dNorm -3.2 x 1.5, capped at -3
    assert s_side == pytest.approx(-1.0)


def test_low_sample_matchup_is_trusted_less(conn):
    champs, mu, _ = picker.load_full("top")
    assert mu[("aatrox", "garen")][0] == pytest.approx(2.1)  # 2.5 x 1.5 = 3.75 -> cap 3 -> x 0.7


def test_reverse_direction_is_derived(conn):
    champs, mu, _ = picker.load_full("top")
    v, tip = mu[("garen", "aatrox")]
    assert v == pytest.approx(-2.1)
    assert tip.startswith("[Aatrox's tip]")


def test_blind_style_and_damage_bonuses(conn):
    champs, mu, _ = picker.load_full("top")
    s, why = picker.score("garen", [], None, [], "wombo", "ad", champs, mu)
    assert s == pytest.approx(1 + 2 + 1)  # blind-safe 'Yes', teamfight comp, gives AD
    assert why == ["fits wombo comp", "gives AD damage", "blind-safe"]


def test_cache_refreshes_after_a_curated_edit(conn):
    assert picker.load_full("top")[0]["aatrox"]["when"] != "Edited"
    db.set_curated_champion(conn, "top", "Aatrox", {"pick_when": "Edited"})
    assert picker.load_full("top")[0]["aatrox"]["when"] == "Edited"


def test_missing_role_data_is_reported(conn):
    with pytest.raises(FileNotFoundError):
        picker.load_full("support")


@pytest.mark.parametrize("typed, expected", [("tf", "twistedfate"), ("Vi", "vi"), ("vik", "viktor")])
def test_resolve_names(typed, expected):
    champs = {"viktor": {}, "vi": {}, "twistedfate": {}}
    assert picker.resolve(typed, champs) == expected


def test_resolve_never_turns_an_exact_name_into_a_longer_one():
    assert picker.resolve("Vi", {"viktor": {}}) == "vi"  # Vi was once read as Viktor


@pytest.mark.parametrize("name", ["Aurelion Sol", "Twisted Fate", "Nunu & Willump", "Ahri"])
def test_ap_fallback_handles_multi_word_names(name):
    assert role_data.damage_of(name) == "AP"
