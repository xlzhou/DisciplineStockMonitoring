from app.indicator_engine import compute_ema, compute_rsi, compute_sma, compute_vwap


def test_compute_sma():
    values = [1, 2, 3, 4, 5]
    result = compute_sma(values, 3)
    assert result == [None, None, 2.0, 3.0, 4.0]


def test_compute_ema():
    values = [1, 2, 3, 4, 5]
    result = compute_ema(values, 3)
    assert result[0:2] == [None, None]
    assert result[2] == 2.0
    assert result[3] > 2.0


def test_compute_rsi():
    values = [1, 2, 3, 4, 5, 6]
    result = compute_rsi(values, 3)
    assert result[0:3] == [None, None, None]
    assert result[3] is not None


def test_compute_vwap():
    prices = [10, 20, 30, 40]
    volumes = [1, 1, 1, 1]
    result = compute_vwap(prices, volumes, 2)
    assert result == [None, 15.0, 25.0, 35.0]
