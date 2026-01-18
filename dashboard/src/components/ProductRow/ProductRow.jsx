import ProductSummaryCard from './ProductSummaryCard'
import SellerChatPanel from './SellerChatPanel'
import { calculateDealMetrics } from '../../utils/metricsCalculator'

function ProductRow({ productName, data }) {
  const { listings, negotiations } = data
  const metrics = calculateDealMetrics(negotiations)

  return (
    <div className="product-row">
      <ProductSummaryCard productName={productName} metrics={metrics} />
      <SellerChatPanel negotiations={negotiations} listings={listings} />
    </div>
  )
}

export default ProductRow
