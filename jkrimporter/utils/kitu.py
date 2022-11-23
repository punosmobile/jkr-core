def short_kitu_2_long(kitu: str):
    parts = kitu.split("-")
    return (
        parts[0].rjust(3, "0")
        + parts[1].rjust(3, "0")
        + parts[2].rjust(4, "0")
        + parts[3].rjust(4, "0")
    )