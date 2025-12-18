## Validation

### Environment

Validation was performed using **Java 11**, leveraging its built-in concurrency utilities to parallelize game validation while maintaining compliance with API constraints.

### API Rate Limiting

The NCAA public API enforces a **maximum of 5 requests per second per IP**. To respect this limitation while processing a large dataset efficiently, the complete set of game IDs (August–December) was divided into two independent subsets and validated in separate runs.

Each run implemented:

- A fixed-size thread pool
- A global rate limiter to ensure the 5 requests/second constraint was never exceeded

This approach enabled controlled parallelism without triggering API throttling.

### Dataset Partitioning and Results

| Date Range       | Total Game IDs | Valid D3 Women’s Soccer Games |
| ---------------- | -------------- | ----------------------------- |
| August–September | 1,935          | 1,871                         |
| October–December | 1,850          | 1,791                         |
| **Total**        | **3,785**      | **3,662**                     |

### Outcome

Each game ID was validated by querying the game-level endpoint and confirming:

- `sportCode = WSO` (Women’s Soccer)
- `division = 3` (NCAA Division III)

Only game IDs meeting both criteria were retained for downstream play-by-play and statistics extraction.
