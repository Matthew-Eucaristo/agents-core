# Pricing rules

How an order is priced. Finance owns these rules and the code in `pricing/` follows them.

Catalogue prices are in dollars and whole cents and never include tax. Whenever a rule below produces a fraction of a cent, the result is rounded half up to the cent before it is used in the next step.

## Subtotal

The subtotal is the sum of unit price × quantity over the lines of the order.

## Bulk discount

Larger orders earn a percentage off the subtotal.

| Subtotal             | Discount |
|----------------------|----------|
| under 500.00         | none     |
| 500.00 to 1,999.99   | 5%       |
| 2,000.00 to 4,999.99 | 10%      |
| 5,000.00 and over    | 15%      |

One tier applies to the whole subtotal; tiers are not marginal.

The bulk discount is applied before tax:

1. the tier is chosen from the subtotal, which never includes tax;
2. the discount is that percentage of the subtotal;
3. tax is then charged on the subtotal minus the discount.

## Tax

Sales tax is charged on the discounted subtotal at the rate of the order's region. The rates are in `pricing/tax.py`. A region without sales tax has a rate of zero.

## Total

total = subtotal − discount + tax

A quote records all four amounts: subtotal, discount, tax and total.

## Worked example

37 monitor arms at 129.90 delivered to TX (6.25%):

| Step                         | Amount   |
|------------------------------|----------|
| Subtotal, 37 × 129.90        | 4,806.30 |
| Bulk discount, 10%           | 480.63   |
| Discounted subtotal          | 4,325.67 |
| Tax, 6.25% of 4,325.67       | 270.35   |
| Total                        | 4,596.02 |
