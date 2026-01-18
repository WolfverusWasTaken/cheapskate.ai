// Mock data for demo - real data comes from chat_history.json
export const mockData = {
  "iPhone 14 Pro 256GB": {
    listings: [
      { seller: "techseller88", price: 800 },
      { seller: "iphoneking", price: 850 },
      { seller: "mobilemall", price: 780 },
    ],
    negotiations: {
      "techseller88_iPhone 14 Pro 256GB": {
        listing: {
          title: "iPhone 14 Pro 256GB",
          price: 800.0,
          seller_name: "techseller88",
          listing_url: "https://www.carousell.sg/p/iphone-14-pro-123456"
        },
        started_at: "2026-01-16T10:30:00.000000",
        messages: [
          {
            role: "lowballer",
            content: "Hey! Love the iPhone 14 Pro. I know $523 is low but that's my budget - can do cash and immediate pickup?",
            offer_price: 523,
            round: 1,
            timestamp: "2026-01-16T10:30:15.000000",
            sent: true
          },
          {
            role: "seller",
            content: "Can do $750 fastest",
            timestamp: "2026-01-16T10:35:00.000000"
          },
          {
            role: "lowballer",
            content: "Got it. How about $683 with immediate collection? Trying to make it easy for you.",
            offer_price: 683,
            round: 2,
            timestamp: "2026-01-16T10:36:00.000000",
            sent: true
          },
          {
            role: "seller",
            content: "Ok deal at $700",
            timestamp: "2026-01-16T10:40:00.000000"
          },
          {
            role: "lowballer",
            content: "Deal! $700 works for me. When can I collect?",
            offer_price: 700,
            round: 3,
            timestamp: "2026-01-16T10:41:00.000000",
            sent: true
          }
        ],
        current_round: 3,
        status: "accepted",
        final_price: 700
      }
    }
  },

  "AirPods Pro 2": {
    listings: [
      { seller: "gadgetworld", price: 250 },
      { seller: "audiosg", price: 240 },
      { seller: "techdeals", price: 260 },
    ],
    negotiations: {
      "gadgetworld_AirPods Pro 2": {
        listing: {
          title: "AirPods Pro 2",
          price: 250.0,
          seller_name: "gadgetworld",
          listing_url: "https://www.carousell.sg/p/airpods-456789"
        },
        started_at: "2026-01-15T14:00:00.000000",
        messages: [
          {
            role: "lowballer",
            content: "Hi there! $163 might be cheeky but I'm serious buyer with cash. How can we make this work?",
            offer_price: 163,
            round: 1,
            timestamp: "2026-01-15T14:00:30.000000",
            sent: true
          },
          {
            role: "seller",
            content: "Price firm",
            timestamp: "2026-01-15T14:05:00.000000"
          },
          {
            role: "lowballer",
            content: "Firm? I understand. Would $213 work if I pickup within the hour? Cash in hand.",
            offer_price: 213,
            round: 2,
            timestamp: "2026-01-15T14:06:00.000000",
            sent: true
          },
          {
            role: "seller",
            content: "No nego sorry",
            timestamp: "2026-01-15T14:10:00.000000"
          },
          {
            role: "lowballer",
            content: "I totally understand if $238 doesn't work for you. Good luck with the sale!",
            offer_price: 238,
            round: 5,
            timestamp: "2026-01-15T14:11:00.000000",
            sent: true
          }
        ],
        current_round: 5,
        status: "walked_away"
      }
    }
  },

  "MacBook Air M2": {
    listings: [
      { seller: "applefan", price: 1200 },
      { seller: "laptopzone", price: 1150 },
      { seller: "techbarn", price: 1280 },
      { seller: "gadgethub", price: 1100 },
    ],
    negotiations: {}
  }
}
