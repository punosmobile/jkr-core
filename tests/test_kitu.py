from jkrimporter.utils.kitu import short_kitu_2_long


def test_short_kitu_2_long():
    assert short_kitu_2_long("12-35-4-1234") == "01203500041234"
