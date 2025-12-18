## Validation

### Environment

Validation was performed using **Java 11** to leverage its built-in concurrency utilities to parallelize game validation while maintaining compliance with API constraints.

### API Rate Limiting

The NCAA public API enforces a **maximum of 5 requests per second per IP**. To respect this limitation while processing a large dataset efficiently, we divided the complete set of game IDs (August–December) into two independent subsets and validated each subset in separate runs.

To enable controlled parallelism without triggering API throttling, we implemented each run with:

- A fixed-size thread pool
- A global rate limiter to ensure the 5 requests/second constraint was never exceeded

### Dataset Partitioning and Results

| Date Range       | Total Game IDs | Valid D3 Women’s Soccer Games |
| ---------------- | -------------- | ----------------------------- |
| August–September | 1,935          | 1,871                         |
| October–December | 1,850          | 1,791                         |
| **Total**        | **3,785**      | **3,662**                     |

### Outcome

We validated each game ID by querying the game-level endpoint and confirming:

- `sportCode = WSO` (Women’s Soccer)
- `division = 3` (NCAA Division III)

We only kept game IDs meeting both criteria for downstream play-by-play and statistics extraction.
