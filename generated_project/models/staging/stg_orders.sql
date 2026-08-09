SELECT
    id,
    customer_id,
    order_total,
    order_date,
    email
FROM (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY email
            ORDER BY id
        ) AS rn
    FROM {{ source('dbtsmith_output', 'orders') }}
) deduped
WHERE rn = 1