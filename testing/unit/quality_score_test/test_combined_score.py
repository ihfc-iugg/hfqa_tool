# testing/unit/quality_score_test/test_combine_scores.py

import pandas as pd

from quality_score.combine_scores import combine_u_m_p_scores


def test_combine_u_m_p_scores_happy_path_builds_Q_and_QP_and_rank():
    df = pd.DataFrame(
        {
            "quality_U": ["U2"],
            "quality_M": ["M3x"],         # suffix must be preserved in Q
            "quality_P": ["SxxxCxh"],     # 7 chars => preserved
        }
    )

    out = combine_u_m_p_scores(df.copy())

    assert out.loc[0, "quality_Q"] == "U2.M3x"
    assert out.loc[0, "quality_QP"] == "U2.M3x.SxxxCxh"

    # rank uses base M only (M3x -> M3) and max(U-rank, M-rank)
    # U2 rank=2, M3 rank=3 => max => 3
    assert int(out.loc[0, "quality_rank"]) == 3


def test_combine_defaults_when_columns_missing():
    # No input cols -> defaults Ux / Mx / -------
    df = pd.DataFrame({"something_else": [1, 2]})

    out = combine_u_m_p_scores(df.copy())

    assert list(out["quality_Q"]) == ["Ux.Mx", "Ux.Mx"]
    assert list(out["quality_QP"]) == ["Ux.Mx.-------", "Ux.Mx.-------"]
    assert list(out["quality_rank"]) == [9, 9]


def test_combine_invalid_values_are_normalized():
    df = pd.DataFrame(
        {
            "quality_U": ["U9", None, "U1"],     # invalid -> Ux; None -> Ux
            "quality_M": ["foo", None, "M4"],    # invalid -> Mx; None -> Mx
            "quality_P": ["too_long", None, "------"],  # invalid length -> -------; '------' len=6 -> -------
        }
    )

    out = combine_u_m_p_scores(df.copy())

    assert out.loc[0, "quality_Q"] == "Ux.Mx"
    assert out.loc[0, "quality_QP"] == "Ux.Mx.-------"
    assert int(out.loc[0, "quality_rank"]) == 9

    assert out.loc[1, "quality_Q"] == "Ux.Mx"
    assert out.loc[1, "quality_QP"] == "Ux.Mx.-------"
    assert int(out.loc[1, "quality_rank"]) == 9

    assert out.loc[2, "quality_Q"] == "U1.M4"
    assert out.loc[2, "quality_QP"] == "U1.M4.-------"
    # U1 rank=1, M4 rank=4 => rank=4
    assert int(out.loc[2, "quality_rank"]) == 4


def test_rank_ignores_m_suffix_only_for_ranking():
    df = pd.DataFrame({"quality_U": ["U4"], "quality_M": ["M1x"], "quality_P": ["-------"]})
    out = combine_u_m_p_scores(df.copy())

    # Q keeps suffix
    assert out.loc[0, "quality_Q"] == "U4.M1x"
    # rank uses base M1 (rank 1) vs U4 (rank 4) => 4
    assert int(out.loc[0, "quality_rank"]) == 4


def test_custom_separator_and_output_column_names():
    df = pd.DataFrame({"U": ["U3"], "M": ["M2"], "P": ["SExxCxh"]})

    out = combine_u_m_p_scores(
        df.copy(),
        u_col="U",
        m_col="M",
        p_col="P",
        out_col="Q",
        out_rank_col="R",
        out_col_with_p="QP",
        separator="|",
    )

    assert out.loc[0, "Q"] == "U3|M2"
    assert out.loc[0, "QP"] == "U3|M2|SExxCxh"
    # U3 rank=3, M2 rank=2 => max => 3
    assert int(out.loc[0, "R"]) == 3
