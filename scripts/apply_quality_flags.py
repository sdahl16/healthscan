from __future__ import annotations

import json

from healthscan.database import connect
from healthscan.indexer import quality_flag_for_amount


def main() -> None:
    connection = connect()
    rows = connection.execute("SELECT id, amount, code_type, price_type FROM indexed_prices").fetchall()
    updates = [
        (
            quality_flag_for_amount(
                amount=float(row["amount"]),
                code_type=str(row["code_type"]),
                price_type=str(row["price_type"]),
            ),
            int(row["id"]),
        )
        for row in rows
    ]
    connection.executemany("UPDATE indexed_prices SET data_quality_flag = ? WHERE id = ?", updates)
    connection.commit()

    summary = connection.execute(
        """
        SELECT data_quality_flag, COUNT(*) AS count
        FROM indexed_prices
        GROUP BY data_quality_flag
        ORDER BY data_quality_flag
        """
    ).fetchall()
    print(json.dumps([dict(row) for row in summary], indent=2))


if __name__ == "__main__":
    main()
