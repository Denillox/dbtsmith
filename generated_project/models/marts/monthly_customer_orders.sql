SELECT
    DATE_TRUNC('month', o.order_date) AS order_date_month,
    SUM(o.order_total) AS total_orders
FROM {{ ref('stg_orders') }} o
INNER JOIN {{ source('dbtsmith_output', 'customers') }} c
    ON o.email = c.email
GROUP BY DATE_TRUNC('month', o.order_date)