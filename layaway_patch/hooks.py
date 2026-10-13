app_name = "layaway_patch"
app_title = "Layaway Patch"
app_publisher = "Antigravity"
app_description = "Independent Layaway, Deposit, Installments and Item Swap Workflow for POS Next"
app_email = "dev@antigravity.ai"
app_license = "MIT"

# Whitelisted method overrides for POS Next deposit handling
override_whitelisted_methods = {
	"pos_next.api.deposit.create_deposit_order": "layaway_patch.api.deposit.create_deposit_order",
}
