def should_retry(current_round: int, max_rounds: int) -> bool:
    return current_round < max_rounds
