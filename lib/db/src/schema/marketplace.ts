import {
  boolean,
  integer,
  pgTable,
  text,
  timestamp,
} from "drizzle-orm/pg-core";

export const marketplaceProductsTable = pgTable("marketplace_products", {
  id: text("id").primaryKey(),
  title: text("title").notNull(),
  description: text("description").notNull(),
  priceCents: integer("price_cents").notNull(),
  category: text("category").notNull(),
  imageUrl: text("image_url").notNull(),
  sellerName: text("seller_name").notNull(),
  inventory: integer("inventory").notNull().default(0),
  featured: boolean("featured").notNull().default(false),
  createdAt: timestamp("created_at", { withTimezone: true })
    .notNull()
    .defaultNow(),
});

export const marketplaceOrdersTable = pgTable("marketplace_orders", {
  id: text("id").primaryKey(),
  buyerName: text("buyer_name").notNull(),
  email: text("email").notNull(),
  address: text("address").notNull(),
  totalCents: integer("total_cents").notNull(),
  status: text("status").notNull().default("processing"),
  paymentStatus: text("payment_status").notNull().default("demo_paid"),
  createdAt: timestamp("created_at", { withTimezone: true })
    .notNull()
    .defaultNow(),
});

export const marketplaceOrderItemsTable = pgTable("marketplace_order_items", {
  id: text("id").primaryKey(),
  orderId: text("order_id")
    .notNull()
    .references(() => marketplaceOrdersTable.id, { onDelete: "cascade" }),
  productId: text("product_id").notNull(),
  title: text("title").notNull(),
  quantity: integer("quantity").notNull(),
  unitPriceCents: integer("unit_price_cents").notNull(),
  imageUrl: text("image_url").notNull(),
});
