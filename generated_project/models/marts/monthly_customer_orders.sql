SELECT
    DATE_TRUNC('month', o.order_date) AS month,
    SUM(o.order_total) AS total_order_value
FROM {{ ref('stg_orders') }} o
LEFT JOIN {{ source('dbtsmith_output', 'customers') }} c
    ON o.email = c.email
GROUP BY DATE_TRUNC('month', o.order_date)