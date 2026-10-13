# Layaway Patch (layaway_patch)

An independent Frappe custom app providing layaway deposits, installment balance collection, auto-invoicing, and item swap audit trail for POS Next.

---

## App Structure

```text
layaway_patch/
|-- pyproject.toml                         (Frappe app packaging)
|-- README.md                              (Developer installation guide)
|-- layaway_patch/                         (Python App Core)
|   |-- __init__.py
|   |-- modules.txt
|   |-- hooks.py                           (Overrides pos_next deposit whitelisted methods)
|   `-- api/
|       `-- deposit.py                     (Layaway creation, payoff, item swap revisions, search)
|
`-- POS_components/                        (Frontend Vue 3 source components)
    |-- sale/
    |   |-- InvoiceCart.vue                (Auto-hold cart on layaway click & order mode switch)
    |   |-- PaymentDialog.vue              (Installment calculation, zero-balance payoff, live item search)
    |   `-- DepositOrdersDialog.vue        (Layaway orders list, filters, change of mind item swap)
    `-- pages/
        `-- POSSale.vue                    (Cart isolation & deposit event routing)
```

---

## Installation & Deployment

### Option A: Install as an Independent Frappe App
1. Copy the `layaway_patch` folder into your bench `apps/` directory:
   ```bash
   cp -r layaway_patch /path/to/frappe-bench/apps/
   ```
2. Install the app into the bench environment:
   ```bash
   cd /path/to/frappe-bench
   bench setup requirements
   bench --site <your-site-name> install-app layaway_patch
   bench --site <your-site-name> clear-cache
   ```

### Option B: Deploying the Frontend Components
Copy the modified components from `POS_components/` into your active POS Next frontend directory:
* `POS_components/sale/InvoiceCart.vue` -> `apps/pos_next_patch/POS/src/components/sale/InvoiceCart.vue` (or `apps/pos_next/POS/src/components/sale/InvoiceCart.vue`)
* `POS_components/sale/PaymentDialog.vue` -> `apps/pos_next_patch/POS/src/components/sale/PaymentDialog.vue` (or `apps/pos_next/POS/src/components/sale/PaymentDialog.vue`)
* `POS_components/sale/DepositOrdersDialog.vue` -> `apps/pos_next_patch/POS/src/components/sale/DepositOrdersDialog.vue`
* `POS_components/pages/POSSale.vue` -> `apps/pos_next_patch/POS/src/pages/POSSale.vue` (or `apps/pos_next/POS/src/pages/POSSale.vue`)

Then compile the POS frontend:
```bash
cd apps/pos_next_patch/POS  # or apps/pos_next/POS
yarn build
```

---

## Verification
1. Open POS in your browser (`/pos`).
2. Add an item to your cart in regular invoice mode.
3. Click the Layaway button:
   - Your active cart items are moved to Drafts (On Hold).
   - The mode switches to Sales Order Mode.
   - The cart is cleared and ready for the layaway order.
4. Click Pay Balance on an existing order:
   - Only the layaway balance is displayed without overpayment warnings.
   - Installment payments are recorded directly against the open shift.
