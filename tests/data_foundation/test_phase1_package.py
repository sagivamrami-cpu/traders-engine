def test_phase1_package_imports():
    import trading_system.data_foundation as data_foundation

    assert data_foundation.QualityStatus.VALID.value == "VALID"
