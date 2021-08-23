from thorcontrol.taskqueue import compute_engine


def test_update_metadata_list__empty():
    metadata = []
    updates = {"thor-job": "abcdefg", "thor-status": "running"}
    have = compute_engine._update_metadata_list(metadata, updates)
    want = [
        {
            "key": "thor-job",
            "value": "abcdefg",
        },
        {
            "key": "thor-status",
            "value": "running",
        },
    ]
    assert have == want


def test_update_metadata_list__modification():
    metadata = [{"key": "thor-job", "value": "none"}]
    updates = {"thor-job": "abcdefg", "thor-status": "running"}
    have = compute_engine._update_metadata_list(metadata, updates)
    want = [
        {
            "key": "thor-job",
            "value": "abcdefg",
        },
        {
            "key": "thor-status",
            "value": "running",
        },
    ]
    assert have == want


def test_update_metadata_list__ignore_existing():
    metadata = [{"key": "user-data", "value": "whatever"}]
    updates = {"thor-job": "abcdefg", "thor-status": "running"}
    have = compute_engine._update_metadata_list(metadata, updates)
    want = [
        {"key": "user-data", "value": "whatever"},
        {
            "key": "thor-job",
            "value": "abcdefg",
        },
        {
            "key": "thor-status",
            "value": "running",
        },
    ]
    assert have == want
