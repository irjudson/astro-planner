def test_minimal_fixture_usage(simple_fixture):
    print(f"Test minimal_fixture_usage is running with fixture: {simple_fixture}")
    assert simple_fixture == "hello"