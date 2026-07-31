/* HMS Frontend Interactivity Scripts */

document.addEventListener('DOMContentLoaded', function() {
    initBillingForm();
    initPrescriptionForm();
});

// Billing Dynamic Form Logic
function initBillingForm() {
    const billingItemsContainer = document.getElementById('billing-items-container');
    const btnAddItem = document.getElementById('btn-add-billing-item');
    if (!billingItemsContainer) return;

    function calculateBillingTotals() {
        let subtotal = 0;
        document.querySelectorAll('.billing-item-row').forEach(row => {
            const price = parseFloat(row.querySelector('.item-price').value) || 0;
            const qty = parseInt(row.querySelector('.item-qty').value) || 1;
            const itemTotal = price * qty;
            row.querySelector('.item-total').value = itemTotal.toFixed(2);
            subtotal += itemTotal;
        });

        const subtotalElem = document.getElementById('subtotal-val');
        const discountInput = document.getElementById('discount_percent');
        const taxInput = document.getElementById('tax_percent');
        const totalElem = document.getElementById('total-amount-val');
        const inputSubtotal = document.getElementById('input_subtotal');
        const inputDiscountAmt = document.getElementById('input_discount_amount');
        const inputTaxAmt = document.getElementById('input_tax_amount');
        const inputTotal = document.getElementById('input_total_amount');

        const discountPct = parseFloat(discountInput ? discountInput.value : 0) || 0;
        const taxPct = parseFloat(taxInput ? taxInput.value : 0) || 0;

        const discountAmt = subtotal * (discountPct / 100);
        const taxableAmount = subtotal - discountAmt;
        const taxAmt = taxableAmount * (taxPct / 100);
        const grandTotal = taxableAmount + taxAmt;

        if (subtotalElem) subtotalElem.textContent = '₹' + subtotal.toFixed(2);
        if (totalElem) totalElem.textContent = '₹' + grandTotal.toFixed(2);
        
        if (inputSubtotal) inputSubtotal.value = subtotal.toFixed(2);
        if (inputDiscountAmt) inputDiscountAmt.value = discountAmt.toFixed(2);
        if (inputTaxAmt) inputTaxAmt.value = taxAmt.toFixed(2);
        if (inputTotal) inputTotal.value = grandTotal.toFixed(2);
    }

    if (btnAddItem) {
        btnAddItem.addEventListener('click', function() {
            const rowCount = billingItemsContainer.children.length;
            const template = document.getElementById('billing-item-template');
            if (template) {
                const clone = template.content.cloneNode(true);
                billingItemsContainer.appendChild(clone);
                attachRowEvents(billingItemsContainer.lastElementChild);
                calculateBillingTotals();
            }
        });
    }

    function attachRowEvents(row) {
        const selectStock = row.querySelector('.stock-select');
        const inputName = row.querySelector('.item-name');
        const inputPrice = row.querySelector('.item-price');
        const inputQty = row.querySelector('.item-qty');
        const btnRemove = row.querySelector('.btn-remove-row');

        if (selectStock) {
            selectStock.addEventListener('change', function() {
                const selectedOpt = selectStock.options[selectStock.selectedIndex];
                if (selectedOpt.value) {
                    inputName.value = selectedOpt.getAttribute('data-name') || '';
                    inputPrice.value = selectedOpt.getAttribute('data-price') || '0';
                }
                calculateBillingTotals();
            });
        }

        if (inputPrice) inputPrice.addEventListener('input', calculateBillingTotals);
        if (inputQty) inputQty.addEventListener('input', calculateBillingTotals);

        if (btnRemove) {
            btnRemove.addEventListener('click', function() {
                if (billingItemsContainer.children.length > 1) {
                    row.remove();
                    calculateBillingTotals();
                } else {
                    alert('At least one item is required in the bill.');
                }
            });
        }
    }

    document.querySelectorAll('.billing-item-row').forEach(row => attachRowEvents(row));

    const discountInput = document.getElementById('discount_percent');
    const taxInput = document.getElementById('tax_percent');
    if (discountInput) discountInput.addEventListener('input', calculateBillingTotals);
    if (taxInput) taxInput.addEventListener('input', calculateBillingTotals);

    calculateBillingTotals();
}

// Prescription Dynamic Form Logic
function initPrescriptionForm() {
    const rxContainer = document.getElementById('rx-items-container');
    const btnAddRx = document.getElementById('btn-add-rx-item');
    if (!rxContainer) return;

    if (btnAddRx) {
        btnAddRx.addEventListener('click', function() {
            const template = document.getElementById('rx-item-template');
            if (template) {
                const clone = template.content.cloneNode(true);
                rxContainer.appendChild(clone);
                attachRxRowEvents(rxContainer.lastElementChild);
            }
        });
    }

    function attachRxRowEvents(row) {
        const inputSearch = row.querySelector('.rx-stock-search');
        const boxSuggestion = row.querySelector('.rx-suggestion-box');
        const inputMedName = row.querySelector('.rx-med-name');
        const selectUnit = row.querySelector('.rx-unit');
        const inputHiddenId = row.querySelector('.rx-medicine-id');
        const btnRemove = row.querySelector('.btn-remove-rx');

        if (inputSearch && boxSuggestion) {
            function renderSuggestions(query) {
                const stockList = window.stockItemsList || [];
                const q = query.trim().toLowerCase();
                
                boxSuggestion.innerHTML = '';
                
                if (!q) {
                    boxSuggestion.style.display = 'none';
                    return;
                }

                const matches = stockList.filter(item => item.name.toLowerCase().includes(q));
                
                if (matches.length === 0) {
                    boxSuggestion.innerHTML = '<div class="px-3 py-2 text-muted fs-8">No matching medicine found. You can type a custom name.</div>';
                    boxSuggestion.style.display = 'block';
                    return;
                }

                matches.forEach(item => {
                    const a = document.createElement('a');
                    a.href = '#';
                    a.className = 'dropdown-item py-2 px-3 border-bottom small d-flex justify-content-between align-items-center text-wrap';
                    a.innerHTML = `
                        <div>
                            <strong class="text-dark">${item.name}</strong>
                            <div class="fs-8 text-muted">Category: ${item.category}</div>
                        </div>
                        <span class="badge bg-success-subtle text-success border">Stock: ${item.qty}</span>
                    `;
                    
                    a.addEventListener('click', function(e) {
                        e.preventDefault();
                        inputSearch.value = item.name;
                        if (inputMedName) inputMedName.value = item.name;
                        if (selectUnit) selectUnit.value = item.category || 'Tablet';
                        if (inputHiddenId) inputHiddenId.value = item.id;
                        boxSuggestion.style.display = 'none';
                    });
                    
                    boxSuggestion.appendChild(a);
                });
                
                boxSuggestion.style.display = 'block';
            }

            inputSearch.addEventListener('input', function() {
                if (inputMedName) inputMedName.value = this.value;
                if (inputHiddenId) inputHiddenId.value = '';
                renderSuggestions(this.value);
            });

            inputSearch.addEventListener('focus', function() {
                if (this.value) {
                    renderSuggestions(this.value);
                }
            });

            document.addEventListener('click', function(e) {
                if (!row.contains(e.target)) {
                    boxSuggestion.style.display = 'none';
                }
            });
        }

        if (btnRemove) {
            btnRemove.addEventListener('click', function() {
                if (rxContainer.children.length > 1) {
                    row.remove();
                } else {
                    alert('At least one medicine is required in the prescription.');
                }
            });
        }
    }

    document.querySelectorAll('.rx-item-row').forEach(row => attachRxRowEvents(row));
}
