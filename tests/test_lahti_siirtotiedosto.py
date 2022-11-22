from jkrimporter.providers.lahti.siirtotiedosto import LahtiSiirtotiedosto


def test_readable(datadir):
    assert LahtiSiirtotiedosto.readable_by_me(datadir)


def test_kohteet(datadir):
    kohteet = LahtiSiirtotiedosto(datadir).kohteet
    assert 'UrakoitsijaId' in kohteet.headers
