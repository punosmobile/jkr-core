from jkrimporter.utils.progress import Progress


def test_progress(capfd):
    p = Progress(3)
    expected = ["  0.00% [0/3]\r", " 33.33% [1/3]\r", " 66.67% [2/3]\r"]
    for i in range(3):
        p.tick()
        out, _ = capfd.readouterr()
        assert out == expected[i]

    p.complete()
    out, _ = capfd.readouterr()
    assert out == "100.00% [3/3]\r"


def test_progress_reset(capfd):
    p = Progress(3)
    expected = ["  0.00% [0/3]\r", " 33.33% [1/3]\r", " 66.67% [2/3]\r"]
    for i in range(3):
        p.tick()
        out, _ = capfd.readouterr()
        assert out == expected[i]

    p.complete()
    out, _ = capfd.readouterr()
    assert out == "100.00% [3/3]\r"

    p.reset()
    p.tick()
    out, _ = capfd.readouterr()
    assert out == "  0.00% [0/3]\r"
