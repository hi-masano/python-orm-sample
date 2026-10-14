import sqlalchemy


def test_sqlalchemy_is_2x():
    assert sqlalchemy.__version__.startswith("2.")
