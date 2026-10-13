# Copyright (c) 2026, Antigravity / WoolMatt ERP
# For license information, please see license.txt

import json
import traceback
import frappe
from frappe import _
from frappe.utils import (
	flt,
	cint,
	nowdate,
	nowtime,
	get_datetime,
	add_days,
	date_diff,
	formatdate,
)


def _set_approved_workflow_state(doc):
	"""Dynamically set the approved state for a document under active workflow before submitting."""
	wf_name = frappe.db.get_value("Workflow", {"document_type": doc.doctype, "is_active": 1}, "name")
	if wf_name:
		approved_state = frappe.db.get_value(
			"Workflow Document State",
			{"parent": wf_name, "doc_status": "1"},
			"state"
		)
		if approved_state and frappe.get_meta(doc.doctype).has_field("workflow_state"):
			frappe.db.set_value(doc.doctype, doc.name, "workflow_state", approved_state, update_modified=False)
			doc.reload()


def _ensure_revision_table_exists():
	"""Create the POS Layaway Revision table if it does not already exist."""
	frappe.db.sql("""
		CREATE TABLE IF NOT EXISTS `tabPOS Layaway Revision` (
			`name` VARCHAR(140) NOT NULL PRIMARY KEY,
			`sales_order` VARCHAR(140) NOT NULL,
			`revision_no` INT(11) DEFAULT 1,
			`cashier` VARCHAR(140),
			`pos_profile` VARCHAR(140),
			`posting_date` DATE,
			`posting_time` TIME,
			`reason` TEXT,
			`changes_summary` TEXT,
			`old_grand_total` DECIMAL(21,9) DEFAULT 0.0,
			`new_grand_total` DECIMAL(21,9) DEFAULT 0.0,
			`price_difference` DECIMAL(21,9) DEFAULT 0.0,
			`total_paid_so_far` DECIMAL(21,9) DEFAULT 0.0,
			`old_balance` DECIMAL(21,9) DEFAULT 0.0,
			`new_balance` DECIMAL(21,9) DEFAULT 0.0,
			`items_before` LONGTEXT,
			`items_after` LONGTEXT,
			`creation` DATETIME(6),
			`modified` DATETIME(6),
			`modified_by` VARCHAR(140),
			`owner` VARCHAR(140),
			`docstatus` INT(1) DEFAULT 0,
			INDEX (`sales_order`),
			INDEX (`posting_date`)
		) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
	""")


def _get_order_revisions(sales_order_name):
	"""Fetch all revisions / item modifications logged for a Sales Order."""
	_ensure_revision_table_exists()
	revs = frappe.db.sql("""
		SELECT 
			name,
			sales_order,
			revision_no,
			cashier,
			pos_profile,
			posting_date,
			posting_time,
			reason,
			changes_summary,
			old_grand_total,
			new_grand_total,
			price_difference,
			total_paid_so_far,
			old_balance,
			new_balance,
			items_before,
			items_after,
			creation
		FROM `tabPOS Layaway Revision`
		WHERE sales_order = %s
		ORDER BY revision_no ASC
	""", sales_order_name, as_dict=1)

	result = []
	for r in revs:
		items_b = []
		items_a = []
		try:
			items_b = json.loads(r.items_before) if r.items_before else []
		except Exception:
			pass
		try:
			items_a = json.loads(r.items_after) if r.items_after else []
		except Exception:
			pass

		result.append({
			"name": r.name,
			"sales_order": r.sales_order,
			"revision_no": cint(r.revision_no),
			"cashier": r.cashier or "",
			"pos_profile": r.pos_profile or "",
			"posting_date": str(r.posting_date or ""),
			"posting_time": str(r.posting_time or ""),
			"reason": r.reason or "",
			"changes_summary": r.changes_summary or "",
			"old_grand_total": flt(r.old_grand_total),
			"new_grand_total": flt(r.new_grand_total),
			"price_difference": flt(r.price_difference),
			"total_paid_so_far": flt(r.total_paid_so_far),
			"old_balance": flt(r.old_balance),
			"new_balance": flt(r.new_balance),
			"items_before": items_b,
			"items_after": items_a,
			"creation": str(r.creation or "")
		})
	return result


@frappe.whitelist()
def search_customers(query=None):
	if not query:
		return frappe.get_all(
			"Customer",
			fields=["name", "customer_name", "mobile_no"],
			limit=20,
			order_by="modified desc"
		)
	q = f"%{query}%"
	return frappe.db.sql(
		"""
		SELECT name, customer_name, mobile_no
		FROM `tabCustomer`
		WHERE disabled = 0 AND (name LIKE %s OR customer_name LIKE %s OR mobile_no LIKE %s)
		LIMIT 20
		""",
		(q, q, q),
		as_dict=1
	)


@frappe.whitelist()
def search_items(query=None, warehouse=None):
	if not query:
		return []
	q = f"%{query}%"
	items = frappe.db.sql(
		"""
		SELECT 
			i.name as item_code,
			i.item_name,
			i.stock_uom,
			i.description,
			ip.price_list_rate as rate
		FROM `tabItem` i
		LEFT JOIN `tabItem Price` ip ON ip.item_code = i.name AND ip.selling = 1
		WHERE i.disabled = 0 
		  AND i.is_sales_item = 1
		  AND (i.name LIKE %s OR i.item_name LIKE %s OR i.barcode LIKE %s)
		LIMIT 25
		""",
		(q, q, q),
		as_dict=1
	)
	for itm in items:
		if not itm.get("rate") or itm.get("rate") == 0:
			itm["rate"] = 100.0
		if warehouse:
			itm["actual_qty"] = frappe.db.get_value(
				"Bin",
				{"item_code": itm["item_code"], "warehouse": warehouse},
				"actual_qty"
			) or 0
	return items


def _get_receivable_account(company):
	acc = frappe.db.get_value(
		"Account",
		{"account_type": "Receivable", "company": company, "is_group": 0},
		"name"
	)
	if not acc:
		acc = frappe.db.get_value("Company", company, "default_receivable_account")
	return acc


def _get_cash_account(mode_of_payment, company):
	mop_name = mode_of_payment
	if "mpesa" in mop_name.lower():
		mop_name = "M-Pesa"
	elif "bank" in mop_name.lower() or "visa" in mop_name.lower() or "card" in mop_name.lower():
		mop_name = frappe.db.get_value("Mode of Payment", {"name": ["like", "%Bank%"]}, "name") or "Bank"

	acc = frappe.db.get_value(
		"Mode of Payment Account",
		{"parent": mop_name, "company": company},
		"default_account"
	)
	if not acc:
		acc = frappe.db.get_value(
			"Mode of Payment Account",
			{"parent": mode_of_payment, "company": company},
			"default_account"
		)
	if not acc:
		acc_type = "Bank" if ("bank" in mode_of_payment.lower() or "card" in mode_of_payment.lower() or "visa" in mode_of_payment.lower()) else "Cash"
		acc = frappe.db.get_value("Account", {"account_type": acc_type, "company": company, "is_group": 0}, "name")
	if not acc:
		acc = frappe.db.get_value("Account", {"account_type": "Cash", "company": company, "is_group": 0}, "name")
	return acc


def _make_payment_entry(so, amount, mode_of_payment, company, pos_opening_shift=None, payment_reference=None):
	receivable_account = _get_receivable_account(company)
	cash_account = _get_cash_account(mode_of_payment, company)
	cost_center = frappe.db.get_value("Company", company, "cost_center")

	valid_shift = pos_opening_shift if (pos_opening_shift and frappe.db.exists("POS Opening Shift", pos_opening_shift)) else None
	ref_num = valid_shift if valid_shift else (payment_reference or so.name)

	pe = frappe.get_doc({
		"doctype": "Payment Entry",
		"payment_type": "Receive",
		"posting_date": nowdate(),
		"company": company,
		"mode_of_payment": mode_of_payment or "Cash",
		"party_type": "Customer",
		"party": so.customer,
		"paid_from": receivable_account,
		"paid_to": cash_account,
		"paid_amount": flt(amount),
		"received_amount": flt(amount),
		"reference_no": ref_num,
		"reference_date": nowdate(),
		"remarks": f"Layaway deposit payment ({mode_of_payment}) for Sales Order {so.name}. Shift: {valid_shift or 'N/A'}. Ref: {payment_reference or so.name}",
		"pos_opening_shift": valid_shift,
		"references": [{
			"reference_doctype": "Sales Order",
			"reference_name": so.name,
			"bill_no": so.name,
			"due_date": so.delivery_date or nowdate(),
			"total_amount": flt(so.grand_total),
			"outstanding_amount": flt(so.grand_total),
			"allocated_amount": flt(amount),
		}]
	})
	if cost_center:
		pe.cost_center = cost_center

	pe.flags.ignore_permissions = True
	pe.flags.ignore_workflow = True
	pe.insert(ignore_permissions=True)

	_set_approved_workflow_state(pe)

	pe.flags.ignore_permissions = True
	pe.flags.ignore_workflow = True
	pe.submit()
	return pe.name


@frappe.whitelist()
def create_deposit_order(
	customer=None,
	customer_phone=None,
	items=None,
	total_amount=0,
	deposit_amount=0,
	mode_of_payment="Cash",
	expected_delivery_date=None,
	company=None,
	pos_terminal=None,
	pos_opening_shift=None,
	payment_reference=None,
	mpesa_receipt=None
):
	try:
		if isinstance(items, str):
			items = json.loads(items)

		total_amount = flt(total_amount)
		deposit_amount = flt(deposit_amount)

		if not company:
			company = frappe.db.get_value("Company", {"is_group": 0}, "name") or frappe.defaults.get_user_default("Company")

		# Customer Resolution
		customer_id = None
		if customer and frappe.db.exists("Customer", customer):
			customer_id = customer
		else:
			existing_cust = frappe.db.get_value("Customer", {"customer_name": customer}, "name")
			if not existing_cust and customer_phone:
				existing_cust = frappe.db.get_value("Customer", {"mobile_no": customer_phone}, "name")

			if existing_cust:
				customer_id = existing_cust
			else:
				cg = frappe.db.get_value("Customer Group", {"is_group": 0}, "name") or "Individual"
				ter = frappe.db.get_value("Territory", {"is_group": 0}, "name") or "Kenya"
				cust_doc = frappe.get_doc({
					"doctype": "Customer",
					"customer_name": customer or "Walk-in Customer",
					"mobile_no": customer_phone or "",
					"customer_type": "Individual",
					"customer_group": cg,
					"territory": ter
				})
				cust_doc.insert(ignore_permissions=True)
				customer_id = cust_doc.name

		wh = frappe.db.get_value("Warehouse", {"is_group": 0, "company": company}, "name") or frappe.db.get_value("Warehouse", {"is_group": 0}, "name")

		so_items = []
		if items and isinstance(items, list) and len(items) > 0:
			for item in items:
				item_code = item.get("item_code")
				if not item_code or not frappe.db.exists("Item", item_code):
					fallback_item = frappe.db.get_value("Item", {"is_sales_item": 1}, "name")
					if not fallback_item:
						frappe.throw(f"Item '{item_code}' does not exist.")
					item_code = fallback_item

				qty = flt(item.get("qty", 1))
				rate = flt(item.get("rate", 0))
				if rate <= 0:
					price = frappe.db.get_value("Item Price", {"item_code": item_code, "selling": 1}, "price_list_rate")
					rate = flt(price) if price else 100.0

				so_items.append({
					"item_code": item_code,
					"qty": qty,
					"rate": rate,
					"amount": qty * rate,
					"warehouse": item.get("warehouse") or wh
				})
		else:
			frappe.throw("At least one item must be selected.")

		calc_total = sum([i["amount"] for i in so_items])
		if total_amount <= 0:
			total_amount = calc_total

		if deposit_amount > (total_amount + 0.05):
			frappe.throw(f"Deposit amount (KES {deposit_amount:,.2f}) cannot exceed total order value (KES {total_amount:,.2f}).")

		# Create & Submit Sales Order
		delivery_dt = expected_delivery_date or add_days(nowdate(), 75)
		so = frappe.get_doc({
			"doctype": "Sales Order",
			"company": company,
			"customer": customer_id,
			"set_warehouse": wh,
			"delivery_date": delivery_dt,
			"items": so_items,
			"po_no": f"DEPOSIT-{customer_id}-{deposit_amount}-{frappe.generate_hash(length=6)}",
		})
		for tax in so.get("taxes", []):
			if tax.charge_type != "Actual":
				tax.included_in_print_rate = 1
		so.calculate_taxes_and_totals()
		so.flags.ignore_permissions = True
		so.flags.ignore_workflow = True
		so.insert(ignore_permissions=True)

		_set_approved_workflow_state(so)

		so.flags.ignore_permissions = True
		so.flags.ignore_workflow = True
		so.submit()

		# Record Deposit Payment Entry
		pe_name = None
		if deposit_amount > 0:
			pe_name = _make_payment_entry(
				so,
				deposit_amount,
				mode_of_payment,
				company,
				pos_opening_shift=pos_opening_shift,
				payment_reference=payment_reference or mpesa_receipt
			)

		frappe.db.commit()

		return {
			"status": "SUCCESS",
			"sales_order": so.name,
			"customer": customer_id,
			"payment_entry": pe_name,
			"total_amount": flt(so.grand_total),
			"deposit_amount": deposit_amount,
			"balance_due": max(0.0, round(flt(so.grand_total) - deposit_amount, 2)),
			"delivery_date": str(delivery_dt),
			"mode_of_payment": mode_of_payment,
			"reference": payment_reference or mpesa_receipt
		}
	except Exception as e:
		frappe.db.rollback()
		err_msg = traceback.format_exc()
		frappe.log_error(err_msg, "POS Layaway Create Deposit Error")
		raise e


@frappe.whitelist()
def get_deposit_orders(search_term=None, status=None, company=None, pos_profile=None):
	"""
	Search and retrieve all active Layaway/Deposit Sales Orders with payment breakdown and overdue status.
	"""
	conditions = ["so.docstatus = 1", "so.status NOT IN ('Closed', 'Cancelled')"]
	values = {}

	if company:
		conditions.append("so.company = %(company)s")
		values["company"] = company

	where_clause = " AND ".join(conditions)

	sql = f"""
		SELECT 
			so.name,
			so.customer,
			so.customer_name,
			so.grand_total,
			so.advance_paid,
			so.per_billed,
			so.per_delivered,
			so.po_no,
			so.delivery_date,
			so.transaction_date,
			so.creation,
			so.status as so_status,
			c.mobile_no as customer_phone
		FROM `tabSales Order` so
		LEFT JOIN `tabCustomer` c ON c.name = so.customer
		WHERE {where_clause}
		ORDER BY so.creation DESC
		LIMIT 150
	"""
	orders = frappe.db.sql(sql, values, as_dict=1)
	today_dt = nowdate()

	result = []
	for o in orders:
		# Sum of submitted Payment Entries referencing this SO
		payments = frappe.db.sql("""
			SELECT 
				per.allocated_amount,
				pe.name as payment_entry,
				pe.mode_of_payment,
				pe.posting_date,
				pe.paid_amount,
				pe.pos_opening_shift,
				pe.owner,
				pe.creation
			FROM `tabPayment Entry Reference` per
			JOIN `tabPayment Entry` pe ON pe.name = per.parent
			WHERE per.reference_doctype = 'Sales Order' 
			  AND per.reference_name = %s 
			  AND pe.docstatus = 1
			ORDER BY pe.creation ASC
		""", o.name, as_dict=1)

		# Check if payments were allocated to a submitted Sales Invoice for this SO
		inv_payments = frappe.db.sql("""
			SELECT 
				per.allocated_amount,
				pe.name as payment_entry,
				pe.mode_of_payment,
				pe.posting_date,
				pe.paid_amount,
				pe.pos_opening_shift,
				pe.owner,
				pe.creation
			FROM `tabPayment Entry Reference` per
			JOIN `tabPayment Entry` pe ON pe.name = per.parent
			WHERE per.reference_doctype = 'Sales Invoice'
			  AND per.reference_name IN (
				SELECT parent FROM `tabSales Invoice Item` WHERE sales_order = %s AND docstatus = 1
			  )
			  AND pe.docstatus = 1
			ORDER BY pe.creation ASC
		""", o.name, as_dict=1)

		all_payments = payments + [p for p in inv_payments if p.payment_entry not in [x.payment_entry for x in payments]]
		paid_advance = sum([flt(p.allocated_amount or p.paid_amount) for p in all_payments])

		if (paid_advance == 0 or paid_advance < flt(o.advance_paid)) and o.advance_paid:
			paid_advance = flt(o.advance_paid)

		if flt(o.per_billed) >= 100.0 and paid_advance >= flt(o.grand_total) - 1.0:
			paid_advance = flt(o.grand_total)

		balance_due = max(0.0, round(flt(o.grand_total) - paid_advance, 2))
		is_fully_paid = balance_due <= 0.01 or flt(o.per_billed) >= 100.0

		# Calculate overdue status
		delivery_date_str = str(o.delivery_date) if o.delivery_date else ""
		is_overdue = False
		days_overdue = 0
		if delivery_date_str and not is_fully_paid:
			diff = date_diff(today_dt, delivery_date_str)
			if diff > 0:
				is_overdue = True
				days_overdue = diff

		# If already billed 100% and closed, mark completed
		if flt(o.per_billed) >= 100.0:
			order_status = "Completed"
		elif is_fully_paid:
			order_status = "Fully Paid"
		elif is_overdue:
			order_status = "Overdue"
		elif paid_advance > 0:
			order_status = "Partially Paid"
		else:
			order_status = "Unpaid"

		# Filter by status if requested
		if status:
			st_filter = status.lower().strip()
			if st_filter == "pending" and is_fully_paid:
				continue
			elif st_filter == "paid" and not is_fully_paid:
				continue
			elif st_filter == "overdue" and not is_overdue:
				continue

		# Filter by search_term across customer, SO ID, phone, PO#
		if search_term:
			st = str(search_term).lower().strip()
			matched = (
				st in str(o.name).lower() or
				st in str(o.customer or "").lower() or
				st in str(o.customer_name or "").lower() or
				st in str(o.customer_phone or "").lower() or
				st in str(o.po_no or "").lower()
			)
			if not matched:
				continue

		# Item summary
		items = frappe.get_all(
			"Sales Order Item",
			filters={"parent": o.name},
			fields=["item_code", "item_name", "qty", "rate", "amount", "uom", "stock_uom"]
		)
		items_summary = ", ".join([f"{i.item_name or i.item_code} (x{i.qty})" for i in items])

		result.append({
			"name": o.name,
			"sales_order": o.name,
			"order_name": o.name,
			"customer": o.customer,
			"customer_name": o.customer_name or o.customer,
			"customer_phone": o.customer_phone or "",
			"transaction_date": str(o.transaction_date or ""),
			"delivery_date": delivery_date_str,
			"is_overdue": is_overdue,
			"days_overdue": days_overdue,
			"creation": str(o.creation),
			"items_summary": items_summary,
			"items": items,
			"grand_total": flt(o.grand_total),
			"advance_paid": paid_advance,
			"deposit_amount": paid_advance,
			"paid_amount": paid_advance,
			"balance_due": balance_due,
			"is_fully_paid": is_fully_paid,
			"per_billed": flt(o.per_billed),
			"per_delivered": flt(o.per_delivered),
			"status": order_status,
			"payment_history": [
				{
					"payment_entry": p.payment_entry,
					"mode_of_payment": p.mode_of_payment,
					"posting_date": str(p.posting_date),
					"creation": str(p.creation),
					"allocated_amount": flt(p.allocated_amount or p.paid_amount),
					"cashier": p.owner,
					"shift": p.pos_opening_shift or ""
				}
				for p in payments
			],
			"revisions": _get_order_revisions(o.name)
		})

	return result


@frappe.whitelist()
def get_order_balance(sales_order_name):
	"""
	Fetch live balance and payment breakdown for a single Sales Order with row locking.
	"""
	if not sales_order_name:
		frappe.throw(_("Sales Order name is required."))

	so = frappe.get_doc("Sales Order", sales_order_name)
	payments = frappe.db.sql("""
		SELECT 
			per.allocated_amount,
			pe.name as payment_entry,
			pe.mode_of_payment,
			pe.posting_date,
			pe.paid_amount,
			pe.pos_opening_shift,
			pe.owner,
			pe.creation
		FROM `tabPayment Entry Reference` per
		JOIN `tabPayment Entry` pe ON pe.name = per.parent
		WHERE per.reference_doctype = 'Sales Order' 
		  AND per.reference_name = %s 
		  AND pe.docstatus = 1
		ORDER BY pe.creation ASC
	""", sales_order_name, as_dict=1)

	# Also include payments that were transferred to auto-generated Sales Invoice for this SO
	inv_payments = frappe.db.sql("""
		SELECT 
			per.allocated_amount,
			pe.name as payment_entry,
			pe.mode_of_payment,
			pe.posting_date,
			pe.paid_amount,
			pe.pos_opening_shift,
			pe.owner,
			pe.creation
		FROM `tabPayment Entry Reference` per
		JOIN `tabPayment Entry` pe ON pe.name = per.parent
		WHERE per.reference_doctype = 'Sales Invoice'
		  AND per.reference_name IN (
			SELECT parent FROM `tabSales Invoice Item` WHERE sales_order = %s AND docstatus = 1
		  )
		  AND pe.docstatus = 1
		ORDER BY pe.creation ASC
	""", sales_order_name, as_dict=1)

	all_payments = payments + [p for p in inv_payments if p.payment_entry not in [x.payment_entry for x in payments]]
	paid_advance = sum([flt(p.allocated_amount or p.paid_amount) for p in all_payments])

	if (paid_advance == 0 or paid_advance < flt(so.advance_paid)) and so.advance_paid:
		paid_advance = flt(so.advance_paid)

	if flt(so.per_billed) >= 100.0 and paid_advance >= flt(so.net_total):
		paid_advance = flt(so.grand_total)

	balance_due = max(0.0, round(flt(so.grand_total) - paid_advance, 2))
	is_fully_paid = balance_due <= 0.01 or flt(so.per_billed) >= 100.0

	delivery_date_str = str(so.delivery_date) if so.delivery_date else ""
	is_overdue = False
	days_overdue = 0
	if delivery_date_str and not is_fully_paid:
		diff = date_diff(nowdate(), delivery_date_str)
		if diff > 0:
			is_overdue = True
			days_overdue = diff

	items = [
		{
			"item_code": i.item_code,
			"item_name": i.item_name,
			"qty": i.qty,
			"rate": i.rate,
			"amount": i.amount,
			"uom": i.uom
		}
		for i in so.items
	]

	return {
		"sales_order": so.name,
		"customer": so.customer,
		"customer_name": so.customer_name or so.customer,
		"grand_total": flt(so.grand_total),
		"paid_amount": paid_advance,
		"balance_due": balance_due,
		"is_fully_paid": is_fully_paid,
		"delivery_date": delivery_date_str,
		"is_overdue": is_overdue,
		"days_overdue": days_overdue,
		"per_billed": flt(so.per_billed),
		"per_delivered": flt(so.per_delivered),
		"items": items,
		"payment_history": [
			{
				"payment_entry": p.payment_entry,
				"mode_of_payment": p.mode_of_payment,
				"posting_date": str(p.posting_date),
				"allocated_amount": flt(p.allocated_amount or p.paid_amount),
				"cashier": p.owner,
				"shift": p.pos_opening_shift or ""
			}
			for p in payments
		],
		"revisions": _get_order_revisions(sales_order_name)
	}


@frappe.whitelist()
def pay_deposit_balance(
	sales_order_name,
	mode_of_payment="Cash",
	amount=None,
	pos_profile=None,
	pos_opening_shift=None,
	mpesa_receipt=None,
	payments=None
):
	"""
	Record subsequent installment payment(s) against an existing Sales Order.
	If balance reaches zero, automatically checkout and convert to Sales Invoice.
	"""
	if not sales_order_name:
		frappe.throw(_("Sales Order name is required."))

	# Parse payments array if supplied
	payment_list = []
	if payments:
		if isinstance(payments, str):
			payment_list = json.loads(payments)
		elif isinstance(payments, list):
			payment_list = payments

	savepoint_name = "layaway_payment_sp"
	try:
		frappe.db.savepoint(savepoint_name)

		# Row-level lock on Sales Order
		frappe.db.sql("SELECT name FROM `tabSales Order` WHERE name = %s FOR UPDATE", sales_order_name)
		so = frappe.get_doc("Sales Order", sales_order_name)

		if so.docstatus != 1:
			frappe.throw(_("Sales Order {0} is not submitted.").format(sales_order_name))
		if so.status in ("Closed", "Cancelled"):
			frappe.throw(_("Sales Order {0} is {1}.").format(sales_order_name, so.status))

		company = so.company

		# Calculate current actual balance
		existing_payments = frappe.db.sql("""
			SELECT SUM(per.allocated_amount) as total
			FROM `tabPayment Entry Reference` per
			JOIN `tabPayment Entry` pe ON pe.name = per.parent
			WHERE per.reference_doctype = 'Sales Order' 
			  AND per.reference_name = %s 
			  AND pe.docstatus = 1
		""", sales_order_name, as_dict=1)

		already_paid = flt(existing_payments[0].total) if (existing_payments and existing_payments[0].total) else flt(so.advance_paid or 0)
		actual_balance = max(0.0, flt(so.grand_total) - already_paid)

		if actual_balance <= 0.01:
			# Already paid; if not yet invoiced, finalize now
			final_invoice = None
			if flt(so.per_billed) < 100.0:
				final_invoice = finalize_deposit_order(sales_order_name, pos_opening_shift, pos_profile)
			return {
				"status": "SUCCESS",
				"message": _("Sales Order {0} is already fully paid.").format(sales_order_name),
				"sales_order": sales_order_name,
				"amount_paid": 0,
				"balance_due": 0,
				"is_fully_paid": True,
				"sales_invoice": final_invoice.get("sales_invoice") if final_invoice else None
			}

		# Determine payments to process
		if not payment_list:
			pay_amt = flt(amount) if (amount and flt(amount) > 0) else actual_balance
			payment_list = [{"mode_of_payment": mode_of_payment or "Cash", "amount": pay_amt}]

		total_paying = sum([flt(p.get("amount", 0)) for p in payment_list])
		if total_paying <= 0:
			frappe.throw(_("Total payment amount must be greater than zero."))

		if total_paying > (actual_balance + 0.05):
			frappe.throw(
				_("Payment amount (KES {0:,.2f}) exceeds outstanding balance (KES {1:,.2f}).").format(
					total_paying, actual_balance
				)
			)

		# Create Payment Entries for each mode
		created_pes = []
		for p in payment_list:
			p_mode = p.get("mode_of_payment") or "Cash"
			p_amount = flt(p.get("amount", 0))
			if p_amount <= 0:
				continue

			pe_name = _make_payment_entry(
				so,
				p_amount,
				p_mode,
				company,
				pos_opening_shift=pos_opening_shift,
				payment_reference=mpesa_receipt or p.get("reference_no")
			)
			created_pes.append(pe_name)

		# Reload SO to check balance
		so.reload()
		new_paid = already_paid + total_paying
		new_balance = max(0.0, flt(so.grand_total) - new_paid)
		is_fully_paid = new_balance <= 0.01

		final_invoice_data = None
		if is_fully_paid:
			# Auto-checkout: Convert Sales Order to Sales Invoice with stock deduction & advance allocation
			final_invoice_data = finalize_deposit_order(
				sales_order_name,
				pos_opening_shift=pos_opening_shift,
				pos_profile=pos_profile
			)

		frappe.db.commit()

		return {
			"status": "SUCCESS",
			"message": _("Payment of KES {0:,.2f} recorded for {1}. Remaining balance: KES {2:,.2f}").format(
				total_paying, sales_order_name, new_balance
			),
			"payment_entries": created_pes,
			"payment_entry": created_pes[0] if created_pes else None,
			"sales_order": sales_order_name,
			"amount_paid": total_paying,
			"previous_balance": actual_balance,
			"balance_due": new_balance,
			"advance_paid": new_paid,
			"grand_total": flt(so.grand_total),
			"is_fully_paid": is_fully_paid,
			"sales_invoice": final_invoice_data.get("sales_invoice") if final_invoice_data else None,
			"invoice_details": final_invoice_data
		}
	except Exception as e:
		frappe.db.rollback(save_point=savepoint_name)
		err_msg = traceback.format_exc()
		frappe.log_error(err_msg, "POS Layaway Pay Balance Error")
		raise e


@frappe.whitelist()
def finalize_deposit_order(sales_order_name, pos_opening_shift=None, pos_profile=None):
	"""
	Convert a fully paid Sales Order into a submitted POS Sales Invoice:
	- Sets allocate_advances_automatically = 1 to absorb all advances
	- Updates stock (update_stock = 1)
	- Tags shift (posa_pos_opening_shift = pos_opening_shift)
	- Marks Sales Order status Completed
	"""
	if not sales_order_name:
		frappe.throw(_("Sales Order name is required."))

	from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice

	# Check if already billed
	so = frappe.get_doc("Sales Order", sales_order_name)
	if flt(so.per_billed) >= 100.0:
		existing_si = frappe.db.get_value(
			"Sales Invoice Item",
			{"sales_order": sales_order_name, "docstatus": 1},
			"parent"
		)
		if existing_si:
			return {
				"status": "SUCCESS",
				"sales_invoice": existing_si,
				"already_billed": True
			}

	# Generate Sales Invoice from Sales Order
	si = make_sales_invoice(sales_order_name)
	si.is_pos = 0  # Paid via advances, not direct cash register
	si.update_stock = 1

	if not pos_profile and pos_opening_shift:
		pos_profile = frappe.db.get_value("POS Opening Shift", pos_opening_shift, "pos_profile")
	if not pos_profile:
		pos_profile = frappe.db.get_value("POS Profile", {"company": si.company, "disabled": 0}, "name")

	if pos_profile:
		si.pos_profile = pos_profile
		prof = frappe.get_cached_doc("POS Profile", pos_profile)
		si.cost_center = si.cost_center or prof.cost_center
		si.set_warehouse = si.set_warehouse or prof.warehouse
		for itm in si.items:
			if not itm.warehouse:
				itm.warehouse = prof.warehouse or si.set_warehouse

	if pos_opening_shift and frappe.db.exists("POS Opening Shift", pos_opening_shift):
		si.posa_pos_opening_shift = pos_opening_shift
		si.pos_opening_shift = pos_opening_shift

	si.flags.pos_next_redeemed_customer_credit = 1
	si.flags.ignore_permissions = True
	si.flags.ignore_workflow = True

	try:
		from pos_next.api.sales_invoice_hooks import apply_tax_inclusive
		apply_tax_inclusive(si)
	except Exception:
		pass

	si.calculate_taxes_and_totals()
	si.allocate_advances_automatically = 1
	si.set_advances()

	target_total = flt(si.rounded_total) if flt(si.rounded_total) > 0 else flt(si.grand_total)
	running_adv = 0.0
	for adv in si.get('advances', []):
		alloc = flt(adv.allocated_amount)
		if running_adv + alloc > target_total:
			adv.allocated_amount = max(0.0, round(target_total - running_adv, 2))
		running_adv += flt(adv.allocated_amount)

	si.calculate_taxes_and_totals()
	si.insert(ignore_permissions=True)

	_set_approved_workflow_state(si)

	si.flags.ignore_permissions = True
	si.flags.ignore_workflow = True
	si.submit()

	# Verify SO status
	so.reload()

	return {
		"status": "SUCCESS",
		"sales_invoice": si.name,
		"grand_total": flt(si.grand_total),
		"total_advance": flt(si.total_advance),
		"outstanding_amount": flt(si.outstanding_amount),
		"customer": si.customer,
		"customer_name": si.customer_name,
		"posting_date": str(si.posting_date),
		"posting_time": str(si.posting_time),
		"items": [
			{
				"item_code": itm.item_code,
				"item_name": itm.item_name,
				"qty": itm.qty,
				"rate": itm.rate,
				"amount": itm.amount
			}
			for itm in si.items
		]
	}


@frappe.whitelist()
def cancel_deposit_order(sales_order_name, reason=None, pos_opening_shift=None):
	"""
	Safely cancel a Sales Order with layaway deposits.
	"""
	if not sales_order_name:
		frappe.throw(_("Sales Order name is required."))

	so = frappe.get_doc("Sales Order", sales_order_name)
	if flt(so.per_billed) > 0:
		frappe.throw(_("Cannot cancel Sales Order {0} because it has already been invoiced.").format(sales_order_name))

	if so.docstatus == 2:
		frappe.throw(_("Sales Order {0} is already cancelled.").format(sales_order_name))

	# Find and cancel active Payment Entries
	payments = frappe.db.sql("""
		SELECT pe.name
		FROM `tabPayment Entry Reference` per
		JOIN `tabPayment Entry` pe ON pe.name = per.parent
		WHERE per.reference_doctype = 'Sales Order' 
		  AND per.reference_name = %s 
		  AND pe.docstatus = 1
	""", sales_order_name, as_dict=1)

	for p in payments:
		pe_doc = frappe.get_doc("Payment Entry", p.name)
		pe_doc.flags.ignore_permissions = True
		pe_doc.flags.ignore_workflow = True
		pe_doc.cancel()

	so.reload()
	so.flags.ignore_permissions = True
	so.flags.ignore_workflow = True
	so.cancel()
	if reason:
		so.add_comment("Comment", f"Layaway cancelled at POS. Reason: {reason}")

	frappe.db.commit()
	return {
		"status": "SUCCESS",
		"message": _("Sales Order {0} and linked deposit payments cancelled.").format(sales_order_name)
	}


@frappe.whitelist()
def get_order_revisions(sales_order_name):
	"""Return all revisions / item modifications logged for a Sales Order."""
	if not sales_order_name:
		frappe.throw(_("Sales Order name is required."))
	return _get_order_revisions(sales_order_name)


@frappe.whitelist()
def modify_layaway_items(
	sales_order_name,
	new_items,
	reason="Customer change of mind",
	cashier=None,
	pos_profile=None
):
	"""
	Modify items on a Layaway Sales Order (change of mind / item swap).
	Recalculates totals, updates balance, and logs full audit revision trail.
	"""
	if not sales_order_name:
		frappe.throw(_("Sales Order name is required."))

	if isinstance(new_items, str):
		new_items = json.loads(new_items)

	if not new_items or not isinstance(new_items, list) or len(new_items) == 0:
		frappe.throw(_("At least one item is required in the updated order."))

	_ensure_revision_table_exists()

	# Lock Sales Order
	frappe.db.sql("SELECT name FROM `tabSales Order` WHERE name = %s FOR UPDATE", sales_order_name)
	so = frappe.get_doc("Sales Order", sales_order_name)

	if so.docstatus != 1:
		frappe.throw(_("Sales Order {0} must be in submitted state.").format(sales_order_name))
	if so.status in ("Closed", "Cancelled"):
		frappe.throw(_("Cannot modify Sales Order {0} because it is {1}.").format(sales_order_name, so.status))
	if flt(so.per_billed) >= 100.0:
		frappe.throw(_("Cannot modify Sales Order {0} because it has already been invoiced.").format(sales_order_name))

	# Snapshot items before
	items_before = [
		{
			"item_code": item.item_code,
			"item_name": item.item_name or item.item_code,
			"qty": flt(item.qty),
			"rate": flt(item.rate),
			"amount": flt(item.amount or (item.qty * item.rate)),
			"uom": item.uom or item.stock_uom or "Nos",
			"warehouse": item.warehouse
		}
		for item in so.items
	]
	old_grand_total = flt(so.grand_total)

	# Calculate payments already made
	existing_payments = frappe.db.sql("""
		SELECT SUM(per.allocated_amount) as total
		FROM `tabPayment Entry Reference` per
		JOIN `tabPayment Entry` pe ON pe.name = per.parent
		WHERE per.reference_doctype = 'Sales Order' 
		  AND per.reference_name = %s 
		  AND pe.docstatus = 1
	""", sales_order_name, as_dict=1)
	already_paid = flt(existing_payments[0].total) if (existing_payments and existing_payments[0].total) else flt(so.advance_paid or 0)
	old_balance = max(0.0, old_grand_total - already_paid)

	# Build new items list
	company = so.company
	wh = frappe.db.get_value("Warehouse", {"is_group": 0, "company": company}, "name") or (so.items and so.items[0].warehouse)

	so.items = []
	items_after = []
	total_new_amount = 0.0

	for itm in new_items:
		item_code = itm.get("item_code")
		if not item_code or not frappe.db.exists("Item", item_code):
			frappe.throw(_("Item '{0}' does not exist.").format(item_code))

		qty = flt(itm.get("qty", 1))
		if qty <= 0:
			frappe.throw(_("Quantity for item '{0}' must be greater than zero.").format(item_code))

		rate = flt(itm.get("rate", 0))
		if rate <= 0:
			price = frappe.db.get_value("Item Price", {"item_code": item_code, "selling": 1}, "price_list_rate")
			rate = flt(price) if price else 100.0

		item_name = itm.get("item_name") or frappe.db.get_value("Item", item_code, "item_name") or item_code
		uom = itm.get("uom") or frappe.db.get_value("Item", item_code, "stock_uom") or "Nos"
		item_wh = itm.get("warehouse") or wh
		line_amount = round(qty * rate, 2)
		total_new_amount += line_amount

		so.append("items", {
			"item_code": item_code,
			"item_name": item_name,
			"qty": qty,
			"rate": rate,
			"amount": line_amount,
			"uom": uom,
			"stock_uom": uom,
			"conversion_factor": 1.0,
			"warehouse": item_wh,
			"delivery_date": so.delivery_date or add_days(nowdate(), 30)
		})

		items_after.append({
			"item_code": item_code,
			"item_name": item_name,
			"qty": qty,
			"rate": rate,
			"amount": line_amount,
			"uom": uom,
			"warehouse": item_wh
		})

	# Calculate taxes and totals
	try:
		from pos_next.api.sales_invoice_hooks import apply_tax_inclusive
		apply_tax_inclusive(so)
	except Exception:
		pass

	so.calculate_taxes_and_totals()
	new_grand_total = flt(so.grand_total) if flt(so.grand_total) > 0 else total_new_amount
	new_balance = max(0.0, new_grand_total - already_paid)
	price_difference = round(new_grand_total - old_grand_total, 2)

	# Update child rows in DB
	frappe.db.sql("DELETE FROM `tabSales Order Item` WHERE parent = %s", so.name)
	for idx, item_row in enumerate(so.items, start=1):
		item_row.name = frappe.generate_hash(length=10)
		item_row.idx = idx
		item_row.parent = so.name
		item_row.parenttype = "Sales Order"
		item_row.parentfield = "items"
		item_row.docstatus = 1
		item_row.db_insert()

	# Update parent doc totals
	frappe.db.set_value("Sales Order", so.name, {
		"total": so.total or total_new_amount,
		"net_total": so.net_total or total_new_amount,
		"base_total": so.base_total or total_new_amount,
		"base_net_total": so.base_net_total or total_new_amount,
		"grand_total": new_grand_total,
		"base_grand_total": so.base_grand_total or new_grand_total,
		"rounded_total": so.rounded_total or new_grand_total,
		"base_rounded_total": so.base_rounded_total or new_grand_total,
		"rounding_adjustment": so.rounding_adjustment or 0.0,
		"modified": frappe.utils.now_datetime(),
		"modified_by": frappe.session.user
	}, update_modified=False)

	# Determine human-readable changes summary
	before_map = {i["item_code"]: i for i in items_before}
	after_map = {i["item_code"]: i for i in items_after}

	added = []
	removed = []
	modified = []

	for code, a_item in after_map.items():
		if code not in before_map:
			added.append(f"+ {a_item['qty']}x {a_item['item_name']} @ KES {a_item['rate']:,.2f}")
		elif before_map[code]["qty"] != a_item["qty"] or before_map[code]["rate"] != a_item["rate"]:
			modified.append(f"Qty {before_map[code]['qty']}->{a_item['qty']} / Rate KES {before_map[code]['rate']:,.2f}->{a_item['rate']:,.2f} for {a_item['item_name']}")

	for code, b_item in before_map.items():
		if code not in after_map:
			removed.append(f"- {b_item['qty']}x {b_item['item_name']}")

	changes_parts = []
	if added:
		changes_parts.append("Added: " + ", ".join(added))
	if removed:
		changes_parts.append("Removed: " + ", ".join(removed))
	if modified:
		changes_parts.append("Modified: " + ", ".join(modified))

	changes_summary = "; ".join(changes_parts) if changes_parts else "Items updated"

	# Calculate revision number
	prev_count = cint(frappe.db.sql("SELECT COUNT(*) FROM `tabPOS Layaway Revision` WHERE sales_order = %s", sales_order_name)[0][0] or 0)
	revision_no = prev_count + 1
	rev_name = frappe.generate_hash(length=12)

	current_cashier = cashier or frappe.session.user

	# Insert revision log
	frappe.db.sql("""
		INSERT INTO `tabPOS Layaway Revision` (
			name, sales_order, revision_no, cashier, pos_profile,
			posting_date, posting_time, reason, changes_summary,
			old_grand_total, new_grand_total, price_difference,
			total_paid_so_far, old_balance, new_balance,
			items_before, items_after,
			creation, modified, modified_by, owner, docstatus
		) VALUES (
			%s, %s, %s, %s, %s,
			%s, %s, %s, %s,
			%s, %s, %s,
			%s, %s, %s,
			%s, %s,
			%s, %s, %s, %s, 0
		)
	""", (
		rev_name, sales_order_name, revision_no, current_cashier, pos_profile or "",
		nowdate(), nowtime(), reason or "Customer change of mind", changes_summary,
		old_grand_total, new_grand_total, price_difference,
		already_paid, old_balance, new_balance,
		json.dumps(items_before), json.dumps(items_after),
		frappe.utils.now_datetime(), frappe.utils.now_datetime(), frappe.session.user, frappe.session.user
	))

	# Post comment on Sales Order
	diff_sign = "+" if price_difference >= 0 else ""
	comment_text = f"Layaway Revision #{revision_no} ({current_cashier}): {changes_summary}. Total: KES {old_grand_total:,.2f} -> KES {new_grand_total:,.2f} ({diff_sign}KES {price_difference:,.2f}). New Balance: KES {new_balance:,.2f}. Reason: {reason or 'Customer change of mind'}."
	so.add_comment("Comment", comment_text)

	frappe.db.commit()

	return {
		"status": "SUCCESS",
		"message": _("Sales Order {0} updated successfully.").format(sales_order_name),
		"sales_order": sales_order_name,
		"revision_no": revision_no,
		"changes_summary": changes_summary,
		"old_grand_total": old_grand_total,
		"new_grand_total": new_grand_total,
		"price_difference": price_difference,
		"already_paid": already_paid,
		"old_balance": old_balance,
		"new_balance": new_balance,
		"items": items_after,
		"revisions": _get_order_revisions(sales_order_name)
	}


@frappe.whitelist()
def search_items(query=None, warehouse=None, pos_profile=None, company=None, limit=25):
	"""
	Search items by name, code, barcode, or description.
	Returns item_code, item_name, rate, stock_uom, actual_qty, image, barcode.
	"""
	if not query or not query.strip():
		return []

	q = query.strip()
	q_like = f"%{q}%"
	limit = cint(limit) or 25

	# Get price list from pos_profile if available
	price_list = None
	if pos_profile:
		price_list = frappe.db.get_value("POS Profile", pos_profile, "selling_price_list")
	if not price_list:
		price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list") or "Standard Selling"

	# Find items matching code, name, description or barcode in tabItem Barcode
	items = frappe.db.sql("""
		SELECT DISTINCT
			i.name as item_code,
			i.item_name,
			i.stock_uom,
			i.image,
			i.description,
			i.standard_rate,
			b.barcode
		FROM `tabItem` i
		LEFT JOIN `tabItem Barcode` b ON b.parent = i.name
		WHERE i.disabled = 0
		  AND (i.is_sales_item = 1 OR i.is_stock_item = 1)
		  AND (
			i.name LIKE %(q_like)s
			OR i.item_name LIKE %(q_like)s
			OR i.description LIKE %(q_like)s
			OR b.barcode = %(q)s
			OR b.barcode LIKE %(q_like)s
		  )
		ORDER BY 
			CASE 
				WHEN b.barcode = %(q)s THEN 1
				WHEN i.name = %(q)s THEN 2
				WHEN i.item_name = %(q)s THEN 3
				WHEN i.name LIKE %(q_prefix)s THEN 4
				WHEN i.item_name LIKE %(q_prefix)s THEN 5
				ELSE 6
			END,
			i.item_name ASC
		LIMIT %(limit)s
	""", {
		"q": q,
		"q_like": q_like,
		"q_prefix": f"{q}%",
		"limit": limit
	}, as_dict=True)

	if not items:
		return []

	item_codes = list(set([it.item_code for it in items]))

	# Fetch rates from Item Price
	rates_map = {}
	if price_list and item_codes:
		prices = frappe.db.sql("""
			SELECT item_code, price_list_rate
			FROM `tabItem Price`
			WHERE price_list = %s AND item_code IN %s AND selling = 1
		""", (price_list, tuple(item_codes)), as_dict=True)
		for p in prices:
			rates_map[p.item_code] = flt(p.price_list_rate)

	# Fetch actual stock from Bin
	stock_map = {}
	if warehouse and item_codes:
		bins = frappe.db.sql("""
			SELECT item_code, SUM(actual_qty) as actual_qty
			FROM `tabBin`
			WHERE warehouse = %s AND item_code IN %s
			GROUP BY item_code
		""", (warehouse, tuple(item_codes)), as_dict=True)
		for b in bins:
			stock_map[b.item_code] = flt(b.actual_qty)

	# Deduplicate items by item_code (in case multiple barcodes joined)
	seen_codes = set()
	results = []
	for it in items:
		if it.item_code in seen_codes:
			continue
		seen_codes.add(it.item_code)

		rate = rates_map.get(it.item_code)
		if rate is None or rate == 0:
			rate = flt(it.standard_rate) or 0.0

		actual_qty = stock_map.get(it.item_code, 0.0)

		results.append({
			"item_code": it.item_code,
			"item_name": it.item_name or it.item_code,
			"rate": rate,
			"stock_uom": it.stock_uom or "Nos",
			"image": it.image or "",
			"barcode": it.barcode or "",
			"actual_qty": actual_qty,
			"description": (it.description or "")[:120]
		})

	return results


@frappe.whitelist()
def get_unallocated_customer_advances(customer=None, company=None):
	"""
	Retrieve advance payments made by customer(s) that are not attached to any Sales Order or Sales Invoice.
	"""
	conditions = [
		"pe.docstatus = 1",
		"pe.party_type = 'Customer'",
		"pe.payment_type = 'Receive'",
		"pe.unallocated_amount > 0.01"
	]
	values = {}
	if customer:
		conditions.append("pe.party = %(customer)s")
		values["customer"] = customer
	if company:
		conditions.append("pe.company = %(company)s")
		values["company"] = company

	where_clause = " AND ".join(conditions)
	advances = frappe.db.sql(f"""
		SELECT 
			pe.name as payment_entry,
			pe.party as customer,
			c.customer_name,
			c.mobile_no as customer_phone,
			pe.posting_date,
			pe.mode_of_payment,
			pe.paid_amount,
			pe.unallocated_amount as available_advance,
			pe.remarks,
			pe.pos_opening_shift,
			pe.owner as cashier
		FROM `tabPayment Entry` pe
		LEFT JOIN `tabCustomer` c ON c.name = pe.party
		WHERE {where_clause}
		ORDER BY pe.posting_date DESC, pe.creation DESC
		LIMIT 100
	""", values, as_dict=1)

	return advances
