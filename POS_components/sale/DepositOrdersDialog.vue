<template>
  <Teleport to="body">
    <div
      v-if="show"
      class="fixed inset-0 bg-slate-950/70 backdrop-blur-sm z-[99990] flex items-center justify-center p-3 sm:p-4 animate-in fade-in duration-200"
      @keydown.esc="closeModal"
    >
      <div class="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl max-w-4xl w-full overflow-hidden border border-slate-200 dark:border-slate-800 flex flex-col max-h-[92vh]">
        
        <!-- Modal Header -->
        <div class="bg-gradient-to-r from-emerald-600 via-teal-600 to-emerald-700 px-5 py-4 text-white flex justify-between items-center shadow-md">
          <div class="flex items-center space-x-3">
            <div class="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center text-white shadow-inner">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
            <div>
              <div class="flex items-center gap-2">
                <h3 class="font-bold text-lg text-white leading-tight">Layaway / Deposit Orders</h3>
                <span v-if="posProfile" class="text-[10px] bg-white/20 text-white px-2 py-0.5 rounded-full font-semibold">
                  {{ posProfile }}
                </span>
              </div>
              <p class="text-xs text-emerald-100">Search orders, view payment history, collect installments, and auto-checkout at zero balance</p>
            </div>
          </div>
          <button
            @click="closeModal"
            class="text-white/80 hover:text-white p-1.5 rounded-lg hover:bg-white/10 transition-colors cursor-pointer text-xl leading-none font-bold"
          >
            ✕
          </button>
        </div>

        <!-- Search & Filter Bar -->
        <div class="p-4 bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-700 space-y-3">
          <div class="relative">
            <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <input
              v-model="search"
              ref="searchInputRef"
              type="text"
              placeholder="Search by Order # (SAL-ORD-...), Customer Name, Mobile Number, or Barcode..."
              class="w-full pl-10 pr-10 py-3 rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-white font-medium text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none shadow-sm"
              @input="fetchOrders"
            />
            <button
              v-if="search"
              @click="search = ''; fetchOrders()"
              class="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-600 cursor-pointer"
            >
              ✕
            </button>
          </div>

          <!-- Status Filter Pills -->
          <div class="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
            <button
              v-for="tab in filterTabs"
              :key="tab.id"
              @click="activeStatusFilter = tab.id"
              :class="[
                'px-3 py-1.5 rounded-lg font-bold transition-all cursor-pointer whitespace-nowrap flex items-center gap-1.5',
                activeStatusFilter === tab.id
                  ? (tab.id === 'overdue' ? 'bg-rose-600 text-white shadow-sm' : 'bg-emerald-600 text-white shadow-sm')
                  : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700'
              ]"
            >
              <span>{{ tab.label }}</span>
              <span
                v-if="tab.count !== undefined"
                class="px-1.5 py-0.2 rounded-full text-[10px]"
                :class="activeStatusFilter === tab.id ? 'bg-white/25 text-white' : (tab.id === 'overdue' && tab.count > 0 ? 'bg-rose-100 text-rose-700 font-black' : 'bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300')"
              >
                {{ tab.count }}
              </span>
            </button>
          </div>
        </div>

        <!-- Orders List Body -->
        <div class="p-4 overflow-y-auto flex-1 space-y-3.5 bg-slate-100/60 dark:bg-slate-950/40">
          
          <div v-if="loading" class="py-12 text-center text-slate-500 font-semibold space-y-2">
            <div class="animate-spin w-8 h-8 border-3 border-emerald-600 border-t-transparent rounded-full mx-auto"></div>
            <p class="text-sm">Loading Layaway Orders...</p>
          </div>

          <div v-else-if="displayedOrders.length === 0" class="py-12 text-center text-slate-500 font-semibold bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-8 space-y-2 shadow-sm">
            <svg class="w-12 h-12 text-slate-300 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p class="text-slate-800 dark:text-slate-200 font-bold text-base">No Layaway Orders Found</p>
            <p class="text-xs text-slate-500">Try searching for a different order number, customer name, or phone.</p>
          </div>

          <!-- Order Cards -->
          <div
            v-for="order in displayedOrders"
            :key="order.sales_order"
            class="bg-white dark:bg-slate-900 rounded-2xl border p-4 shadow-sm hover:shadow-md transition-all space-y-3"
            :class="order.is_overdue ? 'border-rose-300 dark:border-rose-800 ring-1 ring-rose-200 dark:ring-rose-900/50' : 'border-slate-200/90 dark:border-slate-800'"
          >
            <!-- Card Header: Order ID + Status Badge + Overdue Indicator -->
            <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 dark:border-slate-800 pb-2.5">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="font-mono font-black text-base text-slate-900 dark:text-white">{{ order.sales_order }}</span>
                
                <!-- Status Badge -->
                <span
                  :class="[
                    'text-[10px] font-extrabold px-2 py-0.5 rounded-full uppercase tracking-wider',
                    order.status === 'Completed'
                      ? 'bg-blue-100 dark:bg-blue-950/60 text-blue-800 dark:text-blue-300 border border-blue-300'
                      : order.status === 'Fully Paid'
                        ? 'bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300'
                        : order.status === 'Overdue'
                          ? 'bg-rose-100 dark:bg-rose-950/60 text-rose-800 dark:text-rose-300 border border-rose-300 animate-pulse'
                          : order.status === 'Partially Paid'
                            ? 'bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-300'
                            : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-300'
                  ]"
                >
                  {{ order.status }}
                </span>

                <!-- Overdue Warning Badge -->
                <span
                  v-if="order.is_overdue"
                  class="text-[10px] font-black px-2 py-0.5 rounded-full bg-rose-600 text-white flex items-center gap-1 shadow-sm"
                >
                  <span>⚠️ OVERDUE</span>
                  <span>({{ order.days_overdue }} days past promised date)</span>
                </span>
              </div>

              <div class="text-xs text-slate-500 flex items-center gap-2">
                <span>Date: <strong>{{ order.transaction_date || order.creation?.split(' ')[0] }}</strong></span>
                <span v-if="order.delivery_date" :class="order.is_overdue ? 'text-rose-600 font-bold' : 'text-slate-400'">
                  • Promised: <strong>{{ order.delivery_date }}</strong>
                </span>
              </div>
            </div>

            <!-- Customer & Summary Row -->
            <div class="flex flex-wrap items-center justify-between text-xs gap-2">
              <div>
                <span class="text-slate-500 font-medium">Customer: </span>
                <strong class="text-slate-800 dark:text-slate-200 text-sm">{{ order.customer_name || order.customer }}</strong>
                <span v-if="order.customer_phone" class="ml-2 font-mono text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded">
                  📞 {{ order.customer_phone }}
                </span>
              </div>

              <div v-if="order.items_summary" class="text-slate-500 truncate max-w-xs text-[11px]" :title="order.items_summary">
                📦 {{ order.items_summary }}
              </div>
            </div>

            <!-- Financial Breakdown Grid -->
            <div class="grid grid-cols-3 gap-2.5 p-3 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-100 dark:border-slate-800">
              <div>
                <span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Total Order</span>
                <span class="font-mono font-bold text-sm text-slate-900 dark:text-white">
                  KES {{ Number(order.grand_total || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
                </span>
              </div>

              <div>
                <span class="text-[10px] font-bold text-emerald-600 uppercase tracking-wider block">Paid So Far</span>
                <span class="font-mono font-bold text-sm text-emerald-700 dark:text-emerald-400">
                  KES {{ Number(order.deposit_amount || order.paid_amount || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
                </span>
              </div>

              <div>
                <span class="text-[10px] font-bold uppercase tracking-wider block" :class="order.is_overdue ? 'text-rose-600' : 'text-amber-600'">
                  Remaining Balance
                </span>
                <span class="font-mono font-black text-base" :class="order.balance_due > 0 ? (order.is_overdue ? 'text-rose-700 dark:text-rose-400' : 'text-amber-700 dark:text-amber-400') : 'text-emerald-600'">
                  KES {{ Number(order.balance_due || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
                </span>
              </div>
            </div>

            <!-- Expandable Items / Payment History Toggle & Actions -->
            <div class="flex flex-wrap items-center justify-between pt-1 gap-2">
              <div class="flex items-center gap-2">
                <button
                  v-if="order.items && order.items.length > 0"
                  @click="toggleExpand(order.sales_order, 'items')"
                  type="button"
                  class="text-[11px] font-bold text-blue-600 hover:text-blue-800 cursor-pointer flex items-center gap-1"
                >
                  <span>{{ expandedSection[order.sales_order] === 'items' ? '▲ Hide Items' : `▼ Items (${order.items.length})` }}</span>
                </button>

                <button
                  v-if="order.payment_history && order.payment_history.length > 0"
                  @click="toggleExpand(order.sales_order, 'history')"
                  type="button"
                  class="text-[11px] font-bold text-indigo-600 hover:text-indigo-800 cursor-pointer flex items-center gap-1 ml-2"
                >
                  <span>{{ expandedSection[order.sales_order] === 'history' ? '▲ Hide History' : `▼ Payments (${order.payment_history.length})` }}</span>
                </button>

                <button
                  v-if="order.revisions && order.revisions.length > 0"
                  @click="toggleExpand(order.sales_order, 'revisions')"
                  type="button"
                  class="text-[11px] font-bold text-amber-600 hover:text-amber-800 cursor-pointer flex items-center gap-1 ml-2"
                >
                  <span>{{ expandedSection[order.sales_order] === 'revisions' ? '▲ Hide Changes' : `📝 Changes (${order.revisions.length})` }}</span>
                </button>
              </div>

              <div class="flex items-center gap-2">
                <!-- Print Layaway Voucher / Receipt -->
                <button
                  @click="printReceipt(order)"
                  type="button"
                  class="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-slate-300 font-bold rounded-xl text-xs transition-all flex items-center gap-1.5 cursor-pointer shadow-sm active:scale-95"
                  title="Print Layaway Deposit Receipt"
                >
                  <svg class="w-4 h-4 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
                  </svg>
                  <span>Print Voucher</span>
                </button>

                <!-- Swap / Modify Items Action (Change of Mind) -->
                <button
                  v-if="order.balance_due > 0.01"
                  @click="openModifyModal(order)"
                  type="button"
                  class="px-3 py-2 bg-amber-50 hover:bg-amber-100 text-amber-900 dark:bg-amber-950/50 dark:hover:bg-amber-900/60 dark:text-amber-200 font-bold rounded-xl text-xs transition-all flex items-center gap-1.5 cursor-pointer border border-amber-300 dark:border-amber-700 shadow-xs active:scale-95"
                  title="Customer change of mind - swap or modify items in this order"
                >
                  <svg class="w-4 h-4 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                  <span>Swap / Edit Items</span>
                </button>

                <!-- Pay Balance Action -->
                <button
                  v-if="order.balance_due > 0.01"
                  @click="openPayModal(order)"
                  class="text-white font-black px-4 py-2 rounded-xl text-xs transition-all shadow-md hover:brightness-110 active:scale-95 flex items-center gap-1.5 cursor-pointer"
                  style="background-color: #16a34a !important;"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                  <span>Pay Balance / Installment</span>
                </button>

                <span v-else class="text-xs font-bold text-emerald-600 flex items-center gap-1 bg-emerald-50 dark:bg-emerald-950/40 px-3 py-1.5 rounded-xl border border-emerald-200">
                  ✓ Balance Cleared
                </span>
              </div>
            </div>

            <!-- Expanded Items Details -->
            <div
              v-if="expandedSection[order.sales_order] === 'items'"
              class="p-3 bg-slate-50 dark:bg-slate-800/80 rounded-xl border border-slate-200 dark:border-slate-700 text-xs animate-in fade-in duration-150 space-y-1.5"
            >
              <div class="font-bold text-slate-700 dark:text-slate-300 mb-1">Products in Sales Order:</div>
              <div
                v-for="itm in order.items"
                :key="itm.item_code"
                class="flex justify-between py-1 border-b border-slate-200/60 dark:border-slate-700/60 last:border-0"
              >
                <span class="font-medium text-slate-800 dark:text-slate-200">
                  {{ itm.item_name || itm.item_code }} <span class="text-slate-500 font-mono">x{{ itm.qty }}</span>
                </span>
                <span class="font-mono text-slate-700 dark:text-slate-300">
                  @ KES {{ Number(itm.rate).toLocaleString() }} = <strong>KES {{ Number(itm.amount).toLocaleString() }}</strong>
                </span>
              </div>
            </div>

            <!-- Expanded Payment History Details -->
            <div
              v-if="expandedSection[order.sales_order] === 'history'"
              class="p-3 bg-indigo-50/60 dark:bg-indigo-950/40 rounded-xl border border-indigo-200 dark:border-indigo-800 text-xs animate-in fade-in duration-150 space-y-1.5"
            >
              <div class="font-bold text-indigo-900 dark:text-indigo-200 mb-1">Payment History:</div>
              <div
                v-for="(p, idx) in order.payment_history"
                :key="p.payment_entry || idx"
                class="flex flex-wrap justify-between items-center py-1.5 border-b border-indigo-100 dark:border-indigo-900/60 last:border-0 text-[11px] gap-2"
              >
                <div>
                  <span class="font-semibold text-indigo-950 dark:text-indigo-200">{{ p.mode_of_payment }}</span>
                  <span class="text-slate-500 font-mono ml-2">{{ p.posting_date || p.creation?.split(' ')[0] }}</span>
                  <span v-if="p.cashier" class="text-slate-400 ml-1">by {{ p.cashier }}</span>
                </div>
                <div class="font-mono font-bold text-emerald-700 dark:text-emerald-400 text-xs">
                  KES {{ Number(p.allocated_amount).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
                </div>
              </div>
            </div>

            <!-- Expanded Revisions / Item & Price Change History -->
            <div
              v-if="expandedSection[order.sales_order] === 'revisions' && order.revisions && order.revisions.length > 0"
              class="p-3 bg-amber-50/70 dark:bg-amber-950/40 rounded-xl border border-amber-200 dark:border-amber-800 text-xs animate-in fade-in duration-150 space-y-2"
            >
              <div class="font-bold text-amber-950 dark:text-amber-200 mb-1 flex items-center justify-between">
                <span class="flex items-center gap-1.5">
                  <svg class="w-3.5 h-3.5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Item Swaps & Price Revision History:
                </span>
                <span class="text-[10px] bg-amber-200 dark:bg-amber-900 text-amber-900 dark:text-amber-200 px-1.5 py-0.5 rounded-full font-bold">{{ order.revisions.length }} revision(s)</span>
              </div>
              <div
                v-for="rev in order.revisions"
                :key="rev.name || rev.revision_no"
                class="p-2.5 bg-white dark:bg-slate-900 rounded-lg border border-amber-200/90 dark:border-amber-800/80 space-y-1.5 text-[11px]"
              >
                <div class="flex items-center justify-between text-xs font-bold text-slate-800 dark:text-slate-200">
                  <span class="text-amber-700 dark:text-amber-400 font-extrabold">Revision #{{ rev.revision_no }}</span>
                  <span class="text-slate-400 text-[10px]">{{ rev.posting_date }} {{ rev.posting_time }} <span v-if="rev.cashier">• by {{ rev.cashier }}</span></span>
                </div>
                <div class="text-slate-700 dark:text-slate-300 font-medium">
                  <span class="text-slate-500">Reason:</span> {{ rev.reason }}
                </div>
                <div class="text-indigo-700 dark:text-indigo-300 bg-indigo-50/80 dark:bg-indigo-950/50 p-2 rounded-md font-mono text-[10.5px]">
                  {{ rev.changes_summary }}
                </div>
                <div class="flex flex-wrap justify-between items-center pt-1 border-t border-slate-100 dark:border-slate-800 text-[10.5px] gap-2">
                  <span>Order Total: <strong class="line-through text-slate-400">KES {{ Number(rev.old_grand_total).toLocaleString() }}</strong> ➔ <strong class="text-slate-900 dark:text-white">KES {{ Number(rev.new_grand_total).toLocaleString() }}</strong> (<span :class="rev.price_difference >= 0 ? 'text-amber-600 font-bold' : 'text-emerald-600 font-bold'">{{ rev.price_difference >= 0 ? '+' : '' }}KES {{ Number(rev.price_difference).toLocaleString() }}</span>)</span>
                  <span>New Balance Due: <strong class="text-amber-700 dark:text-amber-400 font-bold">KES {{ Number(rev.new_balance).toLocaleString() }}</strong></span>
                </div>
              </div>
            </div>

          </div>
        </div>

        <!-- Modal Footer -->
        <div class="p-3.5 bg-slate-50 dark:bg-slate-800/80 border-t border-slate-200 dark:border-slate-700 flex justify-between items-center text-xs">
          <span class="text-slate-500 font-medium">Showing {{ displayedOrders.length }} orders</span>
          <button
            @click="closeModal"
            class="px-5 py-2.5 bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 dark:hover:bg-slate-600 text-slate-800 dark:text-white font-bold rounded-xl transition-all cursor-pointer"
          >
            Close
          </button>
        </div>

      </div>

      <!-- Nested Subsequent Payment Modal -->
      <Teleport to="body">
        <div
          v-if="selectedOrder"
          class="fixed inset-0 bg-slate-950/80 backdrop-blur-md z-[99995] flex items-center justify-center p-3 sm:p-4 animate-in fade-in duration-150"
        >
          <div class="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl max-w-md w-full overflow-hidden border border-slate-200 dark:border-slate-800 space-y-4 p-5">
            
            <div class="flex justify-between items-center border-b border-slate-100 dark:border-slate-800 pb-3">
              <div>
                <h4 class="font-black text-base text-slate-900 dark:text-white">Record Layaway Installment</h4>
                <p class="text-xs text-slate-500 font-mono">{{ selectedOrder.sales_order }}</p>
              </div>
              <button
                @click="selectedOrder = null; payError = ''"
                class="text-slate-400 hover:text-slate-600 text-lg font-bold p-1 cursor-pointer"
              >
                ✕
              </button>
            </div>

            <!-- Customer & Financial Summary -->
            <div class="bg-emerald-50 dark:bg-emerald-950/40 p-3.5 rounded-xl border border-emerald-200 dark:border-emerald-800 space-y-2 text-xs">
              <div class="flex justify-between">
                <span class="text-slate-600 dark:text-slate-400 font-medium">Customer:</span>
                <strong class="text-slate-900 dark:text-white">{{ selectedOrder.customer_name || selectedOrder.customer }}</strong>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-600 dark:text-slate-400 font-medium">Total Order:</span>
                <strong class="font-mono">KES {{ Number(selectedOrder.grand_total).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</strong>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-600 dark:text-slate-400 font-medium">Paid So Far:</span>
                <strong class="font-mono text-emerald-700">KES {{ Number(selectedOrder.paid_amount || selectedOrder.deposit_amount || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</strong>
              </div>
              <div class="flex justify-between pt-1 border-t border-emerald-200 dark:border-emerald-800/80 font-bold text-sm">
                <span class="text-amber-800 dark:text-amber-300">Remaining Balance:</span>
                <span class="font-mono text-amber-800 dark:text-amber-300 font-black">
                  KES {{ Number(selectedOrder.balance_due).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
                </span>
              </div>
            </div>

            <!-- Payment Input -->
            <div class="space-y-3">
              <div>
                <label class="block font-bold text-slate-700 dark:text-slate-300 text-xs mb-1">
                  Payment Amount (KES)
                </label>
                <div class="relative">
                  <input
                    v-model.number="payAmount"
                    type="number"
                    step="any"
                    min="1"
                    :max="selectedOrder.balance_due"
                    class="w-full p-3 rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-white font-black text-xl text-right focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>
                <div class="flex justify-between items-center mt-1 text-[11px]">
                  <span class="text-slate-500">
                    New Balance: <strong class="text-amber-600 font-mono">KES {{ Math.max(0, (selectedOrder.balance_due - (payAmount || 0))).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</strong>
                  </span>
                  <button
                    @click="payAmount = selectedOrder.balance_due"
                    type="button"
                    class="text-emerald-600 font-bold hover:underline cursor-pointer"
                  >
                    Pay Full Balance
                  </button>
                </div>
              </div>

              <!-- Payment Mode Selector -->
              <div>
                <label class="block font-bold text-slate-700 dark:text-slate-300 text-xs mb-1.5">
                  Payment Mode
                </label>
                <div class="grid grid-cols-4 gap-2">
                  <button
                    v-for="mode in ['Cash', 'M-Pesa', 'Credit Card', 'Bank']"
                    :key="mode"
                    @click="payMode = mode"
                    type="button"
                    :class="[
                      'py-2 px-2 rounded-xl font-bold text-xs border transition-all cursor-pointer text-center',
                      payMode === mode
                        ? 'border-emerald-600 bg-emerald-50 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 shadow-sm'
                        : 'border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300'
                    ]"
                  >
                    {{ mode }}
                  </button>
                </div>
              </div>

              <!-- M-Pesa STK Push Assistant -->
              <div v-if="payMode === 'M-Pesa'" class="space-y-2 p-3 bg-emerald-50 dark:bg-emerald-950/40 rounded-xl border border-emerald-200 dark:border-emerald-800">
                <label class="block font-bold text-emerald-900 dark:text-emerald-200 text-[11px]">
                  Customer Phone for M-Pesa STK Prompt
                </label>
                <div class="flex gap-2">
                  <input
                    v-model="mpesaPhone"
                    type="text"
                    placeholder="e.g. 0769814650"
                    class="flex-1 p-2 rounded-lg border border-emerald-300 dark:border-emerald-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white font-mono text-xs focus:outline-none"
                  />
                  <button
                    @click="triggerMpesaSTK"
                    :disabled="sendingSTK || !mpesaPhone"
                    type="button"
                    class="px-3 py-2 bg-emerald-600 text-white font-bold rounded-lg hover:bg-emerald-700 disabled:opacity-50 cursor-pointer text-xs"
                  >
                    {{ sendingSTK ? 'Sending...' : 'Prompt PIN' }}
                  </button>
                </div>
                <p v-if="stkMessage" class="text-[11px] font-bold text-emerald-800 dark:text-emerald-300">
                  {{ stkMessage }}
                </p>
              </div>

              <!-- Auto-Conversion Notice if full payment -->
              <div v-if="(selectedOrder.balance_due - (payAmount || 0)) <= 0.01" class="bg-blue-50 border border-blue-200 text-blue-800 rounded-xl p-2.5 text-xs font-semibold flex items-center gap-2">
                <span class="text-base">✨</span>
                <span>This payment clears the balance! System will automatically generate the final Tax Invoice and deduct stock.</span>
              </div>

              <!-- Error Alert -->
              <div v-if="payError" class="bg-rose-50 border border-rose-200 text-rose-700 rounded-xl p-3 text-xs font-semibold">
                {{ payError }}
              </div>

              <!-- Action Buttons -->
              <div class="flex gap-2.5 pt-2">
                <button
                  @click="selectedOrder = null; payError = ''"
                  type="button"
                  class="flex-1 px-4 py-3 rounded-xl border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 font-bold hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  @click="confirmPayBalance"
                  :disabled="paying || !payAmount || payAmount <= 0"
                  type="button"
                  class="flex-1 px-4 py-3 rounded-xl text-white font-black shadow-md transition-all disabled:opacity-50 cursor-pointer text-xs"
                  style="background-color: #16a34a !important;"
                >
                  {{ paying ? 'Recording Payment...' : 'Confirm Payment' }}
                </button>
              </div>

            </div>

          </div>
        </div>
      </Teleport>

      <!-- Nested Modify Layaway Items Modal (Customer Change of Mind) -->
      <Teleport to="body">
        <div
          v-if="modifyOrder"
          class="fixed inset-0 bg-slate-950/80 backdrop-blur-md z-[99995] flex items-center justify-center p-3 sm:p-4 animate-in fade-in duration-150"
        >
          <div class="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] flex flex-col overflow-hidden border border-slate-200 dark:border-slate-800">
            
            <!-- Header -->
            <div class="p-4 border-b border-slate-100 dark:border-slate-800 flex justify-between items-center bg-slate-50/50 dark:bg-slate-800/50">
              <div>
                <div class="flex items-center gap-2">
                  <span class="text-base font-black text-slate-900 dark:text-white">Swap / Modify Order Items</span>
                  <span class="text-[10px] bg-amber-100 dark:bg-amber-950 text-amber-900 dark:text-amber-200 font-extrabold px-2 py-0.5 rounded-full border border-amber-300 dark:border-amber-700">Customer Change of Mind</span>
                </div>
                <p class="text-xs text-slate-500 font-mono mt-0.5">{{ modifyOrder.sales_order }} • {{ modifyOrder.customer_name || modifyOrder.customer }}</p>
              </div>
              <button
                @click="modifyOrder = null; modifyError = ''"
                class="text-slate-400 hover:text-slate-600 text-lg font-bold p-1 cursor-pointer"
              >
                ✕
              </button>
            </div>

            <!-- Body -->
            <div class="p-4 overflow-y-auto space-y-4 flex-1">
              
              <!-- Search & Add Item Section -->
              <div class="space-y-1.5 relative">
                <div class="flex items-center justify-between">
                  <label class="block font-bold text-xs text-slate-700 dark:text-slate-300">
                    Search & Add Product / Substitute Item
                  </label>
                  <span class="text-[10px] text-amber-700 dark:text-amber-400 font-semibold flex items-center gap-1">
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01M5 8h2a1 1 0 001-1V5a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1zm12 0h2a1 1 0 001-1V5a1 1 0 00-1-1h-2a1 1 0 00-1 1v2a1 1 0 001 1zM5 20h2a1 1 0 001-1v-2a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1z" />
                    </svg>
                    <span>Barcode & Search Ideas</span>
                  </span>
                </div>

                <div class="relative">
                  <input
                    ref="modifySearchInputRef"
                    v-model="itemSearchQuery"
                    @input="searchItemsForModify"
                    @keydown.down.prevent="navigateSuggestions(1)"
                    @keydown.up.prevent="navigateSuggestions(-1)"
                    @keydown.enter.prevent="handleSearchEnter"
                    @keydown.esc="itemSearchResults = []"
                    type="text"
                    placeholder="Type product name, code, or scan barcode directly..."
                    class="w-full p-2.5 pl-9 pr-24 rounded-xl border border-amber-300 dark:border-amber-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white text-xs font-medium focus:ring-2 focus:ring-amber-500 focus:outline-none shadow-xs"
                  />
                  <svg class="w-4 h-4 text-amber-600 absolute left-3 top-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>

                  <div class="absolute right-2 top-2 flex items-center gap-1">
                    <span v-if="isSearchingItems" class="text-[10px] text-amber-600 font-bold animate-pulse mr-1">
                      Searching...
                    </span>
                    <kbd class="px-1.5 py-0.5 text-[9px] font-mono font-bold text-slate-400 bg-slate-100 dark:bg-slate-800 rounded border border-slate-200 dark:border-slate-700">Enter / Scan</kbd>
                  </div>
                </div>

                <!-- Dropdown Search Results / Suggestions List -->
                <div
                  v-if="itemSearchResults && itemSearchResults.length > 0"
                  class="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-slate-900 border-2 border-amber-400 dark:border-amber-600 rounded-xl shadow-2xl z-[100] max-h-60 overflow-y-auto divide-y divide-slate-100 dark:divide-slate-800 animate-in fade-in zoom-in-95 duration-100"
                >
                  <div class="p-1.5 bg-amber-50/80 dark:bg-amber-950/60 text-[10.5px] font-bold text-amber-900 dark:text-amber-200 flex justify-between items-center px-3">
                    <span>{{ itemSearchResults.length }} Matching Product Idea(s)</span>
                    <span class="text-[9.5px] text-amber-700 dark:text-amber-300 font-normal">Use ↑ ↓ & Enter to select</span>
                  </div>

                  <div
                    v-for="(itm, sIdx) in itemSearchResults"
                    :key="itm.item_code"
                    @click="addItemToModify(itm)"
                    :class="[
                      'p-2.5 cursor-pointer flex justify-between items-center text-xs transition-colors',
                      selectedSuggestionIndex === sIdx ? 'bg-amber-100 dark:bg-amber-900/60' : 'hover:bg-amber-50/70 dark:hover:bg-amber-950/40'
                    ]"
                  >
                    <div class="flex items-center gap-2.5 min-w-0">
                      <div class="w-8 h-8 rounded-lg bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300 flex items-center justify-center font-bold text-xs flex-shrink-0">
                        📦
                      </div>
                      <div class="min-w-0">
                        <strong class="text-slate-900 dark:text-white block truncate">{{ itm.item_name }}</strong>
                        <div class="flex items-center gap-2 text-[10px] text-slate-500 font-mono">
                          <span>{{ itm.item_code }}</span>
                          <span v-if="itm.barcode" class="text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/60 px-1 rounded border border-amber-200 dark:border-amber-800">
                            ||| {{ itm.barcode }}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div class="text-right flex-shrink-0 ml-3">
                      <div class="font-mono font-black text-xs text-emerald-700 dark:text-emerald-400">
                        KES {{ Number(itm.rate || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
                      </div>
                      <div class="text-[10px] flex items-center justify-end gap-1 font-semibold" :class="itm.actual_qty > 0 ? 'text-emerald-600' : 'text-slate-400'">
                        <span>{{ itm.actual_qty !== undefined ? `${itm.actual_qty} in stock` : '' }}</span>
                        <span class="text-amber-600 font-bold ml-1">+ Add</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div
                  v-else-if="itemSearchQuery && itemSearchQuery.trim().length >= 2 && !isSearchingItems"
                  class="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl shadow-xl z-[100] p-3 text-center text-xs text-slate-500"
                >
                  No products found matching "<strong>{{ itemSearchQuery }}</strong>". Try searching with item name, code or barcode.
                </div>
              </div>

              <!-- Current Items Table -->
              <div class="space-y-2">
                <label class="block font-bold text-xs text-slate-700 dark:text-slate-300">
                  Order Items ({{ editableItems.length }})
                </label>
                <div class="border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden divide-y divide-slate-100 dark:divide-slate-800 text-xs">
                  <div
                    v-for="(itm, idx) in editableItems"
                    :key="itm.item_code || idx"
                    class="p-2.5 bg-slate-50/50 dark:bg-slate-800/40 flex items-center justify-between gap-3"
                  >
                    <div class="flex-1 min-w-0">
                      <strong class="text-slate-900 dark:text-white block truncate">{{ itm.item_name || itm.item_code }}</strong>
                      <span class="text-[10px] text-slate-400 font-mono">{{ itm.item_code }}</span>
                    </div>

                    <!-- Rate Input -->
                    <div class="w-24 text-right">
                      <span class="text-[10px] text-slate-400 block">Unit Price</span>
                      <input
                        v-model.number="itm.rate"
                        type="number"
                        min="0"
                        step="any"
                        class="w-full p-1 border rounded text-right font-mono font-bold text-xs bg-white dark:bg-slate-900"
                      />
                    </div>

                    <!-- Quantity Controls -->
                    <div class="flex items-center gap-1.5">
                      <button
                        @click="itm.qty = Math.max(1, (Number(itm.qty) || 1) - 1)"
                        type="button"
                        class="w-7 h-7 rounded-lg bg-slate-200 dark:bg-slate-700 font-bold flex items-center justify-center hover:bg-slate-300 cursor-pointer"
                      >
                        -
                      </button>
                      <input
                        v-model.number="itm.qty"
                        type="number"
                        min="1"
                        class="w-12 p-1 text-center font-mono font-bold rounded border bg-white dark:bg-slate-900 text-xs"
                      />
                      <button
                        @click="itm.qty = (Number(itm.qty) || 0) + 1"
                        type="button"
                        class="w-7 h-7 rounded-lg bg-slate-200 dark:bg-slate-700 font-bold flex items-center justify-center hover:bg-slate-300 cursor-pointer"
                      >
                        +
                      </button>
                    </div>

                    <!-- Line Total -->
                    <div class="w-24 text-right">
                      <span class="text-[10px] text-slate-400 block">Line Total</span>
                      <strong class="font-mono text-xs text-slate-900 dark:text-white">KES {{ (Number(itm.qty || 1) * Number(itm.rate || 0)).toLocaleString() }}</strong>
                    </div>

                    <!-- Remove Item Button -->
                    <button
                      @click="removeItemFromModify(idx)"
                      :disabled="editableItems.length <= 1"
                      type="button"
                      class="p-1 text-rose-500 hover:text-rose-700 hover:bg-rose-50 rounded-lg disabled:opacity-30 cursor-pointer"
                      title="Remove item"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>

              <!-- Price & Total Comparison Overview Card -->
              <div class="p-3.5 bg-amber-50/80 dark:bg-amber-950/40 rounded-xl border border-amber-200 dark:border-amber-800 space-y-2 text-xs">
                <div class="font-bold text-amber-950 dark:text-amber-200 mb-1">Financial Impact Summary:</div>
                <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
                  <div class="bg-white dark:bg-slate-900 p-2 rounded-lg border border-amber-100 dark:border-amber-900">
                    <span class="text-[10px] text-slate-500 block font-semibold">Previous Total</span>
                    <strong class="font-mono text-slate-700 dark:text-slate-300">KES {{ Number(modifyOrder.grand_total).toLocaleString() }}</strong>
                  </div>
                  <div class="bg-white dark:bg-slate-900 p-2 rounded-lg border border-amber-100 dark:border-amber-900">
                    <span class="text-[10px] text-slate-500 block font-semibold">New Grand Total</span>
                    <strong class="font-mono text-slate-900 dark:text-white text-sm">KES {{ Number(modifyNewGrandTotal).toLocaleString() }}</strong>
                  </div>
                  <div class="bg-white dark:bg-slate-900 p-2 rounded-lg border border-amber-100 dark:border-amber-900">
                    <span class="text-[10px] text-slate-500 block font-semibold">Price Difference</span>
                    <strong class="font-mono text-xs" :class="modifyPriceDiff >= 0 ? 'text-amber-600' : 'text-emerald-600'">
                      {{ modifyPriceDiff >= 0 ? '+' : '' }}KES {{ Number(modifyPriceDiff).toLocaleString() }}
                    </strong>
                  </div>
                  <div class="bg-amber-100 dark:bg-amber-900/60 p-2 rounded-lg border border-amber-300 dark:border-amber-700">
                    <span class="text-[10px] text-amber-950 dark:text-amber-200 block font-bold">New Balance Due</span>
                    <strong class="font-mono text-amber-950 dark:text-amber-100 text-sm font-black">KES {{ Number(modifyNewBalance).toLocaleString() }}</strong>
                  </div>
                </div>
              </div>

              <!-- Reason for change -->
              <div class="space-y-1">
                <label class="block font-bold text-xs text-slate-700 dark:text-slate-300">
                  Reason for Change of Mind / Exchange
                </label>
                <input
                  v-model="modifyReason"
                  type="text"
                  placeholder="e.g. Customer wanted different model / color / size"
                  class="w-full p-2.5 rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-white text-xs focus:ring-2 focus:ring-amber-500 focus:outline-none"
                />
              </div>

              <!-- Error Alert -->
              <div v-if="modifyError" class="bg-rose-50 border border-rose-200 text-rose-700 rounded-xl p-3 text-xs font-semibold">
                {{ modifyError }}
              </div>

            </div>

            <!-- Footer -->
            <div class="p-3.5 bg-slate-50 dark:bg-slate-800/80 border-t border-slate-200 dark:border-slate-700 flex justify-end gap-2.5">
              <button
                @click="modifyOrder = null; modifyError = ''"
                type="button"
                class="px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 font-bold hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer text-xs"
              >
                Cancel
              </button>
              <button
                @click="confirmModifyItems"
                :disabled="isModifying || editableItems.length === 0"
                type="button"
                class="px-5 py-2.5 rounded-xl text-white font-black shadow-md transition-all disabled:opacity-50 cursor-pointer text-xs flex items-center gap-1.5"
                style="background-color: #d97706 !important;"
              >
                <svg v-if="isModifying" class="animate-spin h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>{{ isModifying ? 'Updating Order...' : 'Save & Update Order' }}</span>
              </button>
            </div>

          </div>
        </div>
      </Teleport>

      <!-- Success Notification Toast -->
      <div
        v-if="successMsg"
        class="fixed bottom-6 left-1/2 -translate-x-1/2 bg-emerald-600 text-white px-6 py-3 rounded-2xl shadow-2xl font-bold text-sm z-[99999] transition-all flex items-center gap-2"
      >
        <span>✓</span>
        <span>{{ successMsg }}</span>
      </div>

    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { call } from 'frappe-ui'
import { usePOSShiftStore } from '@/stores/posShift'
import { useItemSearchStore } from '@/stores/itemSearch'

const shiftStore = usePOSShiftStore()
const itemSearchStore = useItemSearchStore()

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  posProfile: String,
  company: String,
})

const emit = defineEmits(['close', 'paid', 'load-order-to-pos', 'pay-layaway-order'])

const search = ref('')
const loading = ref(false)
const orders = ref([])
const activeStatusFilter = ref('pending') // 'pending' | 'overdue' | 'all' | 'paid'
const selectedOrder = ref(null)
const payAmount = ref(0)
const payMode = ref('Cash')
const mpesaPhone = ref('')
const sendingSTK = ref(false)
const stkMessage = ref('')
const paying = ref(false)
const payError = ref('')
const successMsg = ref('')
const expandedSection = ref({})
const searchInputRef = ref(null)

// Modify Layaway Items (Change of Mind) State
const modifyOrder = ref(null)
const editableItems = ref([])
const modifyReason = ref('Customer change of mind')
const itemSearchQuery = ref('')
const itemSearchResults = ref([])
const isSearchingItems = ref(false)
const selectedSuggestionIndex = ref(-1)
const modifySearchInputRef = ref(null)
const isModifying = ref(false)
const modifyError = ref('')

const modifyNewGrandTotal = computed(() => {
  return (editableItems.value || []).reduce((acc, i) => acc + (Number(i.qty || 1) * Number(i.rate || 0)), 0)
})

const modifyPriceDiff = computed(() => {
  return modifyNewGrandTotal.value - Number(modifyOrder.value?.grand_total || 0)
})

const modifyNewBalance = computed(() => {
  const paid = Number(modifyOrder.value?.paid_amount || modifyOrder.value?.deposit_amount || 0)
  return Math.max(0, modifyNewGrandTotal.value - paid)
})

const filterTabs = computed(() => {
  const pendingCount = orders.value.filter(o => o.balance_due > 0.01).length
  const overdueCount = orders.value.filter(o => o.is_overdue).length
  const paidCount = orders.value.filter(o => o.balance_due <= 0.01).length
  return [
    { id: 'pending', label: 'Pending Balance', count: pendingCount },
    { id: 'overdue', label: '⚠️ Overdue', count: overdueCount },
    { id: 'all', label: 'All Orders', count: orders.value.length },
    { id: 'paid', label: 'Fully Paid / Completed', count: paidCount },
  ]
})

const displayedOrders = computed(() => {
  let list = orders.value
  if (activeStatusFilter.value === 'pending') {
    list = list.filter(o => o.balance_due > 0.01)
  } else if (activeStatusFilter.value === 'overdue') {
    list = list.filter(o => o.is_overdue)
  } else if (activeStatusFilter.value === 'paid') {
    list = list.filter(o => o.balance_due <= 0.01)
  }
  return list
})

watch(() => props.show, (newVal) => {
  if (newVal) {
    search.value = ''
    selectedOrder.value = null
    payError.value = ''
    fetchOrders()
    nextTick(() => {
      if (searchInputRef.value) searchInputRef.value.focus()
    })
  }
})

async function apiCall(method, args) {
  if (typeof call === 'function') {
    try {
      return await call(method, args)
    } catch (e) {
      console.warn('frappe-ui call fallback', e)
    }
  }
  const csrf = window.frappe?.csrf_token || document.cookie.match(/X-Frappe-CSRF-Token=([^;]+)/)?.[1] || ''
  const query = new URLSearchParams(args || {}).toString()
  const response = await fetch('/api/method/' + method + (query ? '?' + query : ''), {
    method: 'GET',
    headers: {
      'X-Frappe-CSRF-Token': csrf,
      'X-Requested-With': 'XMLHttpRequest'
    }
  })
  const data = await response.json()
  if (data.exc) throw new Error(data.exc)
  return data.message
}

const fetchOrders = async () => {
  loading.value = true
  try {
    const data = await apiCall('pos_next_patch.api.deposit.get_deposit_orders', {
      search_term: search.value || '',
      company: props.company || shiftStore.profileCompany || '',
      pos_profile: props.posProfile || shiftStore.profileName || '',
    })
    if (data && Array.isArray(data)) {
      orders.value = data
    }
  } catch (e) {
    console.error('Failed to load layaway orders:', e)
  } finally {
    loading.value = false
  }
}

function toggleExpand(orderId, section) {
  if (expandedSection.value[orderId] === section) {
    delete expandedSection.value[orderId]
  } else {
    expandedSection.value[orderId] = section
  }
}

function openPayModal(order) {
  emit('pay-layaway-order', order)
  emit('close')
}

function openModifyModal(order) {
  modifyOrder.value = order
  editableItems.value = (order.items || []).map(i => ({
    item_code: i.item_code,
    item_name: i.item_name || i.item_code,
    qty: Number(i.qty) || 1,
    rate: Number(i.rate) || 0,
    uom: i.uom || i.stock_uom || 'Nos',
    warehouse: i.warehouse || shiftStore.profileWarehouse || ''
  }))
  modifyReason.value = 'Customer change of mind'
  modifyError.value = ''
  itemSearchQuery.value = ''
  itemSearchResults.value = []
  selectedSuggestionIndex.value = -1
  nextTick(() => {
    modifySearchInputRef.value?.focus()
  })
}

let searchDebounceTimer = null
function searchItemsForModify() {
  const q = (itemSearchQuery.value || '').trim()
  if (!q) {
    itemSearchResults.value = []
    selectedSuggestionIndex.value = -1
    isSearchingItems.value = false
    return
  }

  selectedSuggestionIndex.value = -1

  // 1. Instant in-memory search from cached items
  const localMatches = (itemSearchStore?.allItems || [])
    .filter(it => {
      const nameMatch = (it.item_name || '').toLowerCase().includes(q.toLowerCase())
      const codeMatch = (it.item_code || '').toLowerCase().includes(q.toLowerCase())
      const barcodeMatch = (it.barcodes || []).some(b => String(b).toLowerCase().includes(q.toLowerCase()))
      return nameMatch || codeMatch || barcodeMatch
    })
    .slice(0, 15)
    .map(it => ({
      item_code: it.item_code,
      item_name: it.item_name || it.item_code,
      rate: Number(it.rate || it.price_list_rate || 0),
      stock_uom: it.stock_uom || 'Nos',
      barcode: it.barcode || (it.barcodes && it.barcodes[0]) || '',
      actual_qty: it.actual_qty ?? it.stock_qty ?? 0
    }))

  if (localMatches.length > 0) {
    itemSearchResults.value = localMatches
  }

  // 2. Concurrently fetch real-time DB items & barcodes
  clearTimeout(searchDebounceTimer)
  isSearchingItems.value = true
  searchDebounceTimer = setTimeout(async () => {
    try {
      const res = await apiCall('pos_next_patch.api.deposit.search_items', {
        query: q,
        warehouse: shiftStore.profileWarehouse || '',
        pos_profile: props.posProfile || shiftStore.profileName || '',
        company: props.company || shiftStore.profileCompany || ''
      })
      if (res && Array.isArray(res)) {
        const map = new Map()
        for (const item of res) map.set(item.item_code, item)
        for (const item of (itemSearchResults.value || [])) {
          if (!map.has(item.item_code)) map.set(item.item_code, item)
        }
        itemSearchResults.value = Array.from(map.values())
      }
    } catch (e) {
      console.error('Failed searching items:', e)
    } finally {
      isSearchingItems.value = false
    }
  }, 120)
}

function navigateSuggestions(step) {
  if (!itemSearchResults.value || itemSearchResults.value.length === 0) return
  const max = itemSearchResults.value.length
  selectedSuggestionIndex.value = (selectedSuggestionIndex.value + step + max) % max
}

async function handleSearchEnter() {
  const q = (itemSearchQuery.value || '').trim()
  if (!q) return

  if (selectedSuggestionIndex.value >= 0 && itemSearchResults.value[selectedSuggestionIndex.value]) {
    addItemToModify(itemSearchResults.value[selectedSuggestionIndex.value])
    return
  }

  if (itemSearchResults.value && itemSearchResults.value.length === 1) {
    addItemToModify(itemSearchResults.value[0])
    return
  }

  // If scanning barcode or direct lookup
  isSearchingItems.value = true
  try {
    const res = await apiCall('pos_next_patch.api.deposit.search_items', {
      query: q,
      warehouse: shiftStore.profileWarehouse || '',
      pos_profile: props.posProfile || shiftStore.profileName || '',
      company: props.company || shiftStore.profileCompany || '',
      limit: 10
    })
    if (res && res.length > 0) {
      const exact = res.find(r => r.barcode === q || r.item_code === q) || res[0]
      addItemToModify(exact)
    }
  } catch (e) {
    console.error('Scanner/Enter item lookup error:', e)
  } finally {
    isSearchingItems.value = false
  }
}

function addItemToModify(itm) {
  const existing = editableItems.value.find(i => i.item_code === itm.item_code)
  if (existing) {
    existing.qty = (Number(existing.qty) || 0) + 1
  } else {
    editableItems.value.push({
      item_code: itm.item_code,
      item_name: itm.item_name || itm.item_code,
      qty: 1,
      rate: Number(itm.rate) || 0,
      uom: itm.stock_uom || 'Nos',
      warehouse: shiftStore.profileWarehouse || ''
    })
  }
  itemSearchQuery.value = ''
  itemSearchResults.value = []
  selectedSuggestionIndex.value = -1
  nextTick(() => {
    modifySearchInputRef.value?.focus()
  })
}

function removeItemFromModify(idx) {
  if (editableItems.value.length > 1) {
    editableItems.value.splice(idx, 1)
  }
}

async function confirmModifyItems() {
  if (!modifyOrder.value || editableItems.value.length === 0) return
  isModifying.value = true
  modifyError.value = ''
  try {
    const res = await apiCall('pos_next_patch.api.deposit.modify_layaway_items', {
      sales_order_name: modifyOrder.value.sales_order,
      new_items: JSON.stringify(editableItems.value),
      reason: modifyReason.value || 'Customer change of mind',
      cashier: shiftStore.userName || '',
      pos_profile: props.posProfile || shiftStore.profileName || ''
    })

    const soName = modifyOrder.value.sales_order
    modifyOrder.value = null
    successMsg.value = `✓ Layaway Order ${soName} updated successfully! New total: KES ${Number(res?.new_grand_total || 0).toLocaleString()}`
    setTimeout(() => { successMsg.value = '' }, 6000)
    await fetchOrders()
  } catch (err) {
    modifyError.value = String(err?.message || err).replace(/&lt;/g, '<').replace(/&gt;/g, '>').substring(0, 300)
  } finally {
    isModifying.value = false
  }
}

async function triggerMpesaSTK() {
  if (!mpesaPhone.value || !payAmount.value || sendingSTK.value) return
  sendingSTK.value = true
  stkMessage.value = 'Initiating M-Pesa STK Prompt...'

  try {
    const res = await apiCall('pos_next_patch.api.mpesa_bridge.trigger_stk_push', {
      phone_number: mpesaPhone.value,
      amount: payAmount.value,
      pos_profile: props.posProfile || shiftStore.profileName || '',
      invoice_ref: selectedOrder.value?.sales_order || '',
    })
    stkMessage.value = 'STK Prompt sent! Ask customer to enter PIN.'
  } catch (err) {
    stkMessage.value = 'Failed to send STK prompt: ' + (err.message || err)
  } finally {
    sendingSTK.value = false
  }
}

async function confirmPayBalance() {
  if (!selectedOrder.value || !payAmount.value || payAmount.value <= 0) return
  paying.value = true
  payError.value = ''

  try {
    const currentShift = shiftStore.openingShiftName || ''
    const result = await apiCall('pos_next_patch.api.deposit.pay_deposit_balance', {
      sales_order_name: selectedOrder.value.sales_order,
      mode_of_payment: payMode.value,
      amount: payAmount.value,
      pos_profile: props.posProfile || shiftStore.profileName || '',
      pos_opening_shift: currentShift,
    })

    const paidOrderObj = selectedOrder.value ? { ...selectedOrder.value } : null
    const soName = selectedOrder.value.sales_order
    const isCompleted = result?.is_fully_paid || false
    const invoiceName = result?.sales_invoice || null

    selectedOrder.value = null
    
    if (isCompleted && invoiceName) {
      successMsg.value = `✓ Order Completed & Invoiced as ${invoiceName}! Printing receipt...`
    } else {
      successMsg.value = result?.message || `Payment recorded for ${soName}.`
    }
    
    setTimeout(() => { successMsg.value = '' }, 6000)
    emit('paid')
    await fetchOrders()

    // If order was auto-finalized into invoice, print the final receipt
    if (isCompleted && result?.invoice_details) {
      printInvoiceReceipt(result.invoice_details)
    } else if (result?.order_details) {
      printReceipt(result.order_details)
    } else if (paidOrderObj) {
      // Calculate updated paid amount & balance due for the printed receipt
      const justPaid = Number(payAmount.value) || 0
      paidOrderObj.paid_amount = (Number(paidOrderObj.paid_amount || paidOrderObj.deposit_amount || 0)) + justPaid
      paidOrderObj.balance_due = Math.max(0, (Number(paidOrderObj.grand_total || 0)) - paidOrderObj.paid_amount)
      paidOrderObj.payment_history = paidOrderObj.payment_history || []
      paidOrderObj.payment_history.push({
        posting_date: new Date().toISOString().split('T')[0],
        mode_of_payment: payMode.value || 'Cash',
        allocated_amount: justPaid
      })
      printReceipt(paidOrderObj)
    }
  } catch (e) {
    payError.value = String(e?.message || e).replace(/&lt;/g, '<').replace(/&gt;/g, '>').substring(0, 300)
  } finally {
    paying.value = false
  }
}

function printReceipt(order) {
  const printWindow = window.open('', '_blank', 'width=380,height=600')
  if (!printWindow) return

  const itemsHtml = (order.items || []).map(i => `
    <tr>
      <td style="padding: 4px 0; text-align: left;">${i.item_name || i.item_code} x${i.qty}</td>
      <td style="padding: 4px 0; text-align: right; font-family: monospace;">KES ${(i.amount || 0).toLocaleString()}</td>
    </tr>
  `).join('')

  const historyHtml = (order.payment_history || []).map(p => `
    <tr>
      <td style="padding: 2px 0; text-align: left; font-size: 11px;">${p.posting_date} (${p.mode_of_payment})</td>
      <td style="padding: 2px 0; text-align: right; font-family: monospace; font-size: 11px;">KES ${(p.allocated_amount || 0).toLocaleString()}</td>
    </tr>
  `).join('')

  const revisionsHtml = (order.revisions && order.revisions.length > 0) ? `
    <div class="divider"></div>
    <div class="bold" style="margin-bottom: 4px; font-size: 11px;">REVISIONS & ITEM CHANGES (${order.revisions.length}):</div>
    ${order.revisions.map(r => `
      <div style="font-size: 10px; margin-bottom: 5px; padding: 4px; border: 1px dashed #d97706; background: #fffbeb;">
        <div style="font-weight: bold; color: #92400e;">Rev #${r.revision_no} • ${r.posting_date} ${r.posting_time} ${r.cashier ? `(${r.cashier})` : ''}</div>
        <div style="color: #4b5563; font-style: italic;">Reason: ${r.reason}</div>
        <div style="font-family: monospace; font-size: 9.5px; margin: 2px 0; color: #1e1b4b;">${r.changes_summary}</div>
        <div style="border-top: 1px dotted #ccc; padding-top: 2px; margin-top: 2px; font-size: 9.5px;">
          Total: KES ${Number(r.old_grand_total).toLocaleString()} ➔ <strong>KES ${Number(r.new_grand_total).toLocaleString()}</strong> (${r.price_difference >= 0 ? '+' : ''}KES ${Number(r.price_difference).toLocaleString()})
        </div>
      </div>
    `).join('')}
  ` : ''

  const html = `
    <!DOCTYPE html>
    <html>
    <head>
      <title>Layaway Deposit Receipt - ${order.sales_order}</title>
      <style>
        body { font-family: 'Courier New', Courier, monospace; font-size: 12px; margin: 0; padding: 15px; color: #000; width: 300px; }
        .text-center { text-align: center; }
        .text-right { text-align: right; }
        .bold { font-weight: bold; }
        .divider { border-top: 1px dashed #000; margin: 8px 0; }
        table { width: 100%; border-collapse: collapse; }
      </style>
    </head>
    <body>
      <div class="text-center">
        <h2 style="margin: 0;">WOOLMATT SUPERMARKET</h2>
        <p style="margin: 2px 0;">LAYAWAY DEPOSIT VOUCHER</p>
        <p style="margin: 2px 0; font-size: 10px;">Order: ${order.sales_order}</p>
        <p style="margin: 2px 0; font-size: 10px;">Date: ${order.transaction_date || order.creation?.split(' ')[0]}</p>
      </div>

      <div class="divider"></div>
      <div>
        <p style="margin: 2px 0;">Customer: <strong>${order.customer_name || order.customer}</strong></p>
        <p style="margin: 2px 0;">Phone: <strong>${order.customer_phone || 'N/A'}</strong></p>
        <p style="margin: 2px 0;">Collection Due: <strong>${order.delivery_date || 'N/A'}</strong></p>
      </div>

      <div class="divider"></div>
      <div class="bold" style="margin-bottom: 4px;">ORDER ITEMS:</div>
      <table>${itemsHtml}</table>

      ${revisionsHtml}

      <div class="divider"></div>
      <div class="bold" style="margin-bottom: 4px;">PAYMENT INSTALLMENTS:</div>
      <table>${historyHtml}</table>

      <div class="divider"></div>
      <table>
        <tr>
          <td class="bold">TOTAL ORDER:</td>
          <td class="text-right bold">KES ${Number(order.grand_total).toLocaleString()}</td>
        </tr>
        <tr>
          <td class="bold">TOTAL PAID:</td>
          <td class="text-right bold">KES ${Number(order.paid_amount || order.deposit_amount || 0).toLocaleString()}</td>
        </tr>
        <tr style="font-size: 14px;">
          <td class="bold">BALANCE REMAINING:</td>
          <td class="text-right bold">KES ${Number(order.balance_due).toLocaleString()}</td>
        </tr>
      </table>

      <div class="divider"></div>
      <div class="text-center" style="font-size: 10px; margin-top: 10px;">
        <p>Please retain this receipt for balance payment and goods collection.</p>
        <p>Thank you for shopping with us!</p>
      </div>
      <script>
        window.onload = function() { window.print(); }
      <\/script>
    </body>
    </html>
  `
  printWindow.document.write(html)
  printWindow.document.close()
}

function printInvoiceReceipt(invoice) {
  const printWindow = window.open('', '_blank', 'width=380,height=600')
  if (!printWindow) return

  const itemsHtml = (invoice.items || []).map(i => `
    <tr>
      <td style="padding: 4px 0; text-align: left;">${i.item_name || i.item_code} x${i.qty}</td>
      <td style="padding: 4px 0; text-align: right; font-family: monospace;">KES ${(i.amount || 0).toLocaleString()}</td>
    </tr>
  `).join('')

  const html = `
    <!DOCTYPE html>
    <html>
    <head>
      <title>Tax Invoice - ${invoice.sales_invoice}</title>
      <style>
        body { font-family: 'Courier New', Courier, monospace; font-size: 12px; margin: 0; padding: 15px; color: #000; width: 300px; }
        .text-center { text-align: center; }
        .text-right { text-align: right; }
        .bold { font-weight: bold; }
        .divider { border-top: 1px dashed #000; margin: 8px 0; }
        table { width: 100%; border-collapse: collapse; }
      </style>
    </head>
    <body>
      <div class="text-center">
        <h2 style="margin: 0;">WOOLMATT SUPERMARKET</h2>
        <p style="margin: 2px 0;">FINAL TAX INVOICE</p>
        <p style="margin: 2px 0; font-size: 10px;">Invoice: ${invoice.sales_invoice}</p>
        <p style="margin: 2px 0; font-size: 10px;">Date: ${invoice.posting_date} ${invoice.posting_time || ''}</p>
      </div>

      <div class="divider"></div>
      <div>
        <p style="margin: 2px 0;">Customer: <strong>${invoice.customer_name || invoice.customer}</strong></p>
        <p style="margin: 2px 0;">Status: <strong>FULLY PAID (LAYAWAY COMPLETED)</strong></p>
      </div>

      <div class="divider"></div>
      <table>${itemsHtml}</table>

      <div class="divider"></div>
      <table>
        <tr>
          <td class="bold">GRAND TOTAL:</td>
          <td class="text-right bold">KES ${Number(invoice.grand_total).toLocaleString()}</td>
        </tr>
        <tr>
          <td class="bold">DEPOSIT ADVANCES APPLIED:</td>
          <td class="text-right bold">KES ${Number(invoice.total_advance || invoice.grand_total).toLocaleString()}</td>
        </tr>
        <tr style="font-size: 14px;">
          <td class="bold">AMOUNT DUE:</td>
          <td class="text-right bold">KES 0.00</td>
        </tr>
      </table>

      <div class="divider"></div>
      <div class="text-center" style="font-size: 10px; margin-top: 10px;">
        <p>Goods Delivered & Completed. All deposits applied.</p>
        <p>Thank you for your business!</p>
      </div>
      <script>
        window.onload = function() { window.print(); }
      <\/script>
    </body>
    </html>
  `
  printWindow.document.write(html)
  printWindow.document.close()
}

function closeModal() {
  selectedOrder.value = null
  emit('close')
}

onMounted(() => {
  if (props.show) fetchOrders()
})
</script>
