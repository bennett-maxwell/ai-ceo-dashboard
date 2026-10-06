# B3 required PRIMARY_AGENTS

Replace the tuple in build.py. Do not merge until that replace is in the same commit.

```python
PRIMARY_AGENTS = (
    ("3edcf5514fd381c18e9ad31f16369f38", ("Dot",)),
    ("3edcf5514fd3815aa780ca4aff45c771", ("Hank",)),
    ("3edcf5514fd3812ea137d3ce41dafab3", ("Dash",)),
    ("3edcf5514fd381d7a91dd8a7bdcccb87", ("Mack CLI", "Mack")),
    ("3f1cf5514fd38106b7f7d96897094996", ("Grok A", "GROK A")),
    ("3f1cf5514fd3810d8039f1bd9d264265", ("Grok B", "GROK B")),
    ("3f1cf5514fd3819d80f2d342673d139f", ("Grok C", "GROK C")),
)
```

Dropped: Rocky 3edcf5514fd381659d38cbb6d9a1a51a, Leo 3edcf5514fd38108b4f4e2d2e319ebe2.
Branch base: 9a600be. build.py on this branch still has the old tuple until the replace commit.
