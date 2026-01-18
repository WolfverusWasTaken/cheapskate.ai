import { getProductIcon } from '../../utils/productIconMapper'

function ProductSummaryCard({ productName, metrics }) {
  const icon = getProductIcon(productName)
  const { totalSavings, averageDiscount, bestDeal } = metrics

  return (
    <div className="product-summary">
      <div className="product-summary__icon">{icon}</div>
      <div className="product-summary__name">{productName}</div>

      <div className="product-summary__metrics">
        <div className="product-summary__metric">
          <span className="product-summary__metric-value product-summary__metric-value--savings">
            ${totalSavings}
          </span>
          <span className="product-summary__metric-label">Total Savings</span>
        </div>

        <div className="product-summary__metric">
          <span className="product-summary__metric-value product-summary__metric-value--discount">
            {averageDiscount}%
          </span>
          <span className="product-summary__metric-label">Avg Discount</span>
        </div>

        <div className="product-summary__metric">
          <span className="product-summary__metric-value product-summary__metric-value--best">
            {bestDeal}%
          </span>
          <span className="product-summary__metric-label">Best Deal</span>
        </div>
      </div>
    </div>
  )
}

export default ProductSummaryCard
