def looks_flaky(test_code: str) -> bool:
    flaky_markers = ["Thread.sleep", "@RepeatedTest", "random(", "Math.random"]
    return any(marker in test_code for marker in flaky_markers)
