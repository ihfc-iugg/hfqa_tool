import pandas as pd

from quality_score.apply_p_flags import calculate_p_flags


def test_p_flags_encoding_happy_path(quality_score_schema):
    # braucht encoding keys wie im Schema (normalisiert!)
    qc = quality_score_schema
    pf = qc["m_score"]["p_flags"]

    # minimal: baue genau die 7 columns aus pf.fields
    row = {}
    for process, col in pf["fields"].items():
        # default: unspecified -> should map to "-" (oder was encoding vorgibt)
        row[col] = "[unspecified]"

    # setze ein paar spezifische Werte, um UPPER/LOWER/X/x/- zu testen
    # Die encoding keys sind im Schema normalisiert (z.B. "[present-and-corrected]")
    #
    processes = list(pf["order"])
    if len(processes) >= 4:
        row[pf["fields"][processes[0]]] = "[present-and-corrected]"      # UPPER
        row[pf["fields"][processes[1]]] = "[present-and-not-corrected]"  # LOWER
        row[pf["fields"][processes[2]]] = "[present-not-significant]"    # X
        row[pf["fields"][processes[3]]] = "[not-recognized]"             # x

    df = pd.DataFrame([row])
    out = calculate_p_flags(df, qc).iloc[0]

    assert isinstance(out, str)
    assert len(out) == 7

    # Prüfe die ersten 4 Positionen exakt gegen die Erwartungen (UPPER/LOWER/X/x)
    # Buchstaben kommen aus pf["letters"][process]
    p0 = pf["letters"][processes[0]].upper()
    p1 = pf["letters"][processes[1]].lower()
    assert out[0] == p0
    assert out[1] == p1
    assert out[2] == "X"
    assert out[3] == "x"


def test_p_flags_missing_schema_returns_dashes():
    df = pd.DataFrame([{"C13": "[present-and-corrected]"}])
    qc_schema = {"m_score": {"p_flags": {}}}
    out = calculate_p_flags(df, qc_schema).iloc[0]
    assert out == "-------"
